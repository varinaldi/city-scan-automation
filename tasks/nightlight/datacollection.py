from utils.log_module import setup_logger
logger = setup_logger(__name__)

import os

import ee
import xarray as xr
import rioxarray
import xee

from utils import gee_fns as fns


def datacollection(
    aoi,
    city_name,
    output_dir,
    return_raster=False
):

    logger.info("Starting nightlight data collection...")

    # ------------------------------------------------------------------
    # 1. Load AOI and VIIRS collection (last 10 years)
    # ------------------------------------------------------------------
    AOI, bounds = fns.aoi_to_ee_geometry(aoi)

    viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG')

    max_date = ee.Date(viirs.reduceColumns(ee.Reducer.max(), ['system:time_start']).get('max'))
    date_range = ee.DateRange(max_date.advance(-10, 'year'), max_date)

    def addTime(image):
        return image.addBands(image.metadata('system:time_start').divide(1000 * 60 * 60 * 24 * 365))

    viirs_filtered = viirs.filterDate(date_range).filterBounds(AOI).map(addTime)

    # ------------------------------------------------------------------
    # 2. Compute linear fit (trend) and sum of lights
    # ------------------------------------------------------------------
    linear_fit = viirs_filtered.select(['system:time_start', 'avg_rad']).reduce(ee.Reducer.linearFit())
    sum_of_light = viirs_filtered.select('avg_rad').reduce(ee.Reducer.sum())

    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    results = {}

    # ------------------------------------------------------------------
    # 3. Export linear fit (scale = slope of trend)
    # ------------------------------------------------------------------
    ds_linfit = xr.open_dataset(
        linear_fit.select('scale'),
        engine='ee',
        geometry=AOI,
        scale=463.83,
        crs='EPSG:3857'
    )

    linfit_rio = fns.xee_to_rio(ds_linfit['scale'])

    linfit_path = os.path.join(spatial_dir, f"{city_name}_linfit.tif")
    linfit_rio.rio.to_raster(linfit_path)
    logger.info(f"Saved linear fit: {linfit_path}")

    results['linfit'] = linfit_rio if return_raster else linfit_path

    # ------------------------------------------------------------------
    # 4. Export sum of lights
    # ------------------------------------------------------------------
    ds_sum = xr.open_dataset(
        sum_of_light.select('avg_rad_sum'),
        engine='ee',
        geometry=AOI,
        scale=463.83,
        crs='EPSG:3857'
    )

    sum_rio = fns.xee_to_rio(ds_sum['avg_rad_sum'])

    sum_path = os.path.join(spatial_dir, f"{city_name}_avg_rad_sum.tif")
    sum_rio.rio.to_raster(sum_path)
    logger.info(f"Saved sum of lights: {sum_path}")

    results['avg_rad_sum'] = sum_rio if return_raster else sum_path

    return results
