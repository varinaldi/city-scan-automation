"""
Demographics Processing for Local Use (Task 6)
Saves directly to mnt/ city folder
"""

import os
import requests
import sys
sys.path.insert(0, 'backend')
import raster_pro

def run_demographics(city_name_l, country_iso3, aoi_file, output_tabular):
    """
    Download WorldPop demographics data and save CSV

    Args:
        city_name_l: lowercase city name
        country_iso3: ISO3 country code (e.g., 'SEN')
        aoi_file: GeoDataFrame with AOI
        output_tabular: path to output tabular folder (e.g., 'mnt/city/02-process-output/tabular')
    """
    print(f"Running demographics for {city_name_l}...")

    # Setup temp folder
    local_demo_folder = 'data/demographics'
    os.makedirs(local_demo_folder, exist_ok=True)
    os.makedirs(output_tabular, exist_ok=True)

    # Fetch WorldPop age/sex data
    print(f"Fetching WorldPop age structures for {country_iso3}...")
    wp_file_json = requests.get(f"https://www.worldpop.org/rest/data/age_structures/ascic_2020?iso3={country_iso3}").json()
    wp_file_list = wp_file_json['data'][0]['files']
    print(f"Found {len(wp_file_list)} age/sex raster files")

    # Download rasters directly from URLs
    print("Downloading rasters...")
    for url in wp_file_list:
        filename = url.split('/')[-1]
        filepath = f'{local_demo_folder}/{filename}'
        if not os.path.exists(filepath):
            print(f"  Downloading {filename}...")
            response = requests.get(url)
            with open(filepath, 'wb') as f:
                f.write(response.content)
        else:
            print(f"  {filename} already exists, skipping")

    # Process demographics by age and sex
    print("Processing demographics by age and sex...")
    features = aoi_file.geometry
    sexes = ['f', 'm']

    output_file = f'{output_tabular}/{city_name_l}_demographics.csv'
    with open(output_file, 'w') as f:
        f.write('age_group,sex,population\n')

        for i in [1] + list(range(0, 85, 5)):
            for s in sexes:
                raster_file = f'{local_demo_folder}/{country_iso3.lower()}_{s}_{i}_2020_constrained.tif'
                out_image, out_meta = raster_pro.raster_mask_file(raster_file, features)
                out_image[out_image == out_meta['nodata']] = 0

                if i == 0:
                    age_group_label = '0-1'
                elif i == 1:
                    age_group_label = '1-4'
                elif i == 80:
                    age_group_label = '80+'
                else:
                    age_group_label = f'{i}-{i+4}'

                population = sum(sum(sum(out_image)))
                f.write(f'{age_group_label},{s},{population}\n')
                print(f"  {age_group_label} {s}: {population:,.0f}")

    print(f"✓ Demographics CSV saved to: {output_file}")
    return output_file
