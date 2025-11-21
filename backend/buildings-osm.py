#!/usr/bin/env python3
"""
Download building footprints from OpenStreetMap
Usage: python buildings-osm.py <city-directory-name>
Example: python buildings-osm.py 2025-10-senegal-tambacounda
"""

import geopandas as gpd
import os
import sys
import requests
import json
import re
from time import sleep

def extract_country_from_directory(city_dir_name):
    """Extract country from directory name"""
    match = re.search(r'\d{4}-\d{2}-([a-z]+)-', city_dir_name)
    if match:
        country = match.group(1)
        return country.capitalize()
    return None

def get_osm_buildings(bbox, max_retries=3):
    """
    Download buildings from OSM using Overpass API
    bbox: (min_lon, min_lat, max_lon, max_lat)
    """
    overpass_url = "https://overpass-api.de/api/interpreter"

    # Overpass query for buildings
    query = f"""
    [out:json][timeout:180];
    (
      way["building"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
      relation["building"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
    );
    out geom;
    """

    for attempt in range(max_retries):
        try:
            print(f"  Querying Overpass API (attempt {attempt + 1}/{max_retries})...")
            response = requests.post(overpass_url, data={'data': query}, timeout=300)
            response.raise_for_status()

            data = response.json()

            if 'elements' not in data:
                print("  Warning: No 'elements' in response")
                return None

            elements = data['elements']
            print(f"  Found {len(elements)} building features")

            if len(elements) == 0:
                return None

            # Convert to GeoDataFrame
            features = []
            for element in elements:
                if 'geometry' not in element:
                    continue

                # Convert OSM geometry to GeoJSON-like format
                if element['type'] == 'way':
                    coords = [(node['lon'], node['lat']) for node in element['geometry']]
                    if len(coords) > 2:
                        feature = {
                            'type': 'Feature',
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [coords]
                            },
                            'properties': {
                                'osm_id': element.get('id'),
                                'building': element.get('tags', {}).get('building', 'yes')
                            }
                        }
                        features.append(feature)

            if len(features) == 0:
                print("  No valid polygon features found")
                return None

            gdf = gpd.GeoDataFrame.from_features(features, crs=4326)
            return gdf

        except requests.exceptions.Timeout:
            print(f"  Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                sleep(5)
                continue
            return None
        except Exception as e:
            print(f"  Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                sleep(5)
                continue
            return None

    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python buildings-osm.py <city-directory-name>")
        print("Example: python buildings-osm.py 2025-10-senegal-tambacounda")
        sys.exit(1)

    city_dir_name = sys.argv[1]

    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    city_dir = os.path.join(project_root, "mnt", city_dir_name)
    aoi_path = os.path.join(city_dir, "01-user-input/AOI")
    output_dir = os.path.join(project_root, "data", "building-tiles")

    # Validate paths
    if not os.path.exists(city_dir):
        print(f"Error: City directory not found: {city_dir}")
        sys.exit(1)

    if not os.path.exists(aoi_path):
        print(f"Error: AOI not found: {aoi_path}")
        sys.exit(1)

    # Extract country and city
    country = extract_country_from_directory(city_dir_name)
    city_name_match = re.search(r'\d{4}-\d{2}-[a-z]+-(.+)$', city_dir_name)
    city_name = city_name_match.group(1) if city_name_match else "unknown"

    if not country:
        print(f"Error: Could not extract country from directory name: {city_dir_name}")
        print("Expected format: YYYY-MM-country-city (e.g., 2025-10-senegal-tambacounda)")
        sys.exit(1)

    print(f"Processing: {city_dir_name}")
    print(f"Country: {country}")
    print(f"City: {city_name}")
    print(f"AOI path: {aoi_path}\n")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Read AOI and get bounding box
    print("Reading AOI...")
    aoi = gpd.read_file(aoi_path)
    bbox = aoi.total_bounds  # (minx, miny, maxx, maxy)
    print(f"Bounding box: {bbox}\n")

    # Output file
    output_file = os.path.join(output_dir, f"{country}-{city_name}-osm.fgb")

    # Check if already exists
    if os.path.exists(output_file):
        print(f"File already exists: {output_file}")
        user_input = input("Overwrite? (y/n): ")
        if user_input.lower() != 'y':
            print("Cancelled")
            sys.exit(0)

    # Download buildings
    print("Downloading buildings from OpenStreetMap...")
    print("Note: This may take several minutes for large areas\n")

    buildings = get_osm_buildings(bbox)

    if buildings is None or len(buildings) == 0:
        print("\nNo building data found for this area")
        print("This could mean:")
        print("  - The area has not been mapped in OpenStreetMap")
        print("  - The Overpass API is temporarily unavailable")
        print("  - The query timed out (try a smaller area)")
        sys.exit(1)

    # Save to file
    print(f"\nSaving {len(buildings)} buildings...")
    buildings.to_file(output_file, driver="FlatGeobuf")
    file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB

    print("\n" + "="*70)
    print("Summary:")
    print(f"  Buildings downloaded: {len(buildings)}")
    print(f"  Output file: {output_file}")
    print(f"  File size: {file_size:.1f} MB")
    print("="*70)

if __name__ == "__main__":
    main()
