#!/usr/bin/env python3
"""
Download GHS built-up data from Earth Engine using computePixels (no Drive/GCS needed)
Usage: python download_ghs_buildup.py <city-directory-name> [--year YEAR]
Example: python download_ghs_buildup.py 2025-10-senegal-diourbel --year 2020
"""

import ee
import numpy as np
import rasterio
from rasterio.transform import from_bounds
import geopandas as gpd
import os
import sys
import re
from glob import glob
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_city_info(city_dir_name):
    """Extract city name from directory"""
    match = re.search(r'\d{4}-\d{2}-[a-z]+-(.+)$', city_dir_name)
    if match:
        return match.group(1)
    return None

def create_grid_tiles(bounds, tile_size_degrees=0.1):
    """Create grid tiles from bounds to stay under EE size limits"""
    minx, miny, maxx, maxy = bounds

    tiles = []
    y = miny
    while y < maxy:
        x = minx
        while x < maxx:
            tile_bounds = [
                x,
                y,
                min(x + tile_size_degrees, maxx),
                min(y + tile_size_degrees, maxy)
            ]
            tiles.append(tile_bounds)
            x += tile_size_degrees
        y += tile_size_degrees

    return tiles

def download_tile_computepixels(image, bounds, scale, band_names):
    """Download single tile using computePixels API"""
    try:
        # Calculate dimensions
        width = int((bounds[2] - bounds[0]) * 111320 / scale)  # degrees to meters
        height = int((bounds[3] - bounds[1]) * 111320 / scale)

        # Build affine transform
        x_scale = (bounds[2] - bounds[0]) / width
        y_scale = -(bounds[3] - bounds[1]) / height

        # Request data
        pixels = ee.data.computePixels({
            'expression': image,
            'fileFormat': 'GEO_TIFF',
            'grid': {
                'dimensions': {'width': width, 'height': height},
                'affineTransform': {
                    'scaleX': x_scale,
                    'shearX': 0,
                    'translateX': bounds[0],
                    'shearY': 0,
                    'scaleY': y_scale,
                    'translateY': bounds[3]
                },
                'crsCode': 'EPSG:4326'
            }
        })

        # Save to temp file and read
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            tmp.write(pixels)
            tmp_path = tmp.name

        # Read the GeoTIFF
        with rasterio.open(tmp_path) as src:
            data = src.read()
            transform = src.transform

        os.unlink(tmp_path)

        return data, transform, bounds

    except Exception as e:
        print(f"  Error downloading tile {bounds}: {e}")
        return None, None, bounds

def mosaic_tiles(tiles_data, full_bounds, scale):
    """Mosaic tiles into single array"""
    if not tiles_data:
        return None, None

    # Calculate full dimensions
    width = int((full_bounds[2] - full_bounds[0]) * 111320 / scale)
    height = int((full_bounds[3] - full_bounds[1]) * 111320 / scale)

    # Get number of bands
    n_bands = tiles_data[0][0].shape[0]

    # Initialize output
    mosaic = np.zeros((n_bands, height, width), dtype=tiles_data[0][0].dtype)

    for data, transform, tile_bounds in tiles_data:
        # Calculate position in mosaic
        col_start = int((tile_bounds[0] - full_bounds[0]) / (full_bounds[2] - full_bounds[0]) * width)
        row_start = int((full_bounds[3] - tile_bounds[3]) / (full_bounds[3] - full_bounds[1]) * height)

        # Place tile
        tile_height, tile_width = data.shape[1], data.shape[2]
        mosaic[:, row_start:row_start+tile_height, col_start:col_start+tile_width] = data

    # Create transform for full mosaic
    full_transform = from_bounds(*full_bounds, width, height)

    return mosaic, full_transform

def main():
    parser = argparse.ArgumentParser(description='Download GHS built-up data from Earth Engine')
    parser.add_argument('city_dir', help='City directory name (e.g., 2025-10-senegal-diourbel)')
    parser.add_argument('--year', type=int, default=2020, help='Year to download (default: 2020)')
    parser.add_argument('--scale', type=int, default=100, help='Resolution in meters (default: 100)')
    parser.add_argument('--tile-size', type=float, default=0.1, help='Tile size in degrees (default: 0.1)')

    args = parser.parse_args()

    city_dir_name = args.city_dir
    year = args.year
    scale = args.scale
    tile_size = args.tile_size

    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    city_dir = os.path.join(project_root, "mnt", city_dir_name)
    user_dir = os.path.join(city_dir, "01-user-input")
    temporal_dir = os.path.join(city_dir, "02-process-output", "temporal")

    if not os.path.exists(city_dir):
        print(f"Error: City directory not found: {city_dir}")
        sys.exit(1)

    city_name = extract_city_info(city_dir_name)
    if not city_name:
        print(f"Error: Could not extract city name from: {city_dir_name}")
        sys.exit(1)

    print(f"Processing: {city_dir_name}")
    print(f"City: {city_name}")
    print(f"Year: {year}")
    print(f"Scale: {scale}m\n")

    # Initialize Earth Engine
    print("Initializing Earth Engine...")
    try:
        ee.Initialize()
        print("  Earth Engine initialized\n")
    except Exception as e:
        print(f"  Error: {e}")
        print("  Run: earthengine authenticate")
        sys.exit(1)

    # Load AOI
    print("Loading AOI...")
    aoi_files = glob(os.path.join(user_dir, 'AOI', '*.shp'))
    if not aoi_files:
        print(f"Error: No AOI shapefile found in {user_dir}/AOI")
        sys.exit(1)

    aoi = gpd.read_file(aoi_files[0]).to_crs("EPSG:4326")
    bounds = aoi.total_bounds
    print(f"  AOI bounds: {bounds}\n")

    # Load GHS built-up image
    print(f"Loading GHS Built-up {year}...")
    ghs = ee.ImageCollection("JRC/GHSL/P2023A/GHS_BUILT_S") \
        .filterDate(f'{year}-01-01', f'{year}-12-31') \
        .first() \
        .clip(ee.Geometry.Rectangle(bounds.tolist()))

    band_names = ghs.bandNames().getInfo()
    print(f"  Bands: {band_names}\n")

    # Create tiles
    tiles = create_grid_tiles(bounds, tile_size_degrees=tile_size)
    print(f"Created {len(tiles)} tiles ({tile_size} degrees each)\n")

    # Download tiles
    print("Downloading tiles...")
    tiles_data = []

    for i, tile_bounds in enumerate(tiles, 1):
        print(f"  Tile {i}/{len(tiles)}: {tile_bounds}")
        data, transform, bounds_used = download_tile_computepixels(ghs, tile_bounds, scale, band_names)
        if data is not None:
            tiles_data.append((data, transform, bounds_used))

    if not tiles_data:
        print("\nError: No tiles downloaded successfully")
        sys.exit(1)

    print(f"\nSuccessfully downloaded {len(tiles_data)}/{len(tiles)} tiles")

    # Mosaic tiles
    print("\nMosaicking tiles...")
    mosaic, mosaic_transform = mosaic_tiles(tiles_data, bounds, scale)

    if mosaic is None:
        print("Error: Failed to create mosaic")
        sys.exit(1)

    print(f"  Mosaic shape: {mosaic.shape}")

    # Save output
    os.makedirs(temporal_dir, exist_ok=True)
    output_file = os.path.join(temporal_dir, f'{city_name}_ghs_built_{year}.tif')

    print(f"\nSaving to: {output_file}")

    with rasterio.open(
        output_file, 'w',
        driver='GTiff',
        height=mosaic.shape[1],
        width=mosaic.shape[2],
        count=mosaic.shape[0],
        dtype=mosaic.dtype,
        crs='EPSG:4326',
        transform=mosaic_transform,
        compress='lzw'
    ) as dst:
        dst.write(mosaic)
        dst.descriptions = band_names

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\nSuccess!")
    print(f"  File size: {file_size:.1f} MB")
    print(f"  Output: {output_file}")

if __name__ == "__main__":
    main()
