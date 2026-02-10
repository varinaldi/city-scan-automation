#!/usr/bin/env python3
"""
Download building footprints for any city from Microsoft Bing dataset
Usage: python download-buildings.py <city-directory-name>
Example: python download-buildings.py 2025-10-senegal-matam
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import os
import sys
import math
import re
import yaml

def get_quadkey(lat, lng, zoom):
    """Convert lat/lng to quadkey at specified zoom level"""
    x = int((lng + 180) / 360 * (1 << zoom))
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * (1 << zoom))
    quadkey = ''
    for i in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if (x & mask) != 0:
            digit += 1
        if (y & mask) != 0:
            digit += 2
        quadkey += str(digit)
    return int(quadkey)

def get_quadkeys(aoi_path, zoom):
    """Extract all unique quadkeys from AOI geometry"""
    aoi = gpd.read_file(aoi_path)
    quadkeys = []

    for geom in aoi.geometry:
        if geom is None:
            continue

        coords = []

        # Extract coordinates based on geometry type
        if geom.geom_type == 'Point':
            coords = [(geom.y, geom.x)]
        elif geom.geom_type == 'LineString':
            coords = [(y, x) for x, y in geom.coords]
        elif geom.geom_type == 'Polygon':
            for ring in [geom.exterior] + list(geom.interiors):
                coords.extend([(y, x) for x, y in ring.coords])
        elif geom.geom_type in ['MultiPoint', 'MultiLineString', 'MultiPolygon']:
            for part in geom.geoms:
                if part.geom_type == 'Point':
                    coords.append((part.y, part.x))
                elif part.geom_type == 'LineString':
                    coords.extend([(y, x) for x, y in part.coords])
                elif part.geom_type == 'Polygon':
                    for ring in [part.exterior] + list(part.interiors):
                        coords.extend([(y, x) for x, y, *_ in ring.coords])

        # Get quadkey for each coordinate
        for lat, lng in coords:
            quadkey = get_quadkey(lat, lng, zoom)
            if quadkey not in quadkeys:
                quadkeys.append(quadkey)

    return quadkeys

def extract_country_from_directory(city_dir):
    """Extract country name from directory pattern like '2025-10-senegal-dakar'"""
    match = re.search(r'\d{4}-\d{2}-([a-z]+)-', city_dir)
    if match:
        country = match.group(1)
        return country.capitalize()
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python download-buildings.py <city-directory-name>")
        print("Example: python download-buildings.py 2025-10-senegal-matam")
        sys.exit(1)

    city_dir_name = sys.argv[1]

    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    city_dir = os.path.join(script_dir, "mnt", city_dir_name)
    aoi_dir = os.path.join(city_dir, "01-user-input/AOI")
    output_dir = os.path.join(script_dir, "building-tiles")

    if not os.path.exists(city_dir):
        print(f"Error: City directory not found: {city_dir}")
        sys.exit(1)

    if not os.path.exists(aoi_dir):
        print(f"Error: AOI not found: {aoi_dir}")
        sys.exit(1)

    # Read AOI_shp_name from city_inputs.yml
    city_inputs_path = os.path.join(city_dir, "01-user-input/city_inputs.yml")
    aoi_shp_name = None
    if os.path.exists(city_inputs_path):
        with open(city_inputs_path) as f:
            city_inputs = yaml.safe_load(f)
        aoi_shp_name = city_inputs.get("AOI_shp_name")

    # Build AOI path: use the specific shapefile if AOI_shp_name is set
    if aoi_shp_name:
        aoi_path = os.path.join(aoi_dir, f"{aoi_shp_name}.shp")
        if not os.path.exists(aoi_path):
            print(f"Warning: {aoi_shp_name}.shp not found, falling back to directory")
            aoi_path = aoi_dir
    else:
        aoi_path = aoi_dir

    # Extract country from directory name
    country = extract_country_from_directory(city_dir_name)
    if not country:
        print(f"Error: Could not extract country from directory name: {city_dir_name}")
        print("Expected format: YYYY-MM-country-city (e.g., 2025-10-senegal-matam)")
        sys.exit(1)

    print(f"Processing: {city_dir_name}")
    print(f"Country: {country}")
    print(f"AOI path: {aoi_path}")

    os.makedirs(output_dir, exist_ok=True)

    # Get quadkeys for AOI
    print("Calculating quadkeys from AOI...")
    quadkeys = get_quadkeys(aoi_path, zoom=9)
    print(f"Found {len(quadkeys)} unique quadkeys: {quadkeys}")

    # Download dataset links
    print("\nDownloading dataset links...")
    dataset_links = pd.read_csv("https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv")

    # Process each quadkey
    downloaded = 0
    skipped = 0
    not_found = 0

    for quadkey in quadkeys:
        output_file = os.path.join(output_dir, f"{country}-{quadkey}.fgb")

        if os.path.exists(output_file):
            print(f"Quadkey {quadkey}: Already exists, skipping...")
            skipped += 1
            continue

        country_links = dataset_links[
            (dataset_links.Location == country) &
            (dataset_links.QuadKey == quadkey)
        ]

        if len(country_links) == 0:
            print(f"Quadkey {quadkey}: No data found for {country}")
            not_found += 1
            continue

        for _, row in country_links.iterrows():
            print(f"Quadkey {quadkey}: Downloading from {row.Url[:80]}...")
            try:
                df = pd.read_json(row.Url, lines=True)
                df['geometry'] = df['geometry'].apply(shape)
                gdf = gpd.GeoDataFrame(df, crs=4326)
                gdf.to_file(output_file, driver="FlatGeobuf")
                file_size = os.path.getsize(output_file) / (1024 * 1024)
                print(f"Saved: {output_file} ({file_size:.1f} MB)")
                downloaded += 1
            except Exception as e:
                print(f"Error downloading quadkey {quadkey}: {e}")

    # Clip to AOI and save to city's spatial folder
    aoi = gpd.read_file(aoi_path)
    all_tiles = []
    for quadkey in quadkeys:
        tile_file = os.path.join(output_dir, f"{country}-{quadkey}.fgb")
        if os.path.exists(tile_file):
            all_tiles.append(gpd.read_file(tile_file))

    if all_tiles:
        buildings = pd.concat(all_tiles, ignore_index=True)
        buildings = gpd.clip(buildings, aoi)
        spatial_dir = os.path.join(city_dir, "02-process-output", "spatial")
        os.makedirs(spatial_dir, exist_ok=True)
        city_string = re.search(r'\d{4}-\d{2}-[a-z]+-(.+)$', city_dir_name).group(1)
        out_path = os.path.join(spatial_dir, f"{city_string}_building_footprints.fgb")
        buildings.to_file(out_path, driver="FlatGeobuf")
        print(f"Saved clipped buildings: {out_path} ({len(buildings)} features)")
    else:
        print("No building tiles to clip")

    print("\n" + "="*60)
    print("Summary:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Not found: {not_found}")
    print("="*60)

if __name__ == "__main__":
    main()
