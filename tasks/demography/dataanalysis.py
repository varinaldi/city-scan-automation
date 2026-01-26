# import
import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import pandas as pd
from utils.log_module import setup_logger
import numpy as np
logger = setup_logger(__name__)

def demographic_aggregate(
    city_name: str,
    output_dir: str,
    demographic_raster: str | None = None,
    clipped_array: np.ndarray | None = None,
    clipped_meta: dict | None = None,
    return_df: bool = True,
):
    """
    Aggregate a multi-band WorldPop demographic raster into tabular format.

    The function first attempts to use an in-memory raster (array + metadata).
    If not provided, it reads a multi-band GeoTIFF from disk.

    Parameters
    ----------
    city_name : str
        City name used for labeling outputs.
    output_dir : str
        Base output directory.
    demographic_raster : str, optional
        Path to multi-band demographic raster. If None, defaults to
        ``{output_dir}/spatial/{city_name}_demographic.tif``.
    clipped_array : np.ndarray, optional
        In-memory raster array with shape (bands, height, width).
    clipped_meta : dict, optional
        Raster metadata dictionary corresponding to ``clipped_array``.
    return_df : bool, default True
        If True, return the aggregated DataFrame.

    Returns
    -------
    pandas.DataFrame or None
        Aggregated demographic table if ``return_df=True``.
    """

    # ------------------------------------------------------------------
    # Prepare output directory
    # ------------------------------------------------------------------
    tabular_dir = os.path.join(output_dir, "tabular")
    os.makedirs(tabular_dir, exist_ok=True)

    rows = []

    # ------------------------------------------------------------------
    # Case 1: Use in-memory raster (preferred if provided)
    # ------------------------------------------------------------------
    if clipped_array is not None and clipped_meta is not None:

        band_descriptions = clipped_meta.get("descriptions")

        if band_descriptions is None:
            raise ValueError("clipped_meta must contain band descriptions")

        for i, band in enumerate(clipped_array):
            desc = band_descriptions[i]
            sex, age_group = desc.split("_", 1)

            population = float(band.sum())

            rows.append({
                "city": city_name,
                "sex": sex,
                "age_group": age_group,
                "population": population
            })

    # ------------------------------------------------------------------
    # Case 2: Read raster from disk
    # ------------------------------------------------------------------
    else:
        if demographic_raster is None:
            demographic_raster = os.path.join(
                output_dir,
                "spatial",
                f"{city_name}_worldpop_demographics.tif"
            )

        logger.info(f"Reading demographic raster from disk: {demographic_raster}")

        with rasterio.open(demographic_raster) as src:

            for band_index in range(1, src.count + 1):
                band = src.read(band_index)
                desc = src.descriptions[band_index - 1]

                sex, age_group = desc.split("_", 1)

                population = float(band.sum())

                rows.append({
                    "city": city_name,
                    "sex": sex,
                    "age_group": age_group,
                    "population": population
                })

    # ------------------------------------------------------------------
    # Convert to DataFrame and write output
    # ------------------------------------------------------------------
    df = pd.DataFrame(rows)

    output_csv = os.path.join(
        tabular_dir,
        f"{city_name}_demographic.csv"
    )
    df.to_csv(output_csv, index=False)

    logger.info(f"Saved demographic table: {output_csv}")

    if return_df:
        return df

    return None

