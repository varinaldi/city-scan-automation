from utils.log_module import setup_logger
logger = setup_logger(__name__)

import os

import ee
import geopandas as gpd
import xarray as xr
import rioxarray
import xee

from . import fns


def datacollection(
    aoi,
    city_name,
    output_dir,
    return_raster=False
    ):

    logger.info("Starting Elevation data collection...")

    # ------------------------------------------------------------------
    # 1. Load AOI as EE Geometry and Image Source
    # ------------------------------------------------------------------

    AOI, bounds = fns.aoi_to_ee_geometry(aoi)

    # Buffered AOI for slope/aspect calculations downstream
    aoi_buf = gpd.GeoDataFrame(geometry=aoi.buffer(0.001), crs=aoi.crs)
    AOI_buf, _ = fns.aoi_to_ee_geometry(aoi_buf)

    elevation = ee.Image("USGS/SRTMGL1_003")

    # ------------------------------------------------------------------
    # 2. Create xarray from EE Image
    # ------------------------------------------------------------------

    ds = xr.open_dataset(
        elevation,
        engine='ee',
        geometry=AOI,
        scale=30,
        crs='EPSG:3857'
    )

    ds_buf = xr.open_dataset(
        elevation,
        engine='ee',
        geometry=AOI_buf,
        scale=30,
        crs='EPSG:3857'
    )

    # ------------------------------------------------------------------
    # 3. Save rasters
    # ------------------------------------------------------------------

    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    # Clipped elevation
    tif_path = os.path.join(spatial_dir, f"{city_name}_elevation.tif")
    elev_rio = fns.xee_to_rio(ds['elevation'])
    elev_rio.rio.to_raster(tif_path)
    logger.info(f"Elevation raster saved to: {tif_path}")

    # Buffered elevation (for slope/aspect)
    tif_path_buf = os.path.join(spatial_dir, f"{city_name}_elevation_buf.tif")
    elev_buf_rio = fns.xee_to_rio(ds_buf['elevation'])
    elev_buf_rio.rio.to_raster(tif_path_buf)
    logger.info(f"Buffered elevation raster saved to: {tif_path_buf}")

    if return_raster:
        return elev_rio, elev_buf_rio

    return None
