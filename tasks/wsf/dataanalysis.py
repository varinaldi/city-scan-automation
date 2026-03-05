# import
import os
import math
import numpy as np
import pandas as pd
import rasterio
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling, calculate_default_transform
from scipy.ndimage import distance_transform_edt
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
        proximity_threshold: int = 5,
        return_df: bool = False
    ):
    """
    Harmonize WSF Evolution (1985-2015) with WSF Tracker (2016+).

    Process:
    1. Floor tracker era values to integer years
    2. Mode-resample tracker to evolution resolution
    3. Mask evolution by tracker 2016 extent (overlapping cells keep evolution year)
    4. Proximity-based backdating: non-overlapping 2016 cells are backdated to
       their nearest Evolution year; cells beyond proximity_threshold are kept as 2016
    5. Combine evolution (masked) + backdated 2016 + tracker 2017+
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
    proximity_threshold : int
        Max pixel distance for backdating non-overlapping 2016 cells.
        Cells beyond this distance are retained as true 2016 development.
    return_df : bool
        If True, return the harmonized stats DataFrame.

    Returns
    -------
    tuple or None
        (harmonized_array, harmonized_meta)
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
    # 2. Mode-resample tracker to evolution resolution
    # ------------------------------------------------------------------
    logger.info("Mode-resampling tracker to evolution resolution...")
    tracker_floor_3d = tracker_floor[np.newaxis, :, :].astype(np.float32)
    tracker_floor_meta = tracker_meta.copy()
    tracker_floor_meta.update({"dtype": "float32"})

    tracker_resampled, _ = _resample_to_target(
        tracker_floor_3d, tracker_floor_meta, evo_meta, method=Resampling.mode
    )
    tracker_resampled = tracker_resampled.squeeze()

    # ------------------------------------------------------------------
    # 3. Mask evolution by tracker 2016 extent
    #    Overlapping cells keep their original Evolution year
    # ------------------------------------------------------------------
    logger.info("Masking evolution by tracker 2016 extent...")
    wsf_2016_binary = (tracker_resampled == 2016)
    evo_masked = np.where(wsf_2016_binary, evolution, 0).astype(float)

    # ------------------------------------------------------------------
    # 4. Proximity-based backdating of non-overlapping 2016 cells
    #    Cells in tracker 2016 but NOT in evolution → backdate to nearest
    #    evolution year if within proximity_threshold, else keep as 2016
    # ------------------------------------------------------------------
    logger.info("Proximity-based backdating of non-overlapping 2016 cells...")

    # Non-overlapping: tracker says 2016 but evolution has no data
    non_overlapping = wsf_2016_binary & (evo_masked == 0)
    n_non_overlap = int(non_overlapping.sum())
    logger.info(f"  Non-overlapping 2016 cells: {n_non_overlap}")

    if n_non_overlap > 0:
        # Distance transform from evolution cells — gives distance to nearest evolution pixel
        evo_binary = (evo_masked > 0)
        if evo_binary.any():
            # EDT returns distance (in pixels) and indices of nearest source cell
            dist, indices = distance_transform_edt(~evo_binary, return_distances=True, return_indices=True)

            # For each non-overlapping cell, find nearest evolution year
            non_overlap_rows, non_overlap_cols = np.where(non_overlapping)
            nearest_rows = indices[0][non_overlap_rows, non_overlap_cols]
            nearest_cols = indices[1][non_overlap_rows, non_overlap_cols]
            nearest_years = evo_masked[nearest_rows, nearest_cols]
            distances = dist[non_overlap_rows, non_overlap_cols]

            # Within threshold: backdate to nearest evolution year
            within = distances <= proximity_threshold
            n_backdated = int(within.sum())
            n_kept_2016 = n_non_overlap - n_backdated
            logger.info(f"  Backdated to nearest evolution year: {n_backdated}")
            logger.info(f"  Retained as true 2016: {n_kept_2016}")

            # Apply backdating
            evo_masked[non_overlap_rows[within], non_overlap_cols[within]] = nearest_years[within]
            # Cells beyond threshold stay as 2016 (will be filled in step 5)
        else:
            logger.warning("  No evolution cells found — all 2016 cells retained as-is")

    # ------------------------------------------------------------------
    # 5. Combine: masked evolution + remaining 2016 + tracker 2017+
    # ------------------------------------------------------------------
    logger.info("Combining Evolution + Tracker...")
    harmonized = np.copy(evo_masked)

    # Fill remaining 2016 cells (those beyond proximity threshold + any not yet filled)
    tracker_2016_remaining = (tracker_resampled == 2016) & (harmonized == 0)
    harmonized[tracker_2016_remaining] = 2016

    # Fill with tracker 2017+
    tracker_post_2016 = np.copy(tracker_resampled)
    tracker_post_2016[tracker_resampled <= 2016] = 0
    fill_post = (harmonized == 0) & (tracker_post_2016 > 0)
    harmonized[fill_post] = tracker_post_2016[fill_post]

    # ------------------------------------------------------------------
    # 6. Save harmonized raster
    # ------------------------------------------------------------------
    harm_meta = evo_meta.copy()
    harm_meta.update({"dtype": "float32", "count": 1, "nodata": 0})
    harm_path = os.path.join(spatial_dir, f"{city_name}_wsf_harmonized.tif")
    with rasterio.open(harm_path, "w", **harm_meta) as dst:
        dst.write(harmonized.astype(np.float32)[np.newaxis, :, :])
    logger.info(f"Harmonized WSF saved to: {harm_path}")

    # ------------------------------------------------------------------
    # 7. Compute stats for harmonized, evolution-only, and tracker-only
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
    harm_stats = _cumulative_stats(harmonized, "WSF Harmonized")
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
