# import
import os
import math
import numpy as np
import pandas as pd
import rasterio
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling, calculate_default_transform
from scipy.ndimage import binary_dilation, binary_erosion
from utils.log_module import setup_logger

logger = setup_logger(__name__)


def _cell_areas_km2(meta):
    """Compute per-pixel area in km2 for a geographic (EPSG:4326) raster.
    Returns 2D array of pixel areas matching raster height/width."""
    transform = meta["transform"]
    height = meta["height"]
    width = meta["width"]

    # Pixel size in degrees
    dx = abs(transform.a)
    dy = abs(transform.e)

    # Center latitude of each row
    top_y = transform.f
    row_centers = np.array([top_y - (i + 0.5) * dy for i in range(height)])

    # Length of 1 degree at each latitude (in km)
    lat_rad = np.radians(row_centers)
    km_per_deg_lat = 111.132  # roughly constant
    km_per_deg_lon = 111.320 * np.cos(lat_rad)

    # Area per pixel = (dx * km/deg_lon) * (dy * km/deg_lat) for each row
    pixel_area = (dx * km_per_deg_lon) * (dy * km_per_deg_lat)  # shape (height,)

    # Broadcast to (height, width)
    return np.broadcast_to(pixel_area[:, np.newaxis], (height, width))


def stats_wsf(
        city_name: str,
        output_dir: str,
        dataset: str = "tracker",
        return_df: bool = False
    ):
    """
    Compute cumulative built-up area by year from a WSF raster.

    Works for both Tracker (fractional years) and Evolution (integer years).
    Floors values to integer years, computes cumulative area.

    Output CSV columns: year, cumulative_sq_km

    Parameters
    ----------
    city_name : str
        City name for locating raster file.
    output_dir : str
        Base output directory.
    dataset : str
        "tracker" or "evolution".
    return_df : bool
        If True, return the DataFrame.

    Returns
    -------
    pd.DataFrame or None
    """
    raster_path = os.path.join(output_dir, "spatial", f"{city_name}_wsf_{dataset}.tif")
    output_path = os.path.join(output_dir, "tabular", f"{city_name}_wsf_{dataset}.csv")

    logger.info(f"Computing WSF stats from: {os.path.basename(raster_path)}")

    if not os.path.exists(raster_path):
        logger.error(f"WSF raster not found at: {raster_path}")
        return None

    with rasterio.open(raster_path) as src:
        vals = src.read(1).astype(float)
        meta = src.meta.copy()

    # Cell areas in km2
    areas = _cell_areas_km2(meta)

    # Valid pixels: non-zero, non-nan, reasonable year range
    valid_mask = (vals > 0) & (~np.isnan(vals))
    vals_floored = np.floor(vals[valid_mask]).astype(int)
    area_valid = areas[valid_mask]

    if vals_floored.size == 0:
        logger.error("No valid WSF pixels found.")
        return None

    # Year range from data
    min_year = int(vals_floored.min())
    max_year = int(vals_floored.max())
    years = list(range(min_year, max_year + 1))

    # Cumulative area: for each year, sum areas of all pixels with value <= year
    cumulative = []
    for yr in years:
        area = float(area_valid[vals_floored <= yr].sum())
        cumulative.append({"year": yr, "cumulative_sq_km": area})

    df = pd.DataFrame(cumulative)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"WSF stats saved to: {output_path}")

    if return_df:
        return df
    return None


def _morphological_closing(binary_mask, kernel_size=7):
    """Apply morphological closing (dilation then erosion) with square kernel.
    Input: 2D boolean array. Returns: 2D boolean array."""
    k = np.ones((kernel_size, kernel_size), dtype=bool)
    dilated = binary_dilation(binary_mask, structure=k)
    closed = binary_erosion(dilated, structure=k)
    return closed


def _resample_to_target(data, src_meta, target_meta, method=Resampling.nearest):
    """Resample a raster array to match target raster's resolution and extent.
    Returns (resampled_array, resampled_meta)."""
    dst_crs = target_meta.get("crs", src_meta["crs"])
    dst_transform = target_meta["transform"]
    dst_width = target_meta["width"]
    dst_height = target_meta["height"]

    # Ensure 3D
    if data.ndim == 2:
        data = data[np.newaxis, :, :]

    destination = np.zeros((data.shape[0], dst_height, dst_width), dtype=data.dtype)

    reproject(
        source=data,
        destination=destination,
        src_transform=src_meta["transform"],
        src_crs=src_meta.get("crs", "EPSG:4326"),
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        dst_width=dst_width,
        dst_height=dst_height,
        resampling=method,
    )

    out_meta = target_meta.copy()
    out_meta.update({"count": data.shape[0], "dtype": str(data.dtype)})

    return destination, out_meta


def harmonize_wsf(
        city_name: str,
        output_dir: str,
        return_df: bool = False
    ):
    """
    Harmonize WSF Evolution (1985-2015) with WSF Tracker (2016+).

    Process:
    1. Floor tracker era values to integer years
    2. Morphological closing on tracker (per-year, 7x7 kernel) to bridge gaps
    3. Resample closed tracker to evolution resolution (nearest neighbor)
    4. Mask evolution: keep only where tracker has 2016 data (trim to tracker extent)
    5. Combine: evolution (masked) → tracker 2016 gap-fill → tracker 2017+
    6. Compute stats for harmonized, evolution-only, and tracker-only

    Output:
    - {city}_wsf_harmonized.tif (spatial)
    - {city}_wsf_harmonized.csv (tabular/processed) with columns:
      year, cumulative_sq_km, growth_percentage, source

    Parameters
    ----------
    city_name : str
        City name for locating raster files.
    output_dir : str
        Base output directory.
    return_df : bool
        If True, return the harmonized stats DataFrame.

    Returns
    -------
    pd.DataFrame or None
    """
    logger.info("Starting WSF harmonization...")

    spatial_dir = os.path.join(output_dir, "spatial")
    tracker_path = os.path.join(spatial_dir, f"{city_name}_wsf_tracker.tif")
    evo_path = os.path.join(spatial_dir, f"{city_name}_wsf_evolution.tif")

    if not os.path.exists(tracker_path):
        logger.error(f"WSF Tracker not found: {tracker_path}")
        return None
    if not os.path.exists(evo_path):
        logger.error(f"WSF Evolution not found: {evo_path}")
        return None

    # Load rasters
    with rasterio.open(tracker_path) as src:
        tracker_era = src.read(1).astype(float)
        tracker_meta = src.meta.copy()

    with rasterio.open(evo_path) as src:
        evolution = src.read(1).astype(float)
        evo_meta = src.meta.copy()

    # ------------------------------------------------------------------
    # 1. Floor tracker years (2016.5 → 2016, 2017.0 → 2017, etc.)
    # ------------------------------------------------------------------
    tracker_floor = np.where(tracker_era > 0, np.floor(tracker_era), 0).astype(float)

    # ------------------------------------------------------------------
    # 2. Morphological closing on tracker (per-year, 7x7 kernel)
    #    Fills small gaps between built-up pixels to match Landsat resolution
    # ------------------------------------------------------------------
    logger.info("Applying morphological closing to WSF Tracker...")
    unique_years = np.unique(tracker_floor[tracker_floor > 0]).astype(int)
    tracker_closed = np.copy(tracker_floor)

    for yr in sorted(unique_years):
        # Binary mask: pixels with this year
        yr_mask = (tracker_floor == yr)

        # Morphological closing: dilation then erosion (7x7 = ~70m at 10m resolution)
        yr_closed = _morphological_closing(yr_mask, kernel_size=7)

        # Fill only where tracker_closed has no data yet
        fill_mask = yr_closed & (tracker_closed == 0)
        tracker_closed[fill_mask] = yr

    # ------------------------------------------------------------------
    # 3. Resample closed tracker to evolution resolution (nearest neighbor)
    # ------------------------------------------------------------------
    logger.info("Resampling tracker to evolution resolution...")
    tracker_closed_3d = tracker_closed[np.newaxis, :, :].astype(np.float32)
    tracker_resampled_meta = tracker_meta.copy()
    tracker_resampled_meta.update({"dtype": "float32"})

    tracker_resampled, _ = _resample_to_target(
        tracker_closed_3d, tracker_resampled_meta, evo_meta, method=Resampling.nearest
    )
    tracker_resampled = tracker_resampled.squeeze()

    # ------------------------------------------------------------------
    # 4. Mask evolution by tracker's 2016 extent
    #    Keep evolution only where tracker has 2016 data
    # ------------------------------------------------------------------
    logger.info("Combining Evolution + Tracker...")

    # Step 1: trim evolution to where tracker has 2016 (matching R: mask by 2016 binary)
    wsf_2016_binary = (tracker_resampled == 2016)
    evo_trimmed = np.where(wsf_2016_binary, evolution, 0).astype(float)
    # Set 0 as nodata
    evo_trimmed[evo_trimmed == 0] = 0

    # Step 2: tracker 2016 pixels NOT already covered by evolution
    tracker_2016_only = np.copy(tracker_resampled)
    tracker_2016_only[tracker_resampled != 2016] = 0
    tracker_2016_only[evo_trimmed > 0] = 0

    # Step 3: combine — evolution first, then 2016 gap-fill, then 2017+
    harmonized = np.copy(evo_trimmed)
    # Fill with tracker 2016 where evolution is empty
    fill_2016 = (harmonized == 0) & (tracker_2016_only > 0)
    harmonized[fill_2016] = tracker_2016_only[fill_2016]
    # Fill with tracker 2017+ where harmonized is empty
    tracker_post_2016 = np.copy(tracker_resampled)
    tracker_post_2016[tracker_resampled <= 2016] = 0
    fill_post = (harmonized == 0) & (tracker_post_2016 > 0)
    harmonized[fill_post] = tracker_post_2016[fill_post]

    # ------------------------------------------------------------------
    # 5. Save harmonized raster
    # ------------------------------------------------------------------
    harm_meta = evo_meta.copy()
    harm_meta.update({"dtype": "float32", "count": 1, "nodata": 0})
    harm_path = os.path.join(spatial_dir, f"{city_name}_wsf_harmonized.tif")
    with rasterio.open(harm_path, "w", **harm_meta) as dst:
        dst.write(harmonized.astype(np.float32)[np.newaxis, :, :])
    logger.info(f"Harmonized WSF saved to: {harm_path}")

    # ------------------------------------------------------------------
    # 6. Compute stats for harmonized, evolution-only, and tracker-only
    #    Using the same cumulative area method as stats_wsf_evolution
    # ------------------------------------------------------------------
    logger.info("Computing harmonized stats...")
    areas = _cell_areas_km2(evo_meta)

    def _cumulative_stats(raster_2d, label):
        """Compute cumulative built-up area by year for a year-valued raster."""
        valid = (raster_2d > 0) & (~np.isnan(raster_2d))
        v = np.floor(raster_2d[valid]).astype(int)
        a = areas[valid]
        if v.size == 0:
            return pd.DataFrame(columns=["year", "cumulative_sq_km", "source"])
        yr_min, yr_max = int(v.min()), int(v.max())
        rows = []
        for yr in range(yr_min, yr_max + 1):
            cum = float(a[v <= yr].sum())
            rows.append({"year": yr, "cumulative_sq_km": cum, "source": label})
        return pd.DataFrame(rows)

    # Stats for each component
    evo_stats = _cumulative_stats(evolution, "WSF Evolution")
    harm_stats = _cumulative_stats(harmonized, "WSF Evolution (masked)")
    # Harmonized stats: only pre-2016 portion (evolution-based part)
    harm_stats = harm_stats[harm_stats["year"] <= 2015]
    tracker_stats = _cumulative_stats(tracker_resampled, "WSF Tracker")

    # Combine all stats
    combined = pd.concat([evo_stats, harm_stats, tracker_stats], ignore_index=True)
    combined = combined.sort_values(["source", "year"]).reset_index(drop=True)

    # Growth percentage per source group
    combined["growth_percentage"] = (
        combined.groupby("source")["cumulative_sq_km"]
        .pct_change() * 100
    ).round(3)

    # Save CSV
    tabular_dir = os.path.join(output_dir, "tabular", "processed")
    os.makedirs(tabular_dir, exist_ok=True)
    output_path = os.path.join(tabular_dir, f"{city_name}_wsf_harmonized.csv")
    combined.to_csv(output_path, index=False)
    logger.info(f"Harmonized WSF stats saved to: {output_path}")

    return harmonized.astype(np.float32)[np.newaxis, :, :], harm_meta
