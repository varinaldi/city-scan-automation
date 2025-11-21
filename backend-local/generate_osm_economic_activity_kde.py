#!/usr/bin/env python3
"""
Generate OSM-based economic activity rasters with KDE at 1km resolution
Generates both frequency counts and KDE-based probability surfaces

Usage: python generate_osm_economic_activity_kde.py <city-directory-name>
Example: python generate_osm_economic_activity_kde.py 2025-10-senegal-tambacounda
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import os
import sys
import re
from glob import glob
import rasterio
import rasterio.features
from rasterio.transform import from_bounds
from scipy.stats import gaussian_kde
from shapely.geometry import Point
from rasterio.warp import calculate_default_transform, reproject, Resampling
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
        print("Usage: python generate_osm_economic_activity_kde.py <city-directory-name>")
        print("Example: python generate_osm_economic_activity_kde.py 2025-10-senegal-tambacounda")
        sys.exit(1)

    city_dir_name = sys.argv[1]

    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    city_dir = os.path.join(project_root, "mnt", city_dir_name)
    data_dir = os.path.join(city_dir, "02-process-output", "spatial")
    user_dir = os.path.join(city_dir, "01-user-input")

    if not os.path.exists(city_dir):
        print(f"Error: City directory not found: {city_dir}")
        sys.exit(1)

    city_name = extract_city_info(city_dir_name)
    if not city_name:
        print(f"Error: Could not extract city name from: {city_dir_name}")
        sys.exit(1)

    print(f"Processing: {city_dir_name}")
    print(f"City: {city_name}\n")

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
    print(f"  AOI loaded\n")

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
        sys.exit(1)

    # Auto-detect UTM zone from AOI centroid
    print("\nDetecting UTM zone...")
    centroid = aoi.geometry.centroid.iloc[0]
    lon = centroid.x
    lat = centroid.y
    utm_zone = int((lon + 180) / 6) + 1
    hemisphere = 'north' if lat >= 0 else 'south'
    epsg_code = 32600 + utm_zone if hemisphere == 'north' else 32700 + utm_zone
    target_crs = f'EPSG:{epsg_code}'
    print(f"  UTM Zone: {utm_zone}{hemisphere[0].upper()} ({target_crs})")

    # Reproject to UTM
    aoi_utm = aoi.to_crs(target_crs)
    aoi_geom_utm = aoi_utm.geometry.iloc[0]

    for category in osm.keys():
        if osm[category] is not None:
            osm[category] = osm[category].to_crs(target_crs)

    # Create 1km resolution grid from AOI bounds
    print("\nCreating 1km grid...")
    bounds = aoi_utm.total_bounds
    pixel_size = 1000  # 1km

    width = int((bounds[2] - bounds[0]) / pixel_size)
    height = int((bounds[3] - bounds[1]) / pixel_size)

    print(f"  Grid: {width} x {height} pixels at {pixel_size}m resolution")

    # Create meshgrid
    x = np.linspace(bounds[0], bounds[2], width)
    y = np.linspace(bounds[1], bounds[3], height)
    xx, yy = np.meshgrid(x, y)
    grid_points = np.vstack([xx.ravel(), yy.ravel()])

    transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)

    # Calculate probabilities: frequency + KDE
    print("\nCalculating frequency and KDE probabilities...")
    probs = {}

    for land_use, gdf in osm.items():
        print(f"  Processing {land_use}...")

        # FREQUENCY
        if gdf is not None and len(gdf) > 0:
            probs[f'{land_use}_freq'] = count_features_per_cell(gdf, width, height, transform)
        else:
            probs[f'{land_use}_freq'] = np.zeros((height, width))

        # KDE
        if gdf is not None and len(gdf) > 0:
            coords = np.array([[p.x, p.y] for p in gdf.geometry])
            kde = gaussian_kde(coords.T, bw_method=100000/coords.std())

            # Evaluate KDE at ALL grid points
            kde_values = kde(grid_points)
            kde_grid = np.flipud(kde_values.reshape(height, width))

            # Apply AOI mask with 1km buffer
            aoi_mask = rasterio.features.geometry_mask(
                aoi_utm.buffer(1000).geometry,
                out_shape=(height, width),
                transform=transform,
                invert=True
            )

            probs[f'{land_use}_kde'] = np.where(aoi_mask, kde_grid, np.nan)
        else:
            probs[f'{land_use}_kde'] = np.full((height, width), np.nan)

    # NORMALIZE FREQUENCY
    print("\nNormalizing probabilities...")
    total_freq = probs['residential_freq'] + probs['commercial_freq'] + probs['industrial_freq']
    total_freq = np.where(total_freq > 0, total_freq, 1.0)

    probs['residential_freq'] = probs['residential_freq'] / total_freq
    probs['commercial_freq'] = probs['commercial_freq'] / total_freq
    probs['industrial_freq'] = probs['industrial_freq'] / total_freq

    # NORMALIZE KDE
    total_kde = probs['residential_kde'] + probs['commercial_kde'] + probs['industrial_kde']
    total_kde = np.where(total_kde > 0, total_kde, 1.0)

    probs['residential_kde'] = probs['residential_kde'] / total_kde
    probs['commercial_kde'] = probs['commercial_kde'] / total_kde
    probs['industrial_kde'] = probs['industrial_kde'] / total_kde

    # Save as GeoTIFFs in EPSG:4326
    print("\nSaving outputs...")
    os.makedirs(data_dir, exist_ok=True)

    crs_4326 = 'EPSG:4326'

    for land_use in ['residential', 'commercial', 'industrial']:
        for method in ['freq', 'kde']:
            data = probs[f'{land_use}_{method}']

            # Calculate transform for EPSG:4326
            transform_4326, width_4326, height_4326 = calculate_default_transform(
                target_crs, crs_4326, width, height, *bounds
            )

            # Save reprojected TIF
            tif_path = os.path.join(data_dir, f'{city_name}_{method}_{land_use}.tif')
            with rasterio.open(
                tif_path, 'w',
                driver='GTiff',
                height=height_4326,
                width=width_4326,
                count=1,
                dtype=data.dtype,
                crs=crs_4326,
                transform=transform_4326
            ) as dst:
                reproject(
                    source=data,
                    destination=rasterio.band(dst, 1),
                    src_transform=transform,
                    src_crs=target_crs,
                    dst_transform=transform_4326,
                    dst_crs=crs_4326,
                    resampling=Resampling.bilinear
                )

            print(f"  Saved: {city_name}_{method}_{land_use}.tif (EPSG:4326)")

    # Save OSM point data as GPKG in EPSG:4326
    print("\nSaving OSM point data...")
    for land_use, gdf in osm.items():
        if gdf is not None and len(gdf) > 0:
            gpkg_path = os.path.join(data_dir, f'{city_name}_osm_{land_use}.gpkg')
            gdf[['geometry']].to_crs('EPSG:4326').to_file(gpkg_path, driver='GPKG')
            print(f"  Saved: {city_name}_osm_{land_use}.gpkg (EPSG:4326)")

    print("\nDone!")

if __name__ == "__main__":
    main()
