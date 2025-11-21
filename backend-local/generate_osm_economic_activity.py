#!/usr/bin/env python3
"""
Generate OSM-based economic activity rasters at 1km resolution
Usage: python generate_osm_economic_activity.py <city-directory-name>
Example: python generate_osm_economic_activity.py 2025-10-senegal-tambacounda
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import os
import sys
import re
from glob import glob
import xarray as xr
import rioxarray as rxr
import rasterio
import rasterio.features
from rasterio.transform import from_bounds
import osmnx as ox
import warnings
warnings.filterwarnings('ignore')

def extract_city_info(city_dir_name):
    """Extract city name from directory"""
    match = re.search(r'\d{4}-\d{2}-[a-z]+-(.+)$', city_dir_name)
    if match:
        return match.group(1)
    return None

def get_osm_features(aoi_geom, osm_keys):
    """Download OSM features for each category"""
    osm = {}

    for category, tags in osm_keys.items():
        all_features = []

        for key, value in tags.items():
            try:
                gdf = ox.features_from_polygon(aoi_geom, tags={key: value})
                gdf['osm_type'] = f"{key}_{value}"
                all_features.append(gdf)
                print(f"  Found {len(gdf)} features for {category}: {key}={value}")
            except Exception as e:
                print(f"  No data for {category}: {key}={value}")

        if all_features:
            combined = pd.concat(all_features, ignore_index=True)
            combined = combined.to_crs('EPSG:3857')
            combined['geometry'] = combined.geometry.centroid
            combined = combined.to_crs('EPSG:4326')
            combined = combined.drop_duplicates(subset=['geometry'], keep='first')
            osm[category] = combined
        else:
            osm[category] = None

    return osm

def count_features_per_cell(gdf, width, height, transform):
    """Count features per raster cell"""
    if len(gdf) == 0:
        return np.zeros((height, width))

    if len(gdf) > 0 and gdf.geometry.iloc[0].geom_type in ['Polygon', 'MultiPolygon']:
        gdf = gdf.copy()
        gdf['geometry'] = gdf.geometry.centroid

    shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]

    counts = rasterio.features.rasterize(
        shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0,
        merge_alg=rasterio.enums.MergeAlg.add,
        dtype=np.float32
    )

    return counts

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_osm_economic_activity.py <city-directory-name>")
        print("Example: python generate_osm_economic_activity.py 2025-10-senegal-tambacounda")
        sys.exit(1)

    city_dir_name = sys.argv[1]

    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    city_dir = os.path.join(project_root, "mnt", city_dir_name)
    data_dir = os.path.join(city_dir, "02-process-output", "spatial")
    temporal_dir = os.path.join(city_dir, "02-process-output", "temporal")
    user_dir = os.path.join(city_dir, "01-user-input")

    # Validate paths
    if not os.path.exists(city_dir):
        print(f"Error: City directory not found: {city_dir}")
        sys.exit(1)

    city_name = extract_city_info(city_dir_name)
    if not city_name:
        print(f"Error: Could not extract city name from: {city_dir_name}")
        sys.exit(1)

    print(f"Processing: {city_dir_name}")
    print(f"City: {city_name}")
    print(f"Data dir: {data_dir}\n")

    # Define OSM categories
    osm_keys = {
        'residential': {
            'building': ['residential', 'apartments', 'house', 'detached', 'terrace', 'dormitory'],
            'landuse': ['residential']
        },
        'commercial': {
            'shop': True,
            'amenity': ['restaurant', 'cafe', 'bar', 'bank', 'marketplace', 'fast_food'],
            'office': True,
            'building': ['commercial', 'retail'],
            'landuse': ['commercial', 'retail'],
            'tourism': ['hotel']
        },
        'industrial': {
            'landuse': ['industrial', 'brownfield', 'quarry'],
            'building': ['industrial', 'warehouse', 'manufacture'],
            'man_made': ['works', 'storage_tank'],
            'craft': True
        }
    }

    # Load AOI
    print("Loading AOI...")
    aoi_files = glob(os.path.join(user_dir, 'AOI', '*.shp'))
    if not aoi_files:
        print(f"Error: No AOI shapefile found in {user_dir}/AOI")
        sys.exit(1)

    aoi = gpd.read_file(aoi_files[0]).to_crs("EPSG:4326")
    aoi_geom = aoi.geometry.unary_union
    print(f"  AOI loaded: {aoi_files[0]}\n")

    # Load reference grid (try population first, then built-up)
    print("Loading reference grid...")

    # Try population data first (more commonly available)
    pop_tif = glob(os.path.join(data_dir, f'{city_name}_population.tif'))
    ghs_tifs = glob(os.path.join(temporal_dir, f'{city_name}_ghs_built_2020.tif'))

    if pop_tif:
        print("  Using population data as reference grid")
        reference_grid = rxr.open_rasterio(pop_tif[0], masked=True).rio.clip(aoi.geometry.values, aoi.crs)
        if reference_grid.ndim == 3:
            reference_grid = reference_grid.sel(band=1)
    elif ghs_tifs:
        print("  Using GHS built-up data as reference grid")
        ghs = rxr.open_rasterio(ghs_tifs[0], masked=True).rio.clip(aoi.geometry.values, aoi.crs)
        if ghs.shape[0] >= 2:
            reference_grid = ghs.sel(band=1) + ghs.sel(band=2)
        else:
            reference_grid = ghs.sel(band=1)
    else:
        print(f"Error: No reference grid data found")
        print(f"  Looked for: {city_name}_population.tif in {data_dir}")
        print(f"  Looked for: {city_name}_ghs_built_2020.tif in {temporal_dir}")
        sys.exit(1)

    print(f"  Reference grid loaded: {reference_grid.shape}\n")

    # Download OSM features
    print("Downloading OSM features...")
    osm = get_osm_features(aoi_geom, osm_keys)

    print("\nOSM feature counts:")
    for category in osm.keys():
        if osm[category] is not None:
            print(f"  {category}: {len(osm[category])} features")
        else:
            print(f"  {category}: 0 features")

    if all(osm[cat] is None or len(osm[cat]) == 0 for cat in osm.keys()):
        print("\nWarning: No OSM features found for this city!")
        print("Cannot generate economic activity rasters.")
        sys.exit(1)

    # Reproject to UTM for metric calculations
    print("\nReprojecting to UTM...")
    # Auto-detect UTM zone from AOI centroid
    centroid = aoi.geometry.centroid.iloc[0]
    lon = centroid.x
    lat = centroid.y
    utm_zone = int((lon + 180) / 6) + 1
    hemisphere = 'north' if lat >= 0 else 'south'
    epsg_code = 32600 + utm_zone if hemisphere == 'north' else 32700 + utm_zone
    target_crs = f'EPSG:{epsg_code}'
    print(f"  Auto-detected UTM Zone: {utm_zone}{hemisphere[0].upper()} ({target_crs})")
    reference_grid = reference_grid.rio.reproject(target_crs)

    for category in osm.keys():
        if osm[category] is not None:
            osm[category] = osm[category].to_crs(target_crs)

    # Create 1km resolution grid
    print("\nCreating 1km resolution grid...")
    bounds = reference_grid.rio.bounds()
    pixel_size = 1000  # 1km

    width_1km = int((bounds[2] - bounds[0]) / pixel_size)
    height_1km = int((bounds[3] - bounds[1]) / pixel_size)

    print(f"  Grid size: {width_1km} x {height_1km} pixels at 1km resolution")

    transform_1km = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3],
                                width_1km, height_1km)

    # Count features per cell
    print("\nCounting OSM features per 1km cell...")
    counts_1km = {}
    for land_use, gdf in osm.items():
        if gdf is not None and len(gdf) > 0:
            counts_1km[land_use] = count_features_per_cell(gdf, width_1km, height_1km, transform_1km)
            print(f"  {land_use}: max {counts_1km[land_use].max():.0f} features per cell")
        else:
            counts_1km[land_use] = np.zeros((height_1km, width_1km))
            print(f"  {land_use}: 0 features")

    # Normalize to probabilities
    print("\nNormalizing to probabilities...")
    total = counts_1km['residential'] + counts_1km['commercial'] + counts_1km['industrial']
    total = np.where(total > 0, total, 1.0)

    probs_1km = {
        'residential': np.where(total > 0, counts_1km['residential'] / total, 1.0),
        'commercial': np.where(total > 0, counts_1km['commercial'] / total, 0.0),
        'industrial': np.where(total > 0, counts_1km['industrial'] / total, 0.0)
    }

    # Save as GeoTIFFs
    print("\nSaving 1km probability rasters...")
    original_crs = reference_grid.rio.crs

    for land_use in ['residential', 'commercial', 'industrial']:
        output_path = os.path.join(data_dir, f'{city_name}_prob_1km_{land_use}.tif')

        da = xr.DataArray(probs_1km[land_use], dims=['y', 'x'])
        da.rio.write_crs(original_crs, inplace=True)
        da.rio.write_transform(transform_1km, inplace=True)

        da_4326 = da.rio.reproject('EPSG:4326')
        da_4326.rio.to_raster(output_path, driver='GTiff')
        print(f"  Saved: {output_path}")

    print("\nDone!")
    print("\nSummary:")
    print(f"  Output directory: {data_dir}")
    print(f"  Files generated:")
    print(f"    - {city_name}_prob_1km_residential.tif")
    print(f"    - {city_name}_prob_1km_commercial.tif")
    print(f"    - {city_name}_prob_1km_industrial.tif")

if __name__ == "__main__":
    main()
