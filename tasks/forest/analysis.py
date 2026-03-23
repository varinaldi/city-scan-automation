import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling
from core.py.log_module import setup_logger

logger = setup_logger(__name__)


# From Caroline's clean.py — clean_deforestation_area()
def compute_histogram(
        city_name: str,
        output_dir: str,
        base_year: int = 2000,
        auto_align: bool = True,
        return_df: bool = False
    ):
    """
    Compute year-over-year deforestation from forest cover and deforestation rasters.
    Produces deforestation_area.csv with columns: year, forest_remaining,
    deforested_this_year, cumulative_deforested, percent_forest_remaining, percent_forest_lost.
    """

    logger.info("Starting deforestation analysis…")

    spatial_dir = os.path.join(output_dir, "spatial")
    forest_path = os.path.join(spatial_dir, f"{city_name}_forest_cover23.tif")
    deforest_path = os.path.join(spatial_dir, f"{city_name}_deforestation.tif")

    if not os.path.exists(forest_path):
        logger.error(f"Forest cover raster not found at: {forest_path}")
        return None
    if not os.path.exists(deforest_path):
        logger.error(f"Deforestation raster not found at: {deforest_path}")
        return None

    try:
        with rasterio.open(forest_path) as forest_src:
            forest_data = forest_src.read(1)
            forest_nodata = forest_src.nodata
            forest_transform = forest_src.transform
            forest_crs = forest_src.crs
            forest_shape = forest_src.shape
            forest_bounds = forest_src.bounds

        with rasterio.open(deforest_path) as deforest_src:
            deforest_data_original = deforest_src.read(1)
            deforest_nodata = deforest_src.nodata
            deforest_transform = deforest_src.transform
            deforest_crs = deforest_src.crs
            deforest_shape = deforest_src.shape
            deforest_bounds = deforest_src.bounds

        # Check alignment
        same_crs = forest_crs == deforest_crs
        same_shape = forest_shape == deforest_shape
        same_bounds = (abs(forest_bounds.left - deforest_bounds.left) < 1e-6 and
                      abs(forest_bounds.right - deforest_bounds.right) < 1e-6 and
                      abs(forest_bounds.top - deforest_bounds.top) < 1e-6 and
                      abs(forest_bounds.bottom - deforest_bounds.bottom) < 1e-6)
        same_transform = forest_transform == deforest_transform
        is_aligned = same_crs and same_shape and same_bounds and same_transform

        if not is_aligned:
            if auto_align:
                logger.info("Auto-aligning deforestation to match forest cover...")
                deforest_data = np.empty(forest_shape, dtype=deforest_data_original.dtype)
                reproject(
                    source=deforest_data_original,
                    destination=deforest_data,
                    src_transform=deforest_transform,
                    src_crs=deforest_crs,
                    src_nodata=deforest_nodata,
                    dst_transform=forest_transform,
                    dst_crs=forest_crs,
                    dst_nodata=deforest_nodata,
                    resampling=Resampling.nearest
                )
            else:
                logger.error("TIF files are not aligned. Set auto_align=True.")
                return None
        else:
            deforest_data = deforest_data_original

        # Use forest cover as primary mask
        if forest_nodata is not None:
            valid_mask = forest_data != forest_nodata
        else:
            valid_mask = ~np.isnan(forest_data) & np.isfinite(forest_data)

        forest_valid = forest_data[valid_mask]
        deforest_valid = deforest_data[valid_mask].copy()

        if deforest_nodata is not None:
            deforest_valid[deforest_valid == deforest_nodata] = 0
        deforest_valid[np.isnan(deforest_valid)] = 0

        baseline_forest = int(np.sum(forest_valid == 1))

    except Exception as e:
        logger.error(f"Error reading TIF files: {e}")
        return None

    if baseline_forest == 0:
        logger.error("No forest pixels found.")
        return None

    # Build year-over-year data
    result_data = [{
        'year': base_year,
        'forest_remaining': baseline_forest,
        'deforested_this_year': 0,
        'cumulative_deforested': 0,
        'percent_forest_remaining': 100.0,
        'percent_forest_lost': 0.0
    }]

    deforest_years = np.unique(deforest_valid[deforest_valid > 0])
    cumulative_deforested = 0

    for year_code in sorted(deforest_years):
        actual_year = base_year + int(year_code)
        deforested_count = int(np.sum((forest_valid == 1) & (deforest_valid == year_code)))
        cumulative_deforested += deforested_count
        forest_remaining = baseline_forest - cumulative_deforested

        result_data.append({
            'year': actual_year,
            'forest_remaining': int(forest_remaining),
            'deforested_this_year': int(deforested_count),
            'cumulative_deforested': int(cumulative_deforested),
            'percent_forest_remaining': round((forest_remaining / baseline_forest) * 100, 2),
            'percent_forest_lost': round((cumulative_deforested / baseline_forest) * 100, 2)
        })

    result_df = pd.DataFrame(result_data)

    # Save
    tabular_dir = os.path.join(output_dir, "tabular")
    os.makedirs(tabular_dir, exist_ok=True)
    output_path = os.path.join(tabular_dir, f"{city_name}_deforestation_area.csv")

    try:
        result_df.to_csv(output_path, index=False)
        logger.info(f"Deforestation histogram saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving histogram CSV: {e}")

    if return_df:
        return result_df
    return None
