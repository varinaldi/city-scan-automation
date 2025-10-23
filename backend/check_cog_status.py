#!/usr/bin/env python3
"""
Check if GCS TIF files are Cloud-Optimized GeoTIFFs (COGs)
and if other files can be streamed without full download.
"""

import rasterio
from rasterio.env import GDALEnv
from google.cloud import storage
import geopandas as gpd
import pandas as pd
from io import BytesIO
import yaml

def check_if_cog(gcs_path):
    """
    Check if a GCS-hosted TIF is a Cloud-Optimized GeoTIFF

    Args:
        gcs_path: gs://bucket-name/path/to/file.tif

    Returns:
        dict with COG status and details
    """
    try:
        # Open with vsigs (GDAL's GCS virtual file system)
        vsi_path = gcs_path.replace('gs://', '/vsigs/')

        with rasterio.open(vsi_path) as src:
            # Check for COG indicators
            is_tiled = src.profile.get('tiled', False)
            has_overviews = src.overviews(1) if src.count > 0 else []
            blockxsize = src.profile.get('blockxsize', 0)
            blockysize = src.profile.get('blockysize', 0)

            # COG requirements:
            # 1. Must be tiled (not striped)
            # 2. Should have overviews (pyramids)
            # 3. Tiles should be reasonable size (typically 512x512)
            is_cog = (
                is_tiled and
                len(has_overviews) > 0 and
                blockxsize >= 256 and blockysize >= 256
            )

            return {
                'path': gcs_path,
                'is_cog': is_cog,
                'is_tiled': is_tiled,
                'tile_size': f'{blockxsize}x{blockysize}',
                'num_overviews': len(has_overviews),
                'compression': src.profile.get('compress', 'none'),
                'can_stream': is_cog
            }
    except Exception as e:
        return {
            'path': gcs_path,
            'is_cog': False,
            'error': str(e),
            'can_stream': False
        }

def test_streaming_read(gcs_path, bbox):
    """
    Test if a file can be read with window/bbox without full download

    Args:
        gcs_path: gs://bucket-name/path/to/file.tif
        bbox: (minx, miny, maxx, maxy) in file's CRS

    Returns:
        Success status and data size
    """
    try:
        vsi_path = gcs_path.replace('gs://', '/vsigs/')

        with rasterio.open(vsi_path) as src:
            # Get window from bbox
            window = src.window(*bbox)

            # This should only download the needed tiles if COG
            data = src.read(1, window=window)

            return {
                'success': True,
                'data_shape': data.shape,
                'data_size_mb': data.nbytes / (1024**2)
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def check_vector_streaming(gcs_path):
    """
    Check if vector files (shp, gpkg, geojson) can be read directly from GCS

    Args:
        gcs_path: gs://bucket-name/path/to/file.{shp,gpkg,geojson}

    Returns:
        Streaming capability info
    """
    vsi_path = gcs_path.replace('gs://', '/vsigs/')

    try:
        # Try to read with geopandas
        gdf = gpd.read_file(vsi_path)

        return {
            'path': gcs_path,
            'can_stream': True,
            'rows': len(gdf),
            'format': gcs_path.split('.')[-1],
            'note': 'Can read directly via GDAL VSI'
        }
    except Exception as e:
        return {
            'path': gcs_path,
            'can_stream': False,
            'error': str(e),
            'note': 'Must download fully first'
        }

def check_csv_streaming(bucket_name, blob_path):
    """
    Check if CSV can be streamed from GCS

    Args:
        bucket_name: GCS bucket name
        blob_path: Path to CSV in bucket

    Returns:
        Streaming capability info
    """
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        # Download as bytes and read with pandas
        csv_bytes = blob.download_as_bytes()
        df = pd.read_csv(BytesIO(csv_bytes))

        return {
            'path': f'gs://{bucket_name}/{blob_path}',
            'can_stream': True,
            'rows': len(df),
            'size_mb': len(csv_bytes) / (1024**2),
            'note': 'Can stream via google-cloud-storage client'
        }
    except Exception as e:
        return {
            'path': f'gs://{bucket_name}/{blob_path}',
            'can_stream': False,
            'error': str(e)
        }

def main():
    """Run checks on common datasets"""

    print("=" * 80)
    print("CHECKING COG STATUS OF GCS TIF FILES")
    print("=" * 80)

    # Example datasets to check (update with actual paths from global_inputs.yml)
    test_datasets = {
        'elevation': 'gs://city-scan-global-data/DEM/fabdem.tif',
        'landcover': 'gs://city-scan-global-data/landcover/esa_cci_landcover.tif',
        # Add more from global_inputs.yml
    }

    print("\n1. Checking TIF files for COG compatibility:\n")
    for name, path in test_datasets.items():
        print(f"Checking {name}...")
        result = check_if_cog(path)

        if 'error' in result:
            print(f"  ❌ Error: {result['error']}")
        else:
            status = "✅ IS COG" if result['is_cog'] else "❌ NOT COG"
            print(f"  {status}")
            print(f"     - Tiled: {result['is_tiled']}")
            print(f"     - Tile size: {result['tile_size']}")
            print(f"     - Overviews: {result['num_overviews']}")
            print(f"     - Compression: {result['compression']}")
            print(f"     - Can stream chunks: {result['can_stream']}")
        print()

    print("\n2. Testing vector file streaming:\n")
    # Example: Check if shapefiles can be read directly
    vector_test = 'gs://city-scan-global-data/boundaries/admin_boundaries.gpkg'
    result = check_vector_streaming(vector_test)
    print(f"Vector streaming test: {result}")

    print("\n3. Testing CSV streaming:\n")
    csv_result = check_csv_streaming('city-scan-global-data', 'some_data.csv')
    print(f"CSV streaming test: {csv_result}")

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print("""
    If TIFs are COG:
      ✅ You can stream chunks without full download using rasterio windows
      ✅ Use vsigs:// protocol: rasterio.open('/vsigs/bucket/file.tif')
      ✅ Read only needed windows/bboxes

    If TIFs are NOT COG:
      ❌ Must download fully before processing
      💡 Consider converting to COG: gdal_translate -of COG input.tif output_cog.tif

    Vector files (shp/gpkg):
      ✅ Can usually stream via GDAL VSI (/vsigs/)
      ✅ GeoPandas: gpd.read_file('/vsigs/bucket/file.gpkg', bbox=(...))

    CSV files:
      ✅ Can stream via google-cloud-storage Python client
      ✅ Use blob.download_as_bytes() + BytesIO + pandas
    """)

if __name__ == '__main__':
    main()
