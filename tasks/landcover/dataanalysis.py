from utils.log_module import setup_logger
logger = setup_logger(__name__)

import os
import csv
import numpy as np
import rioxarray

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


def dataanalysis(city_name, output_dir):
    """Compute land cover stats CSV from the raster."""

    spatial_dir = os.path.join(output_dir, "spatial")
    tif_path = os.path.join(spatial_dir, f"{city_name}_lc.tif")
    lc_data = rioxarray.open_rasterio(tif_path).isel(band=0).values

    # Frequency histogram
    valid = lc_data[~np.isnan(lc_data)].astype(int)
    unique, counts = np.unique(valid, return_counts=True)
    pixel_counts = dict(zip(unique, counts))

    counts_dict = {}
    for class_val, class_name in CLASS_VALUES.items():
        counts_dict[class_name] = pixel_counts.get(class_val, 0)

    tabular_dir = os.path.join(output_dir, "tabular")
    os.makedirs(tabular_dir, exist_ok=True)
    csv_path = os.path.join(tabular_dir, f"{city_name}_lc.csv")

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Land Cover Type', 'Pixel Count'])
        writer.writeheader()
        for class_name, count in counts_dict.items():
            writer.writerow({'Land Cover Type': class_name, 'Pixel Count': count})

    logger.info(f"Land cover stats saved to: {csv_path}")
    return counts_dict
