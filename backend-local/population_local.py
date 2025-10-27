"""
WorldPop Population Processing for Local Use (Task 7)
Saves directly to mnt/ city folder
"""

import os
import requests
import rasterio
import sys
sys.path.insert(0, 'backend')
import raster_pro

def run_population(city_name_l, country_iso3, aoi_file, output_spatial):
    """
    Download WorldPop data and save to local folder

    Args:
        city_name_l: lowercase city name
        country_iso3: ISO3 country code (e.g., 'SEN')
        aoi_file: GeoDataFrame with AOI
        output_spatial: path to output spatial folder (e.g., 'mnt/city/02-process-output/spatial')
    """
    print(f"Running WorldPop population for {city_name_l}...")

    # Setup temp folder
    local_pop_folder = 'data/pop'
    os.makedirs(local_pop_folder, exist_ok=True)
    os.makedirs(output_spatial, exist_ok=True)

    # Fetch WorldPop file list
    print(f"Fetching WorldPop data for {country_iso3}...")
    wp_file_json = requests.get(f"https://hub.worldpop.org/rest/data/pop/cic2020_100m?iso3={country_iso3}").json()
    wp_file_list = wp_file_json['data'][0]['files']
    print(f"Found {len(wp_file_list)} raster files")

    # Download rasters directly from URLs
    print("Downloading rasters...")
    downloaded_list = []
    for url in wp_file_list:
        filename = url.split('/')[-1]
        filepath = f'{local_pop_folder}/{filename}'
        if not os.path.exists(filepath):
            print(f"  Downloading {filename}...")
            response = requests.get(url)
            with open(filepath, 'wb') as f:
                f.write(response.content)
        else:
            print(f"  {filename} already exists, skipping")
        downloaded_list.append(filepath)

    # Mosaic rasters
    print("Mosaicking rasters...")
    raster_pro.mosaic_raster(downloaded_list, local_pop_folder, f'{city_name_l}_population.tif')

    # Mask to AOI
    print("Clipping to AOI...")
    features = aoi_file.geometry
    out_image, out_meta = raster_pro.raster_mask_file(f'{local_pop_folder}/{city_name_l}_population.tif', features)

    # Save directly to mnt/ folder
    output_file = f'{output_spatial}/{city_name_l}_population.tif'
    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(out_image)

    print(f"✓ Population raster saved to: {output_file}")
    return output_file
