from core.py.log_module import setup_logger
logger = setup_logger(__name__)
import requests
import shutil

def download_public_zip(url, output_path):
    """
    Download a publicly accessible ZIP file via HTTP.

    Parameters
    ----------
    url : str
        Public URL of the ZIP file.
    output_path : str
        Local path to save the ZIP.
    """
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)

def normalize_fabdem_tile_name(tile_name: str) -> str:
    """
    Normalize FABDEM tile name to match filenames inside ZIP archives.
    FABDEM uses 2-digit latitude, 3-digit longitude (e.g. N36E010).

    Examples
    --------
    N036E010 -> N36E010
    S003W098 -> S3W098
    N15E120  -> N15E120
    """
    import re

    match = re.match(r"([NS])0*(\d+)([EW])0*(\d+)", tile_name)
    if not match:
        return tile_name

    lat_hem, lat_deg, lon_hem, lon_deg = match.groups()
    return f"{lat_hem}{int(lat_deg)}{lon_hem}{int(lon_deg):03d}"



def datacollection(
    aoi,
    city_name,
    output_dir,
    return_raster=False,
    create_raster_buffer=True,
):
    """
    Download FABDEM raster tiles from internal cloud storage, mosaic,
    clip to AOI, and save as a city-level elevation raster.

    Parameters
    ----------
    aoi : geopandas.GeoDataFrame
        AOI polygon(s). Must be convertible to EPSG:4326.
    city_name : str
        City name used for output file naming.
    output_dir : str
        Base directory where outputs will be written.
    return_raster : bool, optional
        If True, return clipped raster array and metadata.
    create_raster_buffer : bool, optional
        If True, raster will be clipped to buffered AOI (used for slope analysis)

    Returns
    -------
    (numpy.ndarray, dict) or None
        Clipped raster array and rasterio metadata if return_raster=True,
        otherwise None.
    """

    import os
    import tempfile
    import zipfile

    import geopandas as gpd
    import rasterio
    from rasterio.merge import merge
    from rasterio.mask import mask

    import core.py as utils

    # ------------------------------------------------------------------
    # 1. Normalize AOI CRS
    # ------------------------------------------------------------------
    logger.info("Normalizing AOI CRS to EPSG:4326")

    if aoi.crs is None or aoi.crs.to_epsg() != 4326:
        aoi = aoi.to_crs(epsg=4326)

    aoi_geom = aoi.geometry.values
    aoi_bounds = aoi.total_bounds  # (minx, miny, maxx, maxy)

    # ------------------------------------------------------------------
    # 2. Prepare output directories
    # ------------------------------------------------------------------
    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    output_raster_path = os.path.join(
        spatial_dir, f"{city_name}_elevation.tif"
    )

    # ------------------------------------------------------------------
    # 3. Load FABDEM tile index
    # ------------------------------------------------------------------
    logger.info("Loading FABDEM tile index")

    bucket_base = "https://storage.googleapis.com/city-scan-global-public/"
    tile_index_path = "fabdem/FABDEM_v1-2_tiles.geojson"
    fabdem_tiles = gpd.read_file(bucket_base+tile_index_path)

    # ------------------------------------------------------------------
    # 4. Find intersecting tiles
    # ------------------------------------------------------------------
    logger.info("Intersecting AOI with FABDEM tiles")

    intersecting = fabdem_tiles[
        fabdem_tiles.intersects(aoi.unary_union)
    ]

    if intersecting.empty:
        logger.error("No FABDEM tiles found for AOI")
        raise RuntimeError("No FABDEM tiles found for AOI")

    tile_names = intersecting["tile_name"].unique().tolist()
    logger.info(tile_names)
    zip_files = intersecting["zipfile_name"].unique().tolist()
    logger.info(zip_files)

    logger.info(
        f"Found {len(tile_names)} FABDEM tiles across "
        f"{len(zip_files)} ZIP archives"
    )

    # ------------------------------------------------------------------
    # 5. Download ZIP files & extract required TIFFs (public bucket)
    # ------------------------------------------------------------------
    logger.info("Downloading FABDEM ZIP archives from public bucket")

    extracted_tifs = []

    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("Using temporary directory for ZIP extraction")

        for zip_name in zip_files:
            zip_url = f"{bucket_base}fabdem/{zip_name}"
            local_zip = os.path.join(tmpdir, zip_name)

            logger.info(f"Downloading {zip_url}")

            try:
                with requests.get(zip_url, stream=True, timeout=300) as r:
                    r.raise_for_status()
                    with open(local_zip, "wb") as f:
                        shutil.copyfileobj(r.raw, f)
            except Exception as e:
                logger.error(f"Failed to download {zip_name}: {e}")
                continue

            logger.info(f"Extracting required TIFFs from {zip_name}")

            try:
                with zipfile.ZipFile(local_zip, "r") as z:
                    zip_contents = z.namelist()

                    logger.debug(
                        f"ZIP {zip_name} contains {len(zip_contents)} files"
                    )

                    for tile in tile_names:
                        normalized_tile = normalize_fabdem_tile_name(tile)
                        expected_suffix = f"{normalized_tile}_FABDEM_V1-2.tif"

                        for member in zip_contents:
                            if member.endswith(expected_suffix):
                                logger.info(f"Extracting {member}")
                                z.extract(member, tmpdir)

                                extracted_tifs.append(
                                    os.path.join(tmpdir, member)
                                )

            except Exception as e:
                logger.error(f"Failed to extract {zip_name}: {e}")

        if not extracted_tifs:
            logger.warning("No FABDEM TIFFs extracted — falling back to GEE SRTM")
            return gee_elevation(aoi, city_name, output_dir, return_raster, create_raster_buffer)
        # ------------------------------------------------------------------
        # 6. Mosaic tiles
        # ------------------------------------------------------------------
        logger.info("Mosaicing FABDEM tiles")

        src_files = [rasterio.open(fp) for fp in extracted_tifs]
        mosaic_array, mosaic_transform = merge(src_files)

        mosaic_meta = src_files[0].meta.copy()
        mosaic_meta.update({
            "height": mosaic_array.shape[1],
            "width": mosaic_array.shape[2],
            "transform": mosaic_transform,
        })

        for src in src_files:
            src.close()

        # ------------------------------------------------------------------
        # 7. Clip mosaic to AOI
        # ------------------------------------------------------------------
        logger.info("Clipping mosaic to AOI")

        with rasterio.io.MemoryFile() as memfile:
            with memfile.open(**mosaic_meta) as dataset:
                dataset.write(mosaic_array)

                clipped_array, clipped_transform = mask(
                    dataset,
                    aoi_geom,
                    crop=True,
                    nodata=mosaic_meta.get("nodata"),
                )

                clipped_meta = dataset.meta.copy()
                clipped_meta.update({
                    "height": clipped_array.shape[1],
                    "width": clipped_array.shape[2],
                    "transform": clipped_transform,
                })
        # ------------------------------------------------------------------
        # 8. Write output raster
        # ------------------------------------------------------------------
        logger.info(f"Writing elevation raster to {output_raster_path}")

        with rasterio.open(output_raster_path, "w", **clipped_meta) as dst:
            dst.write(clipped_array)

        # ------------------------------------------------------------------
        # 9. Clip raster to buffered AOI (for slope analysis)
        # ------------------------------------------------------------------
        if create_raster_buffer:
            logger.info("Creating buffered AOI for slope-safe raster")

            buffer_distance_m = 500  

            # --------------------------------------------------------------
            # 9a. Project AOI to local metric CRS
            # --------------------------------------------------------------
            utm_crs = aoi.estimate_utm_crs()
            aoi_utm = aoi.to_crs(utm_crs)

            # --------------------------------------------------------------
            # 9b. Buffer in meters, then return to WGS84
            # --------------------------------------------------------------
            buffered = aoi_utm.buffer(buffer_distance_m)
            buffered_wgs = buffered.to_crs(epsg=4326)

            buffered_geom = buffered_wgs.values

            # --------------------------------------------------------------
            # 9c. Clip mosaic again with buffered AOI
            # --------------------------------------------------------------
            logger.info("Clipping elevation to buffered AOI")

            with rasterio.io.MemoryFile() as memfile:
                with memfile.open(**mosaic_meta) as dataset:
                    dataset.write(mosaic_array)

                    buf_array, buf_transform = mask(
                        dataset,
                        buffered_geom,
                        crop=True,
                        nodata=mosaic_meta.get("nodata"),
                    )

                    buf_meta = dataset.meta.copy()
                    buf_meta.update({
                        "height": buf_array.shape[1],
                        "width": buf_array.shape[2],
                        "transform": buf_transform,
                    })

            buf_output_path = os.path.join(
                spatial_dir, f"{city_name}_elevation_buf.tif"
            )

            logger.info(f"Writing buffered elevation raster: {buf_output_path}")

            with rasterio.open(buf_output_path, "w", **buf_meta) as dst:
                dst.write(buf_array)

        

    # ------------------------------------------------------------------
    # 9. Optional return
    # ------------------------------------------------------------------
    if return_raster:
        return clipped_array, clipped_meta

    return None


def gee_elevation(aoi, city_name, output_dir, return_raster=False, create_raster_buffer=True):
    """Fallback: download SRTM elevation from GEE when FABDEM is unavailable."""
    import os
    import ee
    import geopandas as gpd
    import xarray as xr
    import rioxarray
    import xee
    from core.py import gee_fns as fns

    logger.info("Starting GEE SRTM elevation data collection...")

    AOI, bounds = fns.aoi_to_ee_geometry(aoi)
    elevation = ee.Image("USGS/SRTMGL1_003")

    ds = xr.open_dataset(
        elevation, engine='ee', geometry=AOI,
        scale=30, crs='EPSG:3857'
    )

    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    # Clipped elevation — mask to AOI boundary (not just bbox)
    elev_rio = fns.xee_to_rio(ds['elevation'])
    elev_rio = elev_rio.rio.clip(aoi.to_crs(elev_rio.rio.crs).geometry, drop=True)
    tif_path = os.path.join(spatial_dir, f"{city_name}_elevation.tif")
    elev_rio.rio.to_raster(tif_path)
    logger.info(f"Elevation raster saved to: {tif_path}")

    # Buffered elevation (for slope analysis)
    if create_raster_buffer:
        aoi_buf = gpd.GeoDataFrame(geometry=aoi.buffer(0.001), crs=aoi.crs)
        AOI_buf, _ = fns.aoi_to_ee_geometry(aoi_buf)

        ds_buf = xr.open_dataset(
            elevation, engine='ee', geometry=AOI_buf,
            scale=30, crs='EPSG:3857'
        )

        elev_buf_rio = fns.xee_to_rio(ds_buf['elevation'])
        tif_path_buf = os.path.join(spatial_dir, f"{city_name}_elevation_buf.tif")
        elev_buf_rio.rio.to_raster(tif_path_buf)
        logger.info(f"Buffered elevation raster saved to: {tif_path_buf}")

    if return_raster:
        return elev_rio, elev_buf_rio if create_raster_buffer else None

    return None
