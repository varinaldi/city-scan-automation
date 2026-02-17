from utils.log_module import setup_logger
logger = setup_logger(__name__)

import os
import csv
import numpy as np

import ee
import xarray as xr
import rioxarray
import xee

from . import fns

CLASS_VALUES = {
    10: 'Tree cover',
    20: 'Shrubland',
    30: 'Grassland',
    40: 'Cropland',
    50: 'Built-up',
    60: 'Bare / sparse vegetation',
    70: 'Snow and ice',
    80: 'Permanent water bodies',
    90: 'Herbaceous wetland',
    95: 'Mangroves',
    100: 'Moss and lichen'
}


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
    # 3. Extract land cover data and compute stats
    # ------------------------------------------------------------------
    lc_data = ds['Map'].isel(time=0).values

    # Compute frequency histogram
    valid = lc_data[~np.isnan(lc_data)].astype(int)
    unique, counts = np.unique(valid, return_counts=True)
    pixel_counts = dict(zip(unique, counts))

    counts_dict = {}
    for class_val, class_name in CLASS_VALUES.items():
        counts_dict[class_name] = pixel_counts.get(class_val, 0)

    # Write CSV (same format as old backend)
    tabular_dir = os.path.join(output_dir, "tabular")
    os.makedirs(tabular_dir, exist_ok=True)
    csv_path = os.path.join(tabular_dir, f"{city_name}_lc.csv")

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Land Cover Type', 'Pixel Count'])
        writer.writeheader()
        for class_name, count in counts_dict.items():
            writer.writerow({'Land Cover Type': class_name, 'Pixel Count': count})

    logger.info(f"Land cover stats saved to: {csv_path}")

    # ------------------------------------------------------------------
    # 4. Save raster
    # ------------------------------------------------------------------
    
    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)
    tif_path = os.path.join(spatial_dir, f"{city_name}_lc.tif")

    from rasterio.enums import Resampling
    lc_rio = fns.xee_to_rio(ds['Map'], resampling=Resampling.nearest)
    lc_rio.rio.to_raster(tif_path)

    logger.info(f"Land cover raster saved to: {tif_path}")

    if return_raster:
        return lc_rio, counts_dict

    return None
