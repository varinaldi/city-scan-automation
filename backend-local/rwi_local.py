"""
Relative Wealth Index (RWI) Processing for Local Use (Task 14)
Downloads Meta/Facebook RWI data from GCS and saves directly to mnt/ city folder
"""

import os
import subprocess
import pandas as pd
import geopandas as gpd
from pyquadkey2.quadkey import QuadKey, TileAnchor
from shapely.geometry import Polygon


def run_rwi(city_name_l, country_iso3, aoi_file, output_spatial):
    """
    Process RWI data and save to local folder

    Args:
        city_name_l: lowercase city name
        country_iso3: ISO3 country code (e.g., 'SEN')
        aoi_file: GeoDataFrame with AOI
        output_spatial: path to output spatial folder (e.g., 'mnt/city/02-process-output/spatial')
    """
    print(f"Running RWI for {city_name_l}...")

    # Setup data folder
    local_rwi_folder = 'data/rwi'
    os.makedirs(local_rwi_folder, exist_ok=True)
    os.makedirs(output_spatial, exist_ok=True)

    # RWI data file path
    rwi_file = f'{local_rwi_folder}/{country_iso3}_relative_wealth_index.csv'
    gcs_path = f'gs://city-scan-global-data/Relative Wealth Index/{country_iso3}_relative_wealth_index.csv'

    # Download from GCS if not already present
    if not os.path.exists(rwi_file):
        print(f"Downloading RWI data from GCS...")
        try:
            result = subprocess.run(
                ['gsutil', 'cp', gcs_path, rwi_file],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ Downloaded from {gcs_path}")
        except subprocess.CalledProcessError as e:
            print(f'❌ Failed to download RWI data from GCS')
            print(f'Error: {e.stderr}')
            print(f'\nAttempted to download from: {gcs_path}')
            print(f'This may mean:')
            print(f'1. No RWI data available for {country_iso3}')
            print(f'2. GCS authentication issue (try: gcloud auth login)')
            return None
    else:
        print(f"Using cached RWI data from {rwi_file}")

    print(f"Loading RWI data...")

    # Load RWI data
    FB_QKdata = pd.read_csv(rwi_file)

    # Check if data has expected columns
    if 'quadkey' not in FB_QKdata.columns:
        print(f'❌ RWI file does not contain "quadkey" column')
        print(f'Available columns: {list(FB_QKdata.columns)}')
        return None

    # Change quadkey format to str
    FB_QKdata["quadkey1"] = FB_QKdata["quadkey"].astype('str')

    # Fill 13 digit quadkeys with 0 before the QK (standardize to 14 digits)
    FB_QKdata['quadkey1'] = FB_QKdata['quadkey1'].apply(lambda x: x.zfill(14))

    # Take column with quadkeys and transform it to list and then to QuadKey object
    fb_qk = FB_QKdata["quadkey1"].tolist()
    FB_QK = [QuadKey(i) for i in fb_qk]

    print(f"Converting {len(FB_QK)} quadkeys to polygons...")

    # Locate the four corners of QuadKey tiles
    SW = []
    NE = []
    SE = []
    NW = []

    for i in FB_QK:
        # South west point
        sw = i.to_geo(anchor=TileAnchor.ANCHOR_SW)
        SW.append(sw)
        # North east point
        ne = i.to_geo(anchor=TileAnchor.ANCHOR_NE)
        NE.append(ne)
        # South east point
        se = i.to_geo(anchor=TileAnchor.ANCHOR_SE)
        SE.append(se)
        # North west point
        nw = i.to_geo(anchor=TileAnchor.ANCHOR_NW)
        NW.append(nw)

    # Flip lat and lon for tile corner coordinates
    swFinal = [(i[1], i[0]) for i in SW]
    neFinal = [(i[1], i[0]) for i in NE]
    seFinal = [(i[1], i[0]) for i in SE]
    nwFinal = [(i[1], i[0]) for i in NW]

    # Generate Polygon object based on four corner coordinates
    tiledata = [Polygon([nw, sw, se, ne]) for sw, ne, se, nw in zip(swFinal, neFinal, seFinal, nwFinal)]

    # Create GeoDataFrame with Polygons
    gdf = gpd.GeoDataFrame(geometry=tiledata, crs="epsg:4326")

    # Add QuadKeys to gdf
    gdf['quadkey'] = FB_QK

    # Change type of quadkey column to str
    gdf["quadkey"] = gdf["quadkey"].astype('str')

    # Merge gdf and fb data
    gdf = gdf.merge(FB_QKdata, left_on='quadkey', right_on='quadkey1', how='inner')

    print("Clipping to AOI...")
    # Clip to AOI
    gdf_aoi = gpd.clip(gdf, aoi_file)

    if len(gdf_aoi) == 0:
        print(f'⚠️  Warning: No RWI data found within AOI bounds')
        return None

    # Save directly to mnt/ folder
    output_file = f'{output_spatial}/{city_name_l}_rwi.gpkg'
    gdf_aoi.to_file(output_file, driver='GPKG', layer='rwi')

    print(f"✓ RWI data saved to: {output_file}")
    print(f"  {len(gdf_aoi)} tiles within AOI")

    if 'rwi' in gdf_aoi.columns:
        print(f"  RWI range: {gdf_aoi['rwi'].min():.3f} to {gdf_aoi['rwi'].max():.3f}")

    return output_file
