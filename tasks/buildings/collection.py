# Download building footprints from OpenStreetMap via Overpass API
import os
import geopandas as gpd
import requests
from time import sleep
from core.py.log_module import setup_logger

logger = setup_logger(__name__)


def get_osm_buildings(bbox, max_retries=3):
    """
    Download buildings from OSM using Overpass API.
    bbox: (min_lon, min_lat, max_lon, max_lat)
    """
    overpass_url = "https://overpass-api.de/api/interpreter"

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
            logger.info(f"Querying Overpass API (attempt {attempt + 1}/{max_retries})...")
            response = requests.post(overpass_url, data={'data': query}, timeout=300)
            response.raise_for_status()

            data = response.json()

            if 'elements' not in data:
                logger.warning("No 'elements' in response")
                return None

            elements = data['elements']
            logger.info(f"Found {len(elements)} building features")

            if len(elements) == 0:
                return None

            features = []
            for element in elements:
                if 'geometry' not in element:
                    continue

                if element['type'] == 'way':
                    coords = [(node['lon'], node['lat']) for node in element['geometry']]
                    if len(coords) > 2:
                        features.append({
                            'type': 'Feature',
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [coords]
                            },
                            'properties': {
                                'osm_id': element.get('id'),
                                'building': element.get('tags', {}).get('building', 'yes')
                            }
                        })

            if len(features) == 0:
                logger.warning("No valid polygon features found")
                return None

            gdf = gpd.GeoDataFrame.from_features(features, crs=4326)
            return gdf

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                sleep(5)
                continue
            return None
        except Exception as e:
            logger.warning(f"Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                sleep(5)
                continue
            return None

    return None


def datacollection(aoi, city_name, output_dir):
    """
    Download building footprints from OSM, clip to AOI, save as FlatGeobuf.

    Parameters
    ----------
    aoi : GeoDataFrame
        AOI polygon(s).
    city_name : str
        City name for naming output files.
    output_dir : str
        Directory where output will be saved.
    """

    logger.info("Starting building footprint collection...")

    if aoi is None or aoi.empty:
        logger.error("AOI is empty.")
        return None

    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    output_path = os.path.join(spatial_dir, f"{city_name}_building_footprints.fgb")

    if os.path.exists(output_path):
        logger.info(f"Building footprints already exist: {output_path}")
        return output_path

    bbox = aoi.total_bounds
    logger.info(f"Bounding box: {bbox}")

    buildings = get_osm_buildings(bbox)

    if buildings is None or len(buildings) == 0:
        logger.warning("No building data found for this area")
        return None

    # Clip to AOI polygon (not just bbox)
    aoi_4326 = aoi.to_crs(4326) if aoi.crs != "EPSG:4326" else aoi
    buildings = gpd.clip(buildings, aoi_4326)
    logger.info(f"Clipped to {len(buildings)} buildings within AOI")

    buildings.to_file(output_path, driver="FlatGeobuf")
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f"Saved {len(buildings)} buildings to: {output_path} ({file_size:.1f} MB)")

    return output_path
