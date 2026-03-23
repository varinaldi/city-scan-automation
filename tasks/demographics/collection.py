# import
import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import pandas as pd
from core.py.log_module import setup_logger
import numpy as np
logger = setup_logger(__name__)


def age_label(age):
    if age == 0:
        return "0-1"
    elif age == 1:
        return "1-4"
    elif age == 80:
        return "80+"
    else:
        return f"{age}-{age+4}"


def datacollection(
    aoi: gpd.GeoDataFrame,
    city_name: str,
    country_iso3: str,
    output_dir: str,
    return_raster: bool = False,
):
    """
    Download, clip, and stack WorldPop age–sex rasters into a single multi-band GeoTIFF.

    Parameters
    ----------
    aoi : GeoDataFrame
        AOI polygon(s).
    city_name : str
        City name for naming output files.
    country_iso3 : str
        ISO3 country code (e.g. "IDN", "KHM").
    output_dir : str
        Directory where clipped raster will be saved.
    return_raster : bool, default False
        If True, return (array, metadata) for the stacked raster.

    Returns
    -------
    (np.ndarray, dict) or None
        Multi-band raster array and metadata if return_raster=True.
    """

    logger.info("Starting WorldPop demographic data collection")

    AGE_GROUPS = [0, 1] + list(range(5, 85, 5))  # 18 groups
    SEXES = ["f", "m"]

    if aoi is None or aoi.empty or aoi.crs is None:
        logger.error("Invalid AOI")
        return None

    bucket_base = "https://storage.googleapis.com/city-scan-global-public/"
    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    output_raster = os.path.join(
        spatial_dir,
        f"{city_name}_worldpop_demographics.tif"
    )

    band_arrays = []
    band_descriptions = []

    for sex in SEXES:
        for age in AGE_GROUPS:

            blob = (
                f"world_population_age_structures/"
                f"{country_iso3.lower()}_{sex}_{age}_2020_constrained.tif"
            )
            raster_path = f"/vsicurl/{bucket_base}{blob}"

            logger.info(f"Reading {blob}")

            with rasterio.open(raster_path) as src:

                # Reproject AOI if needed
                if aoi.crs != src.crs:
                    aoi_proj = aoi.to_crs(src.crs)
                else:
                    aoi_proj = aoi

                shapes = [g.__geo_interface__ for g in aoi_proj.geometry]

                clipped, transform = mask(
                    src,
                    shapes=shapes,
                    crop=True,
                    nodata=0
                )

                clipped[clipped == src.nodata] = 0
                band_arrays.append(clipped[0])

                band_descriptions.append(
                    f"{sex}_{age_label(age)}"
                )

                # Capture metadata once
                if len(band_arrays) == 1:
                    meta = src.meta.copy()
                    meta.update({
                        "count": len(SEXES) * len(AGE_GROUPS),
                        "height": clipped.shape[1],
                        "width": clipped.shape[2],
                        "transform": transform,
                        "nodata": 0
                    })

    # Write multi-band raster to disk
    with rasterio.open(output_raster, "w", **meta) as dst:
        for i, band in enumerate(band_arrays, start=1):
            dst.write(band, i)
            dst.set_band_description(i, band_descriptions[i - 1])

    logger.info(f"Saved multi-band raster: {output_raster}")

    # Optional in-memory return
    if return_raster:
        stacked_array = np.stack(band_arrays, axis=0)
        return stacked_array, meta

    return None

