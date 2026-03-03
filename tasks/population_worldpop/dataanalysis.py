import os
import re
import numpy as np
import pandas as pd
import rasterio
from utils.log_module import setup_logger

logger = setup_logger(__name__)


def compute_stats(
        city_name: str,
        output_dir: str,
        clipped_image=None,
        clipped_meta=None,
        return_df: bool = False
    ):
    """
    Perform statistics on clipped population raster.

    Parameters
    ----------
    city_name : str
        City name used for locating the clipped raster file.
    output_dir : str
        Base output directory.
    clipped_image : np.ndarray, optional
        In-memory clipped raster array from datacollection().
    clipped_meta : dict, optional
        Raster metadata from datacollection().
    return_df : bool
        If True, return dataframe, default is False.

    Returns
    -------
    stats_df : pandas.DataFrame
        DataFrame containing min, p25, median, mean, p75, max, sum.
    """

    logger.info("Starting WorldPop raster analysis…")

    # -----------------------------------------------------
    # 1. Load raster from disk if not provided
    # -----------------------------------------------------
    if clipped_image is None or clipped_meta is None:
        raster_path = os.path.join(output_dir, "spatial", f"{city_name}_population.tif")

        if not os.path.exists(raster_path):
            logger.error(f"Clipped raster not found at: {raster_path}")
            return None

        logger.info(f"Loading clipped raster from disk: {raster_path}")

        try:
            with rasterio.open(raster_path) as src:
                clipped_image = src.read()
                clipped_meta = src.meta
        except Exception as e:
            logger.error(f"Failed to load raster: {e}")
            return None
    else:
        logger.info("Using in-memory raster from datacollection().")

    # -----------------------------------------------------
    # 2. Prepare raster data for statistics
    # -----------------------------------------------------
    # Convert to 1D and remove zeros/nodata
    arr = clipped_image.squeeze().astype(float)
    valid = arr[arr > 0]

    if valid.size == 0:
        logger.error("Raster contains no valid values. Cannot compute statistics.")
        return None

    # -----------------------------------------------------
    # 3. Compute statistics
    # -----------------------------------------------------
    stats = {
        "min": float(np.min(arr)),
        "p5": float(np.percentile(arr, 5)),
        "p25": float(np.percentile(arr, 25)),
        "median": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "p75": float(np.percentile(arr, 75)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr)),
        "sum": float(np.sum(arr)),
        "stdev": float(np.std(arr, ddof=0)),
        "count": int(arr.size)
    }

    stats_df = pd.DataFrame([stats])
    logger.info("Raster statistics calculated successfully.")

    # -----------------------------------------------------
    # 4. Save output CSV
    # -----------------------------------------------------
    tabular_dir = os.path.join(output_dir, "tabular")
    os.makedirs(tabular_dir, exist_ok=True)

    output_path = os.path.join(tabular_dir, f"{city_name}_population_stats.csv")

    try:
        stats_df.to_csv(output_path, index=False)
        logger.info(f"Population statistics saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving statistics CSV: {e}")

    if return_df:
        return stats_df

    return None


def stats_worldpop(
        city_name: str,
        output_dir: str,
        dataset: str = "worldpop_2015_2030",
        return_df: bool = False
    ):
    """
    Compute total population per year from a multi-band WorldPop raster.

    Works for both Global 1 (2000-2020) and Global 2 (2015-2030).
    Reads band descriptions to extract years.

    Parameters
    ----------
    city_name : str
        City name for locating raster file.
    output_dir : str
        Base output directory.
    dataset : str
        "worldpop_2000_2020" or "worldpop_2015_2030".
    return_df : bool
        If True, return the DataFrame.

    Returns
    -------
    pd.DataFrame or None
    """
    raster_path = os.path.join(output_dir, "spatial", f"{city_name}_{dataset}.tif")
    output_path = os.path.join(output_dir, "tabular", f"{city_name}_{dataset}.csv")

    logger.info(f"Computing WorldPop yearly population stats from: {os.path.basename(raster_path)}")

    if not os.path.exists(raster_path):
        logger.error(f"WorldPop raster not found at: {raster_path}")
        return None

    with rasterio.open(raster_path) as src:
        nodata = src.nodata
        rows = []
        for i in range(1, src.count + 1):
            band = src.read(i).astype(float)
            desc = src.descriptions[i - 1]  # e.g. "pop_2020"

            # Extract year from band description
            year_match = re.search(r'\d{4}', desc) if desc else None
            year = int(year_match.group()) if year_match else i

            # Mask nodata and negative values before summing
            if nodata is not None:
                band[band == nodata] = np.nan
            band[band < 0] = np.nan

            population = float(np.nansum(band))
            rows.append({"year": year, "population": population})

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"WorldPop yearly stats saved to: {output_path}")

    if return_df:
        return df

    return None


if __name__ == "__main__":
    compute_stats(city_name="testcity", output_dir="./outputs")
