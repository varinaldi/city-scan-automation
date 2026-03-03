from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    logger.info("Collecting fathom data...")
    datacollection(
        aoi=scan.aoi, 
        city_name=scan.city_name,
        city_inputs=scan.city_inputs,
        menu=scan.menu,
        output_dir=scan.output_dir
    )


# def analyze(scan):
#     from .dataanalysis import generate_contours, elevation_stats, elevation_interpretation

#     logger.info("Analyzing elevation data...")
#     generate_contours(
#         city_name=scan.city_name, output_dir=scan.output_dir,
#         return_gdf=False
#     )
#     elevation_stats(
#         city_name=scan.city_name, output_dir=scan.output_dir
#     )
#     elevation_interpretation(
#         city_name=scan.city_name, output_dir=scan.output_dir
#     )


# def visualize(scan):
#     from .datavisualization import plot_elevation_rastermap, plot_elevation_stats

#     logger.info("Visualizing elevation data...")
#     plot_elevation_rastermap(
#         city_name=scan.city_name, output_dir=scan.output_dir
#     )
#     plot_elevation_stats(
#         city_name=scan.city_name, output_dir=scan.output_dir,
#         render_dir=scan.render_dir
#     )


def run(scan):
    collect(scan)
    # analyze(scan)
    logger.info("Done with fathom analysis")
