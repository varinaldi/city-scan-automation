# import
import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from core.py.log_module import setup_logger
import osmnx as ox
import yaml

logger = setup_logger(__name__)

def graph_collection(
        aoi: gpd.GeoDataFrame,
        city_name: str,
        output_dir: str,
        buffer: 5000,
        network_type='all', 
        simplify=True,
        return_graph: bool = True
    ):
    """
    Download street network graph from OSM given the AOI with optional buffers.

    Parameters
    ----------
    aoi : GeoDataFrame
        AOI polygon(s).
    city_name : str
        City name for naming output files.
    output_dir : str
        Directory where clipped raster will be saved.
    buffer: int
        Distance in meters to buffer AOI for graph extraction (default 5km). 
    network_type: str
        available network_type {"all", "all_public", "bike", "drive", "drive_service", "walk"}.
    return_graph : bool
        If True, return clipped raster array & metadata.

    Returns
    -------
    (graph) or None
    """

    logger.info("Starting street network graph collection…")

    # Validate AOI
    if aoi is None or aoi.empty:
        logger.error("AOI is empty. Cannot continue.")
        return None

    if aoi.crs is None:
        logger.error("AOI has no CRS defined.")
        return None

    logger.info(f"AOI CRS: {aoi.crs}")

    # Check for cached graphml first
    spatial_dir = os.path.join(output_dir, "spatial")
    graphml_path = os.path.join(spatial_dir, f"{city_name}_network.graphml")
    if os.path.exists(graphml_path) and return_graph:
        logger.info(f"Loading cached graph from {os.path.basename(graphml_path)}")
        road_graphs = ox.load_graphml(graphml_path)
        return road_graphs

    try:
        gdf_temp = aoi.to_crs(epsg=3857)
        buffered_geom = gdf_temp.geometry.iloc[0].buffer(buffer)
        buffered_geom = gpd.GeoSeries([buffered_geom], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]
        buffered_gdf = gpd.GeoDataFrame(geometry=[buffered_geom], crs="EPSG:4326")

        logger.info(f"Downloading {network_type} network for {city_name} with {buffer} meters of buffer")
        road_graphs = ox.graph_from_polygon(polygon=buffered_geom, network_type=network_type, simplify=simplify)
        if road_graphs is None or len(road_graphs.edges) == 0:
            logger.info(f"⚠️ No road network found for {city_name}")
            return
    
    except Exception as e:
        logger.error(f"Error reading network graph from OSM: {e}")
        return None

    # Create output directory & save graph
    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)

    # Save as geopackage (for GIS)
    gpkg_path = os.path.join(spatial_dir, f"{city_name}_nodes_and_edges.gpkg")
    try:
        ox.save_graph_geopackage(road_graphs, filepath=gpkg_path)
    except Exception as e:
        logger.error(f"Error saving road network gpkg: {e}")

    # Save as graphml (for fast reload in analyze)
    graphml_path = os.path.join(spatial_dir, f"{city_name}_network.graphml")
    try:
        ox.save_graphml(road_graphs, filepath=graphml_path)
    except Exception as e:
        logger.error(f"Error saving graphml: {e}")

    logger.info("street network graph extraction complete.")

    if return_graph:
        return road_graphs

    return None

def POI_collection(
    aoi,
    city_name = str,
    city_inputs_path=str,
    buffer =5000,
    output_dir=str
    ):
    """
    Extract OSM POIs from YAML configuration using OSMnx
    and export each category to a separate GeoPackage.
    
    Parameters
    ----------
    aoi : GeoDataFrame
        AOI polygon(s).
    city_name : str
        City name for naming output files.
    city_inputs_path : str
        path where city_inputs.yaml is stored.
    output_dir : str
        Directory where OSM POIs will be saved.
    buffer: int
        Distance in meters to buffer AOI for graph extraction (default 5km). 

    Returns
    -------
    None
    """
    logger.info("Starting OSM POI collection…")

    # Create output directory to store OSM POI
    spatial_dir = os.path.join(output_dir, "spatial")
    os.makedirs(spatial_dir, exist_ok=True)


    # -----------------------------------------------------
    # 1. Load YAML configuration
    # -----------------------------------------------------
    with open(city_inputs_path, "r") as f:
        config = yaml.safe_load(f)

    osm_queries = config["osm_query"]

    # Set OSMnx timeout to avoid hanging on Overpass API
    ox.settings.timeout = 120  # 2 minutes max per query

    # -----------------------------------------------------
    # 2. Prepare AOI geometry with buffer
    # -----------------------------------------------------
    # Validate AOI
    if aoi is None or aoi.empty:
        logger.error("AOI is empty. Cannot continue.")
        return None

    # Ensure AOI is in correct CRS for raster operations
    if aoi.crs is None:
        logger.error("AOI has no CRS defined.")
        return None

    logger.info(f"AOI CRS: {aoi.crs}")
    
    # Buffer geometry for x km # This is to ensure we capture the road network around the AOI
    gdf_temp = aoi.to_crs(epsg=3857)
    buffered_geom = gdf_temp.geometry.iloc[0].buffer(buffer)  # buffer by 5000 meters
    buffered_geom = gpd.GeoSeries([buffered_geom], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]  # back to EPSG:4326

    # -----------------------------------------------------
    # 3. Loop through POI categories
    # -----------------------------------------------------
    for name, tags in osm_queries.items():
        if tags is None:
            continue

        logger.info(f"Collecting: {name}")

        try:
            import threading

            result_container = [None]
            error_container = [None]

            def _query():
                try:
                    result_container[0] = ox.features_from_polygon(buffered_geom, tags)
                except Exception as e:
                    error_container[0] = e

            query_thread = threading.Thread(target=_query, daemon=True)
            query_thread.start()
            query_thread.join(timeout=120)

            if query_thread.is_alive():
                raise TimeoutError(f"OSM query for {name} timed out after 120s")
            if error_container[0] is not None:
                raise error_container[0]

            gdf = result_container[0]

            if gdf.empty:
                logger.info(f"⚠️  No features found for {name}")
                continue

            gdf = gdf[gdf.geometry.notnull()].copy()

            out_path = os.path.join(spatial_dir, f"{city_name}_osm_{name}.gpkg")
            gdf.to_file(out_path, driver="GPKG")

            logger.info(f"✓ Saved {name}: {len(gdf)} features")

        except (Exception, TimeoutError) as e:
            logger.warning(f"✘ Failed {name}: {e}")

    logger.info("POI collection complete.")
