#!/usr/bin/env python3
"""
Download GHS Built-S data directly from JRC (no authentication needed)
Usage: python download_ghs_buildup_direct.py <city-directory-name> [--year YEAR]
Example: python download_ghs_buildup_direct.py 2025-10-senegal-diourbel --year 2020
"""

import os
import sys
import re
import argparse
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
import requests
import zipfile
import tempfile
import io
from pathlib import Path
from glob import glob
from rasterio.io import MemoryFile

def extract_city_info(city_dir_name):
    """Extract city name from directory"""
    match = re.search(r'\d{4}-\d{2}-[a-z]+-(.+)$', city_dir_name)
    if match:
        return match.group(1)
    return None

def download_tile_shapefile():
    """Download GHSL tile shapefile to determine which tiles to download"""
    tile_shp_url = "https://ghsl.jrc.ec.europa.eu/download/GHSL_data_54009_shapefile.zip"

    print("  Downloading GHSL tile shapefile...")

    try:
        response = requests.get(tile_shp_url, timeout=60)
        response.raise_for_status()

        # Create temp file for ZIP
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp.write(response.content)
            tmp_zip = tmp.name

        # Find and read shapefile from ZIP
        with zipfile.ZipFile(tmp_zip, "r") as z:
            shp_files = [f for f in z.namelist() if f.endswith(".shp")]
            if not shp_files:
                raise FileNotFoundError("No shapefile found in ZIP")

            shp_name = shp_files[0]
            print(f"  Found: {shp_name}")

            # Mollweide projection (native GHSL projection)
            mollweide_proj = "+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
            tile_gdf = gpd.read_file(f"zip://{tmp_zip}!{shp_name}").to_crs(mollweide_proj)

        os.remove(tmp_zip)
        return tile_gdf

    except Exception as e:
        print(f"  Error downloading tile shapefile: {e}")
        return None

def download_ghs_tile(tile_code, year):
    """Download a single GHS tile ZIP from JRC server and return rasterio dataset"""

    # GHS Built-S URL pattern (ZIP files, not direct TIF)
    base_url = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_S_GLOBE_R2023A"
    sub_path = f"GHS_BUILT_S_E{year}_GLOBE_R2023A_54009_100/V1-0/tiles"
    filename = f"GHS_BUILT_S_E{year}_GLOBE_R2023A_54009_100_V1_0_{tile_code}.zip"
    url = f"{base_url}/{sub_path}/{filename}"

    print(f"    Downloading {tile_code}...")

    try:
        response = requests.get(url, timeout=90)
        response.raise_for_status()

        # Open ZIP in memory and extract TIF
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            tif_files = [f for f in z.namelist() if f.endswith(".tif")]
            if not tif_files:
                print(f"      No TIF found in ZIP for {tile_code}")
                return None

            # Read TIF data
            tif_data = z.read(tif_files[0])

            # Check file size (GHSL tiles should be > 1MB)
            if len(tif_data) < 1_000_000:
                print(f"      Skipping tiny/invalid TIF: {len(tif_data)} bytes")
                return None

            # Open with rasterio MemoryFile
            memfile = MemoryFile(tif_data)
            dataset = memfile.open()

            print(f"      Success: {len(tif_data) / (1024*1024):.1f} MB")
            return dataset, memfile  # Return both to keep memfile alive

    except requests.exceptions.RequestException as e:
        print(f"      Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Download GHS Built-S data from JRC')
    parser.add_argument('city_dir', help='City directory name')
    parser.add_argument('--year', type=int, help='Single year to download')
    parser.add_argument('--all-years', action='store_true', help='Download all available years')
    args = parser.parse_args()

    city_dir_name = args.city_dir

    # GHS Built-S R2023A available years (historical data only, projections may not be available)
    available_years = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020]

    print(f"Note: Only historical years (1975-2020) are currently available")
    print(f"Projection years (2025, 2030) may not be accessible on JRC server\n")

    if args.all_years:
        years = available_years
    elif args.year:
        if args.year not in available_years:
            print(f"Error: Year {args.year} not available")
            print(f"Available years: {', '.join(map(str, available_years))}")
            sys.exit(1)
        years = [args.year]
    else:
        years = [2020]  # Default

    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    city_dir = os.path.join(project_root, "mnt", city_dir_name)
    user_dir = os.path.join(city_dir, "01-user-input")
    temporal_dir = os.path.join(city_dir, "02-process-output", "temporal")

    # Create temp directory for tiles
    temp_dir = os.path.join(project_root, "cache", "ghs_tiles")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(temporal_dir, exist_ok=True)

    if not os.path.exists(city_dir):
        print(f"Error: City directory not found: {city_dir}")
        sys.exit(1)

    city_name = extract_city_info(city_dir_name)
    if not city_name:
        print(f"Error: Could not extract city name from: {city_dir_name}")
        sys.exit(1)

    print(f"Processing: {city_dir_name}")
    print(f"City: {city_name}")
    print(f"Years to download: {', '.join(map(str, years))}\n")

    # Load AOI
    print("Loading AOI...")
    aoi_files = glob(os.path.join(user_dir, 'AOI', '*.shp'))
    if not aoi_files:
        print(f"Error: No AOI shapefile found")
        sys.exit(1)

    aoi = gpd.read_file(aoi_files[0]).to_crs("EPSG:4326")
    print(f"  AOI loaded\n")

    # Download tile shapefile
    print("Preparing GHSL tile index...")
    tile_gdf = download_tile_shapefile()
    if tile_gdf is None:
        print("Error: Could not download tile shapefile")
        sys.exit(1)

    # Find tile ID column
    tile_id_col = None
    for col in tile_gdf.columns:
        if col.lower() in ("tile_id", "tileid", "tile"):
            tile_id_col = col
            break

    if tile_id_col is None:
        print("Error: Could not find tile ID column in shapefile")
        sys.exit(1)

    # Project AOI to Mollweide (native GHSL projection)
    mollweide_proj = "+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    aoi_mollweide = aoi.to_crs(mollweide_proj)

    # Find intersecting tiles
    print("Finding intersecting tiles...")
    aoi_union = aoi_mollweide.unary_union
    intersecting_tiles = tile_gdf[tile_gdf.intersects(aoi_union)]

    if intersecting_tiles.empty:
        print("Error: No intersecting tiles found")
        sys.exit(1)

    tile_ids = intersecting_tiles[tile_id_col].tolist()
    print(f"  Found {len(tile_ids)} tiles: {', '.join(tile_ids)}\n")

    # Process each year
    for year in years:
        print("="*60)
        print(f"Processing year: {year}")
        print("="*60)

        # Check if already exists
        output_file = os.path.join(temporal_dir, f'{city_name}_ghs_built_{year}.tif')
        if os.path.exists(output_file):
            print(f"  File already exists: {output_file}")
            print(f"  Skipping year {year}\n")
            continue

        # Download tiles
        print("\n  Downloading tiles...")
        datasets = []
        memfiles = []

        for tile_id in tile_ids:
            result = download_ghs_tile(tile_id, year)
            if result:
                ds, mem = result
                datasets.append(ds)
                memfiles.append(mem)

        if not datasets:
            print(f"\n  Warning: No tiles downloaded for year {year}, skipping")
            continue

        print(f"\n  Downloaded {len(datasets)} tiles")

        # Mosaic and clip
        print("\nMosaicking and clipping to AOI...")

        try:
            # Merge the in-memory datasets
            mosaic_arr, mosaic_transform = merge(datasets)

            # Get metadata from first dataset
            out_meta = datasets[0].meta.copy()

            # Update metadata for mosaic
            out_meta.update({
                "driver": "GTiff",
                "height": mosaic_arr.shape[1],
                "width": mosaic_arr.shape[2],
                "transform": mosaic_transform,
                "compress": "lzw"
            })

            # Save mosaic temporarily
            temp_mosaic = os.path.join(temp_dir, f"temp_mosaic_{year}.tif")
            with rasterio.open(temp_mosaic, "w", **out_meta) as dest:
                dest.write(mosaic_arr)

            # Close datasets and memfiles
            for ds in datasets:
                ds.close()
            for mem in memfiles:
                mem.close()

            # Reproject AOI to match raster CRS (Mollweide)
            with rasterio.open(temp_mosaic) as src:
                aoi_reproj = aoi.to_crs(src.crs)

                # Clip to AOI
                clipped, clip_transform = mask(src, aoi_reproj.geometry, crop=True)

                # Update metadata for clipped raster
                clip_meta = src.meta.copy()
                clip_meta.update({
                    "height": clipped.shape[1],
                    "width": clipped.shape[2],
                    "transform": clip_transform
                })

            # Save final output
            print(f"Saving to: {output_file}")
            with rasterio.open(output_file, "w", **clip_meta) as dest:
                dest.write(clipped)

            # Clean up
            os.remove(temp_mosaic)

            file_size = os.path.getsize(output_file) / (1024 * 1024)
            print(f"Success! File size: {file_size:.1f} MB\n")

        except Exception as e:
            print(f"Error processing year {year}: {e}\n")
            # Clean up on error
            for ds in datasets:
                try:
                    ds.close()
                except:
                    pass
            for mem in memfiles:
                try:
                    mem.close()
                except:
                    pass
            continue

    print("\n" + "="*60)
    print("All years completed!")
    print("="*60)

if __name__ == "__main__":
    main()
