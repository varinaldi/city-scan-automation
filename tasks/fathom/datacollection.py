# import
import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from utils.log_module import setup_logger
import numpy as np
from utils import raster_module as raster_pro
logger = setup_logger(__name__)
from os.path import exists
GCS_FATHOM_BASE = "/vsigs/city-scan-global-private/Fathom/v2023"
from config.gdal_auth import configure_gdal_gcs

configure_gdal_gcs()

def apply_flood_threshold(out_image, out_meta, flood_threshold, prob):
    import numpy as np

    # Ensure out_image is a NumPy array
    out_image = np.asarray(out_image)

    # Replace nodata values with 0
    out_image[out_image == out_meta['nodata']] = 0

    # Apply flood threshold
    out_image = np.where(out_image < flood_threshold, 0, out_image)
    out_image = np.where(out_image >= flood_threshold, 1, out_image)

    # Multiply by probability
    out_image = out_image * prob

    # Update metadata
    out_meta.update({'nodata': 0, 'dtype': 'float32'})

    return out_image, out_meta

def composite_flood_raster(raster_arrays, out_meta, output_raster):
    import numpy as np
    import rasterio

    out_image = np.squeeze(np.maximum.reduce(raster_arrays)).astype(np.float32)

    with rasterio.open(output_raster, 'w', **out_meta) as dst:
        dst.write(out_image, 1)


def _process_year(
    flood_type,
    year,
    ssp,
    flood_rps,
    lat_tiles,
    lon_tiles,
    flood_type_folder_dict,
    flood_threshold,
    spatial_dir,
    buffer_aoi,
    utm_crs,
    city_name,
    flood_ssp_labels=None
):
    """
    Process one flood_type-year-(optional ssp) combination.

    Methodology preserved from old code:
    tiles → mosaic → mask → threshold → stack (max reduce) → write → reproject
    """

    out_image_arrays = []
    out_meta = None

    for rp in flood_rps:

        tile_paths = []

        # ---------------------------------------------------
        # 1️⃣ Collect tile paths for this return period
        # ---------------------------------------------------
        for lat in lat_tiles:
            for lon in lon_tiles:

                if year <= 2020:
                    relative_path = (
                        f"GLOBAL-1ARCSEC-NW_OFFSET-1in{rp}-"
                        f"{flood_type_folder_dict[flood_type]}-DEPTH-{year}-"
                        f"PERCENTILE50-v3.0/"
                        f"{lat.lower()}{lon.lower()}.tif"
                    )
                else:
                    relative_path = (
                        f"GLOBAL-1ARCSEC-NW_OFFSET-1in{rp}-"
                        f"{flood_type_folder_dict[flood_type]}-DEPTH-{year}-"
                        f"SSP{flood_ssp_labels[ssp]}-PERCENTILE50-v3.0/"
                        f"{lat.lower()}{lon.lower()}.tif"
                    )

                gcs_path = f"{GCS_FATHOM_BASE}/{relative_path}"
                tile_paths.append(gcs_path)

        if not tile_paths:
            logger.warning(f"No tiles found for RP {rp}")
            continue

        # ---------------------------------------------------
        # 2️⃣ Mosaic tiles (CRITICAL alignment step)
        # ---------------------------------------------------
        tmp_mosaic_name = (
            f"tmp_{city_name}_{flood_type}_{year}"
            f"{'' if ssp is None else f'_ssp{ssp}'}_rp{rp}.tif"
        )

        tmp_mosaic_path = os.path.join(spatial_dir, tmp_mosaic_name)

        try:
            raster_pro.mosaic_raster(
                tile_paths,
                spatial_dir,
                tmp_mosaic_name
            )
        except Exception as e:
            logger.debug(f"Mosaic failed for RP {rp}: {str(e)}")
            continue

        # ---------------------------------------------------
        # 3️⃣ Mask mosaic to AOI (ensures identical grid)
        # ---------------------------------------------------
        try:
            with rasterio.open(tmp_mosaic_path) as src:
                out_image, out_transform = mask(
                    src,
                    buffer_aoi.geometry,
                    crop=True
                )

                out_meta = src.meta.copy()
                out_meta.update({
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })

        except Exception as e:
            logger.debug(f"Mask failed for RP {rp}: {str(e)}")
            continue

        # ---------------------------------------------------
        # 4️⃣ Apply threshold + probability weighting
        # ---------------------------------------------------
        out_image, out_meta = apply_flood_threshold(
            out_image,
            out_meta,
            flood_threshold,
            100 / rp
        )

        out_image_arrays.append(out_image)

        # Optional: remove temporary mosaic
        try:
            os.remove(tmp_mosaic_path)
        except Exception:
            pass

    # -------------------------------------------------------
    # 5️⃣ Composite across return periods
    # -------------------------------------------------------
    if not out_image_arrays or out_meta is None:
        logger.warning(
            f"{flood_type} {year}"
            + (f" SSP{ssp}" if ssp else "")
            + " : no valid RP data"
        )
        return None

    if ssp is None:
        out_name = f"{city_name}_{flood_type}_{year}.tif"
    else:
        out_name = f"{city_name}_{flood_type}_{year}_ssp{ssp}.tif"

    output_raster = os.path.join(spatial_dir, out_name)

    composite_flood_raster(
        out_image_arrays,
        out_meta,
        output_raster
    )

    # -------------------------------------------------------
    # 6️⃣ Reproject to UTM (same as old code)
    # -------------------------------------------------------
    utm_output = output_raster.replace(".tif", "_utm.tif")

    raster_pro.reproject_raster(
        output_raster,
        utm_output,
        dst_crs=utm_crs
    )

    logger.info(f"Generated: {out_name}")

    return {
        "wgs84": output_raster,
        "utm": utm_output
    }

def datacollection(
        aoi: gpd.GeoDataFrame,
        city_name: str,
        city_inputs: dict,
        menu: dict,
        output_dir: str,
    ):
    """
    Collect Fathom flood rasters from private GCS bucket,
    clip to AOI, threshold, and generate composite rasters.

    Access control:
    - Team member (IAM access): full analysis runs
    - Public user (no IAM access): flood section skipped
    """

    logger.info("Starting Fathom data collection (GCS-native)…")

    # -----------------------------
    # Validate AOI
    # -----------------------------
    if aoi is None or aoi.empty:
        logger.error("AOI is empty.")
        return

    if aoi.crs is None:
        logger.error("AOI has no CRS defined.")
        return

    logger.info(f"AOI CRS: {aoi.crs}")

    # -----------------------------
    # Parameters
    # -----------------------------
    flood_threshold = city_inputs['flood']['threshold']
    flood_years = city_inputs['flood']['year']
    if isinstance(flood_years, int):
        flood_years = [flood_years]

    flood_ssps = city_inputs['flood']['ssp']
    flood_rps = city_inputs['flood']['return_period']

    flood_types = ['coastal', 'fluvial', 'pluvial']

    flood_ssp_labels = {
        1: '1_2.6',
        2: '2_4.5',
        3: '3_7.0',
        5: '5_8.5'
    }

    flood_type_folder_dict = {
        'coastal': 'COASTAL-UNDEFENDED',
        'fluvial': 'FLUVIAL-UNDEFENDED',
        'pluvial': 'PLUVIAL-DEFENDED'
    }

    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    # -----------------------------
    # AOI preparation
    # -----------------------------
    aoi_bounds = aoi.bounds
    buffer_aoi = aoi.buffer(
        np.nanmax([
            aoi_bounds.maxx - aoi_bounds.minx,
            aoi_bounds.maxy - aoi_bounds.miny
        ])
    )

    lat_tiles = raster_pro.tile_finder(buffer_aoi, 'lat')
    lon_tiles = raster_pro.tile_finder(buffer_aoi, 'lon')
    logger.info(f"found: {lat_tiles, lon_tiles}")

    utm_crs = aoi.estimate_utm_crs()

    # -----------------------------
    # Main processing loop
    # -----------------------------
    for ft in flood_types:
        logger.info(f"Flood Types: {ft}")
        if not menu.get(f'flood_{ft}', False):
            continue

        for year in flood_years:

            if year <= 2020:
                try:
                    _process_year(
                        ft, year, None, flood_rps, lat_tiles, lon_tiles,
                        flood_type_folder_dict, flood_threshold,
                        spatial_dir, buffer_aoi, utm_crs, city_name
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "does not exist" in error_msg or "not recognized" in error_msg:
                        logger.warning(
                            f"Data missing or non-existent: {ft} {year}"
                        )
                    else:
                        logger.error(
                            f"Failed to process {ft} {year}: {error_msg}"
                        )
                    continue

            else:
                for ssp in flood_ssps:
                    try:
                        _process_year(
                            ft, year, ssp, flood_rps, lat_tiles, lon_tiles,
                            flood_type_folder_dict, flood_threshold,
                            spatial_dir, buffer_aoi, utm_crs, city_name,
                            flood_ssp_labels
                        )
                    except Exception as e:
                        error_msg = str(e)
                        if "does not exist" in error_msg or "not recognized" in error_msg:
                            logger.warning(
                                f"Data missing or non-existent: {ft} {year} SSP{ssp}"
                            )
                        else:
                            logger.error(
                                f"Failed to process {ft} {year} SSP{ssp}: {error_msg}"
                            )
                        continue

    # -----------------------------
    # Combined flood map
    # -----------------------------
    if menu.get('flood_comb', False):
        for year in flood_years:

            if year <= 2020:
                comb_list = [
                    f'{spatial_dir}/{city_name}_{ft}_{year}.tif'
                    for ft in flood_types
                    if exists(f'{spatial_dir}/{city_name}_{ft}_{year}.tif')
                ]

                if comb_list:
                    raster_pro.mosaic_raster(
                        comb_list, spatial_dir,
                        f'{city_name}_comb_{year}.tif',
                        method='max'
                    )

                    raster_pro.reproject_raster(
                        f'{spatial_dir}/{city_name}_comb_{year}.tif',
                        f'{spatial_dir}/{city_name}_comb_{year}_utm.tif',
                        dst_crs=utm_crs
                    )

            else:
                for ssp in flood_ssps:
                    comb_list = [
                        f'{spatial_dir}/{city_name}_{ft}_{year}_ssp{ssp}.tif'
                        for ft in flood_types
                        if exists(f'{spatial_dir}/{city_name}_{ft}_{year}_ssp{ssp}.tif')
                    ]

                    if comb_list:
                        raster_pro.mosaic_raster(
                            comb_list, spatial_dir,
                            f'{city_name}_comb_{year}_ssp{ssp}.tif',
                            method='max'
                        )

                        raster_pro.reproject_raster(
                            f'{spatial_dir}/{city_name}_comb_{year}_ssp{ssp}.tif',
                            f'{spatial_dir}/{city_name}_comb_{year}_ssp{ssp}_utm.tif',
                            dst_crs=utm_crs
                        )

