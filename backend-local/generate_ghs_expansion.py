#!/usr/bin/env python3
"""
Generate GHS Built-up expansion rasters (res and nres)
Tracks the first year each pixel exceeded area threshold (1000 m²)

Usage: python generate_ghs_expansion.py <city-directory-name>
Example: python generate_ghs_expansion.py 2025-10-senegal-diourbel
"""

import os
import sys
import re
import numpy as np
import xarray as xr
import rioxarray as rxr
import geopandas as gpd
from glob import glob

def extract_city_info(city_dir_name):
    """Extract city name from directory"""
    match = re.search(r'\d{4}-\d{2}-[a-z]+-(.+)$', city_dir_name)
    if match:
        return match.group(1)
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_ghs_expansion.py <city-directory-name>")
        print("Example: python generate_ghs_expansion.py 2025-10-senegal-diourbel")
        sys.exit(1)

    city_dir_name = sys.argv[1]

    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    city_dir = os.path.join(project_root, "mnt", city_dir_name)
    user_dir = os.path.join(city_dir, "01-user-input")
    temporal_dir = os.path.join(city_dir, "02-process-output", "temporal")
    spatial_dir = os.path.join(city_dir, "02-process-output", "spatial")

    if not os.path.exists(city_dir):
        print(f"Error: City directory not found: {city_dir}")
        sys.exit(1)

    city_name = extract_city_info(city_dir_name)
    if not city_name:
        print(f"Error: Could not extract city name from: {city_dir_name}")
        sys.exit(1)

    print(f"Processing: {city_dir_name}")
    print(f"City: {city_name}\n")

    # Load AOI
    print("Loading AOI...")
    aoi_files = glob(os.path.join(user_dir, 'AOI', '*.shp'))
    if not aoi_files:
        print(f"Error: No AOI shapefile found")
        sys.exit(1)

    aoi = gpd.read_file(aoi_files[0]).to_crs("EPSG:4326")
    print(f"  AOI loaded\n")

    # Find all GHS built-up files
    print("Finding GHS built-up files...")
    ghs_files = sorted(glob(os.path.join(temporal_dir, f'{city_name}_ghs_built_*.tif')))

    if not ghs_files:
        print(f"Error: No GHS built-up files found in {temporal_dir}")
        print(f"Expected pattern: {city_name}_ghs_built_*.tif")
        print("\nRun: python backend-local/download_ghs_buildup_direct.py", city_dir_name, "--all-years")
        sys.exit(1)

    # Extract years from filenames
    years = []
    for f in ghs_files:
        match = re.search(r'_ghs_built_(\d{4})\.tif$', f)
        if match:
            years.append(int(match.group(1)))

    years = sorted(years)
    print(f"  Found {len(years)} years: {years}\n")

    if len(years) < 2:
        print("Error: Need at least 2 years to calculate expansion")
        sys.exit(1)

    # Load and process each year
    print("Loading GHS built-up data...")
    ghs_builts = {}

    # Load first file to get reference for reprojection
    print("  Loading reference...")
    first_file = ghs_files[0]
    wsf_ref = rxr.open_rasterio(first_file, masked=True)

    for year, built_file in zip(years, ghs_files):
        print(f"  Loading {year}...")

        r = rxr.open_rasterio(built_file, masked=True)

        # Reproject to match first file if needed
        if r.rio.crs != wsf_ref.rio.crs or r.shape != wsf_ref.shape:
            r = r.rio.reproject_match(wsf_ref)

        # GHS Built-S has 2 bands: built (band 1) and non-residential (band 2)
        built = r.sel(band=1)
        nres = r.sel(band=2)

        # Residential = total built - non-residential
        res = built - nres

        # Clip to AOI
        res = res.rio.clip(aoi.geometry.values, aoi.crs)
        nres = nres.rio.clip(aoi.geometry.values, aoi.crs)

        ghs_builts[year] = {
            'res': res,
            'nres': nres
        }

    print("\nCalculating expansion...")

    # Area threshold (m²)
    area_threshold = 1000

    res_expansion = None
    nres_expansion = None

    for i, year in enumerate(years):
        print(f"  Processing {year}...")
        res = ghs_builts[year]['res']
        nres = ghs_builts[year]['nres']

        if res_expansion is None:
            # Initialize with NaN everywhere, then set built pixels to year
            res_expansion = xr.full_like(res, np.nan)
            res_expansion = xr.where(res > area_threshold, year, res_expansion)
        else:
            # Only update pixels that are built now but weren't marked before
            res_expansion = xr.where((res > area_threshold) & (np.isnan(res_expansion)), year, res_expansion)

        # Same for nres
        if nres_expansion is None:
            nres_expansion = xr.full_like(nres, np.nan)
            nres_expansion = xr.where(nres > area_threshold, year, nres_expansion)
        else:
            nres_expansion = xr.where((nres > area_threshold) & (np.isnan(nres_expansion)), year, nres_expansion)

    # Write CRS
    res_expansion = res_expansion.rio.write_crs(wsf_ref.rio.crs)
    nres_expansion = nres_expansion.rio.write_crs(wsf_ref.rio.crs)

    # Save outputs
    os.makedirs(spatial_dir, exist_ok=True)

    print("\nSaving outputs...")

    res_output = os.path.join(spatial_dir, 'ghs_res_expansion.tif')
    nres_output = os.path.join(spatial_dir, 'ghs_nres_expansion.tif')

    # Reproject to EPSG:4326 before saving
    res_expansion_4326 = res_expansion.rio.reproject('EPSG:4326')
    nres_expansion_4326 = nres_expansion.rio.reproject('EPSG:4326')

    res_expansion_4326.rio.to_raster(res_output, driver='GTiff')
    nres_expansion_4326.rio.to_raster(nres_output, driver='GTiff')

    print(f"  Saved: {res_output}")
    print(f"  Saved: {nres_output}")

    # Print statistics
    res_years = res_expansion.values[~np.isnan(res_expansion.values)]
    nres_years = nres_expansion.values[~np.isnan(nres_expansion.values)]

    print(f"\nStatistics:")
    print(f"  Residential expansion:")
    print(f"    Pixels tracked: {len(res_years)}")
    print(f"    Year range: {int(res_years.min())} - {int(res_years.max())}")

    print(f"  Non-residential expansion:")
    print(f"    Pixels tracked: {len(nres_years)}")
    print(f"    Year range: {int(nres_years.min())} - {int(nres_years.max())}")

    print("\nDone!")

if __name__ == "__main__":
    main()
