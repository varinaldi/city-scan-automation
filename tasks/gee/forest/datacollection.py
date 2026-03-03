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

    logger.info("Starting Forest data collection...")

    # ------------------------------------------------------------------
    # 1. Load AOI as EE Geometry and Image Source
    # ------------------------------------------------------------------

    AOI, bounds = fns.aoi_to_ee_geometry(aoi)
    # fc = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")
    fc = ee.Image("UMD/hansen/global_forest_change_2024_v1_12")

    # ------------------------------------------------------------------
    # 2. Compute forest cover and deforestation (server-side)
    # ------------------------------------------------------------------

    deforestation0023 = fc.select('loss').eq(1).rename('fcloss0023')
    forestCover00 = fc.select('treecover2000').gte(20)
    # Note: forest gain is only updated until 2012
    forestCoverGain0012 = fc.select('gain').eq(1)
    forestCover23 = forestCover00.subtract(deforestation0023) \
        .add(forestCoverGain0012).gte(1).rename('fc23')
    deforestation_year = fc.select('lossyear').rename('lossyear')

    # ------------------------------------------------------------------
    # 3. Create xarray from EE Images
    # ------------------------------------------------------------------

    ds_fc23 = xr.open_dataset(
        forestCover23,
        engine='ee',
        geometry=AOI,
        scale=30,
        crs='EPSG:3857'
    )

    ds_defor = xr.open_dataset(
        deforestation_year,
        engine='ee',
        geometry=AOI,
        scale=30,
        crs='EPSG:3857'
    )

    # ------------------------------------------------------------------
    # 4. Save rasters
    # ------------------------------------------------------------------

    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    from rasterio.enums import Resampling

    # Forest cover 2023
    tif_fc23 = os.path.join(spatial_dir, f"{city_name}_forest_cover23.tif")
    fc23_rio = fns.xee_to_rio(ds_fc23['fc23'], resampling=Resampling.nearest)
    fc23_rio.rio.to_raster(tif_fc23)
    logger.info(f"Forest cover raster saved to: {tif_fc23}")

    # Deforestation year
    tif_defor = os.path.join(spatial_dir, f"{city_name}_deforestation.tif")
    defor_rio = fns.xee_to_rio(ds_defor['lossyear'], resampling=Resampling.nearest)
    defor_rio.rio.to_raster(tif_defor)
    logger.info(f"Deforestation raster saved to: {tif_defor}")

    if return_raster:
        return fc23_rio, defor_rio

    return None
