# import
import os
import math
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.io import MemoryFile
from core.py.log_module import setup_logger

logger = setup_logger(__name__)

# GCS bucket path for WSF Tracker (private bucket, needs credentials)
GCS_TRACKER_BASE = "/vsigs/city-scan-global-private/wsf_tracker"

# DLR download URL template for WSF Evolution
DLR_EVO_URL = "https://download.geoservice.dlr.de/WSF_EVO/files/WSFevolution_v1_{x}_{y}/WSFevolution_v1_{x}_{y}.tif"


def _tile_grid(aoi_bounds):
    """Compute 2-degree tile grid coordinates covering the AOI extent.
    Returns list of (x, y) tuples matching DLR/WSF tile naming convention."""
    minx, miny, maxx, maxy = aoi_bounds

    # WSF Tracker: floor to nearest even number, step by 2
    x_seq = list(range(math.floor(minx - minx % 2), math.ceil(maxx) + 1, 2))
    # WSF Evolution uses floor(val/2)*2 rounding
    y_seq = list(range(math.floor(miny - miny % 2), math.ceil(maxy) + 1, 2))

    return [(x, y) for x in x_seq for y in y_seq]


def _merge_tiles(tile_datasets):
    """Merge multiple rasterio datasets into a single array + meta.
    Returns (merged_array, merged_meta)."""
    if len(tile_datasets) == 1:
        src = tile_datasets[0]
        data = src.read()
        meta = src.meta.copy()
        return data, meta

    merged, merged_transform = merge(tile_datasets)
    meta = tile_datasets[0].meta.copy()
    meta.update({
        "height": merged.shape[1],
        "width": merged.shape[2],
        "transform": merged_transform,
    })
    return merged, meta


def _crop_to_aoi(data, meta, aoi_shapes):
    """Mask a raster array to AOI polygon shapes.
    Returns (clipped_array, clipped_meta)."""
    with MemoryFile() as memfile:
        with memfile.open(**meta) as mem_dst:
            mem_dst.write(data)

        with memfile.open() as mem_src:
            clipped, clipped_transform = mask(mem_src, shapes=aoi_shapes, crop=True, nodata=0)
            clipped_meta = mem_src.meta.copy()
            clipped_meta.update({
                "height": clipped.shape[1],
                "width": clipped.shape[2],
                "transform": clipped_transform,
                "nodata": 0,
            })

    return clipped, clipped_meta


def datacollection(
        aoi: gpd.GeoDataFrame,
        city_name: str,
        output_dir: str,
        return_raster: bool = False
    ):
    """
    Download WSF Tracker and WSF Evolution, merge tiles, crop to AOI, save TIFs.

    WSF Tracker: Sentinel-2 (10m), 2016-2025, from GCS (2-degree tiles)
    WSF Evolution: Landsat (30m), 1985-2015, from DLR (2-degree tiles)

    Parameters
    ----------
    aoi : GeoDataFrame
        AOI polygon(s) in EPSG:4326.
    city_name : str
        City name for naming output files.
    output_dir : str
        Directory where clipped rasters will be saved.
    return_raster : bool
        If True, return dict of (array, meta) tuples.

    Returns
    -------
    dict or None
        Keys: 'tracker', 'evolution'. Values: (array, meta) tuples.
    """

    logger.info("Starting WSF data collection...")

    if aoi is None or aoi.empty:
        logger.error("AOI is empty. Cannot continue.")
        return None

    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    aoi_bounds = aoi.total_bounds  # (minx, miny, maxx, maxy)
    aoi_shapes = [geom.__geo_interface__ for geom in aoi.geometry]
    tiles = _tile_grid(aoi_bounds)

    arrays = {}
    metas = {}

    # ==================================================================
    # WSF Tracker — Sentinel-2 (10m), 2016-2025, from GCS
    # 2-degree tiles: WSFtracker_20160701-20250701_{x}_{y}.tif
    # ==================================================================
    logger.info("Collecting WSF Tracker...")

    tracker_datasets = []
    for x, y in tiles:
        fname = f"WSFtracker_20160701-20250701_{x}_{y}.tif"
        gcs_path = f"{GCS_TRACKER_BASE}/{fname}"
        try:
            src = rasterio.open(gcs_path)
            tracker_datasets.append(src)
            logger.info(f"  Opened tile: {fname}")
        except Exception:
            logger.info(f"  Tile not found (ocean/missing): {fname}")

    if len(tracker_datasets) == 0:
        logger.error("No WSF Tracker tiles found for this area")
    else:
        # Merge tiles and crop to AOI
        merged_data, merged_meta = _merge_tiles(tracker_datasets)

        # Close rasterio handles
        for src in tracker_datasets:
            src.close()

        tracker_clipped, tracker_meta = _crop_to_aoi(merged_data, merged_meta, aoi_shapes)

        # Convert mode values to fractional years (2016.5, 2017.0, ...)
        # Band 1 = mode (settlement class), values 1..N map to years starting at 2016.5 with 0.5 step
        mode_band = tracker_clipped[0].astype(float)
        max_mode = int(np.nanmax(mode_band[mode_band > 0])) if np.any(mode_band > 0) else 1
        era_lut = np.zeros(max_mode + 1, dtype=np.float32)
        for i in range(1, max_mode + 1):
            era_lut[i] = 2016.0 + i * 0.5
        # Apply lookup — 0 stays 0 (nodata)
        era_band = era_lut[mode_band.astype(int).clip(0, max_mode)]
        era_band[mode_band <= 0] = 0

        # Save with era values (float years)
        tracker_out_meta = tracker_meta.copy()
        tracker_out_meta.update({"dtype": "float32", "count": 1})
        tracker_path = os.path.join(spatial_dir, f"{city_name}_wsf_tracker.tif")
        with rasterio.open(tracker_path, "w", **tracker_out_meta) as dst:
            dst.write(era_band[np.newaxis, :, :])
            dst.set_band_description(1, "era")
        logger.info(f"WSF Tracker saved to: {tracker_path}")

        if return_raster:
            arrays['tracker'] = era_band[np.newaxis, :, :]
            metas['tracker'] = tracker_out_meta

    # ==================================================================
    # WSF Evolution — Landsat (30m), 1985-2015, from DLR
    # 2-degree tiles: WSFevolution_v1_{x}_{y}.tif
    # Direct download (tiles are small enough)
    # ==================================================================
    logger.info("Collecting WSF Evolution...")

    evo_datasets = []
    for x, y in tiles:
        tile_name = f"WSFevolution_v1_{x}_{y}"
        url = f"/vsicurl/https://download.geoservice.dlr.de/WSF_EVO/files/{tile_name}/{tile_name}.tif"
        try:
            src = rasterio.open(url)
            evo_datasets.append(src)
            logger.info(f"  Opened tile: {tile_name}")
        except Exception:
            logger.info(f"  Tile not found (ocean/missing): {tile_name}")

    if len(evo_datasets) == 0:
        logger.error("No WSF Evolution tiles found for this area")
    else:
        # Merge tiles and crop to AOI
        merged_data, merged_meta = _merge_tiles(evo_datasets)

        for src in evo_datasets:
            src.close()

        evo_clipped, evo_meta = _crop_to_aoi(merged_data, merged_meta, aoi_shapes)

        # Save evolution raster
        evo_path = os.path.join(spatial_dir, f"{city_name}_wsf_evolution.tif")
        with rasterio.open(evo_path, "w", **evo_meta) as dst:
            dst.write(evo_clipped)
        logger.info(f"WSF Evolution saved to: {evo_path}")

        if return_raster:
            arrays['evolution'] = evo_clipped
            metas['evolution'] = evo_meta

    logger.info("WSF data collection complete.")

    if return_raster:
        return arrays, metas

    return None
