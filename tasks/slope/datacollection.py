from utils.log_module import setup_logger
logger = setup_logger(__name__)
import requests
import shutil


def datacollection(
    aoi,
    city_name,
    output_dir,
    return_raster=False,
):
    """
    Extract or download FABDEM elevation raster tiles from output folders, perform slope calculation,
    clip to AOI, and save as a city-level slope raster.

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

    Returns
    -------
    (numpy.ndarray, dict) or None
        Clipped raster array and rasterio metadata if return_raster=True,
        otherwise None.
    """

    import os
    import numpy as np
    import geopandas as gpd
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    from rasterio.mask import mask

    # ------------------------------------------------------------------
    # 1. Normalize AOI CRS
    # ------------------------------------------------------------------
    if aoi.crs is None or aoi.crs.to_epsg() != 4326:
        aoi = aoi.to_crs(epsg=4326)

    aoi_geom = aoi.geometry.values

    spatial_dir = os.path.join(output_dir, "spatial")
    elev_buf_path = os.path.join(spatial_dir, f"{city_name}_elevation_buf.tif")
    slope_output_path = os.path.join(spatial_dir, f"{city_name}_slope.tif")

    # ------------------------------------------------------------------
    # 2. Ensure buffered elevation exists
    # ------------------------------------------------------------------
    if not os.path.exists(elev_buf_path):
        from tasks.elevation import datacollection as elev_collect

        elev_collect.datacollection(
            aoi=aoi,
            city_name=city_name,
            output_dir=output_dir,
            return_raster=False,
            create_raster_buffer=True,
        )

    # ------------------------------------------------------------------
    # 3. Select projected CRS for slope math
    # ------------------------------------------------------------------
    utm_crs = aoi.estimate_utm_crs()

    # ------------------------------------------------------------------
    # 4. Reproject elevation to projected CRS
    # ------------------------------------------------------------------
    with rasterio.open(elev_buf_path) as src:

        transform, width, height = calculate_default_transform(
            src.crs, utm_crs, src.width, src.height, *src.bounds
        )

        profile = src.profile.copy()
        profile.update({
            "crs": utm_crs,
            "transform": transform,
            "width": width,
            "height": height,
            "dtype": "float32",
        })

        elevation_proj = np.empty((height, width), dtype=np.float32)

        reproject(
            source=rasterio.band(src, 1),
            destination=elevation_proj,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=utm_crs,
            resampling=Resampling.bilinear,
        )

        nodata = src.nodata

    # ------------------------------------------------------------------
    # 5. Nodata-safe slope calculation
    # ------------------------------------------------------------------
    elev = elevation_proj.astype(np.float32)

    if nodata is not None:
        elev[elev == nodata] = np.nan

    pixel_x = transform.a
    pixel_y = -transform.e

    dy, dx = np.gradient(elev, pixel_y, pixel_x)

    slope = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))

    slope[np.isnan(elev)] = np.nan

    # ------------------------------------------------------------------
    # 6. Write projected slope raster (temporary)
    # ------------------------------------------------------------------
    slope_proj_path = os.path.join(spatial_dir, f"{city_name}_slope_proj.tif")

    profile.update({
        "count": 1,
        "nodata": np.nan,
        "compress": "lzw",
    })

    with rasterio.open(slope_proj_path, "w", **profile) as dst:
        dst.write(slope.astype(np.float32), 1)

    # ------------------------------------------------------------------
    # 7. Reproject slope back to 4326
    # ------------------------------------------------------------------
    with rasterio.open(slope_proj_path) as src:

        transform2, w2, h2 = calculate_default_transform(
            src.crs, "EPSG:4326", src.width, src.height, *src.bounds
        )

        profile2 = src.profile.copy()
        profile2.update({
            "crs": "EPSG:4326",
            "transform": transform2,
            "width": w2,
            "height": h2,
        })

        slope_4326 = np.empty((h2, w2), dtype=np.float32)

        reproject(
            source=rasterio.band(src, 1),
            destination=slope_4326,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform2,
            dst_crs="EPSG:4326",
            resampling=Resampling.bilinear,
        )

    # ------------------------------------------------------------------
    # 8. Clip to original AOI
    # ------------------------------------------------------------------
    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(**profile2) as dataset:
            dataset.write(slope_4326, 1)

            clipped_array, clipped_transform = mask(
                dataset,
                aoi_geom,
                crop=True,
                nodata=np.nan,
            )

            clipped_meta = dataset.meta.copy()
            clipped_meta.update({
                "height": clipped_array.shape[1],
                "width": clipped_array.shape[2],
                "transform": clipped_transform,
            })

    # ------------------------------------------------------------------
    # 9. Save final slope raster
    # ------------------------------------------------------------------
    with rasterio.open(slope_output_path, "w", **clipped_meta) as dst:
        dst.write(clipped_array)
    
    logger.info(f"Writing slope raster: {slope_output_path}")

    # ------------------------------------------------------------------
    # 10. Optional return
    # ------------------------------------------------------------------
    if return_raster:
        return clipped_array, clipped_meta

    return None


