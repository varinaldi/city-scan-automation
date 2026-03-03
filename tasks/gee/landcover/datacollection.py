from utils.log_module import setup_logger
logger = setup_logger(__name__)

import os

import ee
import xarray as xr
import rioxarray
import xee

from .. import fns


def datacollection(
    aoi,
    city_name,
    output_dir,
    return_raster=False
    ):

    logger.info("Starting Land Cover data collection...")

    # ------------------------------------------------------------------
    # 1. Load AOI as EE Geometry and Image Source
    # ------------------------------------------------------------------

    AOI, bounds = fns.aoi_to_ee_geometry(aoi)
    lc = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map')

    # ------------------------------------------------------------------
    # 2. Create xarray from EE Image
    # ------------------------------------------------------------------
    ds = xr.open_dataset(
        lc,
        engine='ee',
        geometry=AOI,
        scale=10,
        crs='EPSG:3857'
    )

    # ------------------------------------------------------------------
    # 3. Save raster
    # ------------------------------------------------------------------

    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)
    tif_path = os.path.join(spatial_dir, f"{city_name}_lc.tif")

    from rasterio.enums import Resampling
    lc_rio = fns.xee_to_rio(ds['Map'], resampling=Resampling.nearest)
    lc_rio.rio.to_raster(tif_path)

    logger.info(f"Land cover raster saved to: {tif_path}")

    if return_raster:
        return lc_rio

    return None
