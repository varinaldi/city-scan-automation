from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    logger.info("Collecting relative wealth index data...")
    datacollection(
        aoi=scan.aoi, city_name=scan.city_name,
        country_iso3=scan.country_iso3, output_dir=scan.output_dir,
        return_gdf=True
    )


def analyze(scan):
    from .dataanalysis import compute_stats_gdf
    from .datavisualization import run_viz_gdf

    logger.info("Analyzing relative wealth index data...")
    compute_stats_gdf(
        city_name=scan.city_name, output_dir=scan.output_dir,
        value_col='rwi'
    )
    run_viz_gdf(
        city_name=scan.city_name, output_dir=scan.output_dir,
        value_col='rwi'
    )


def run(scan):
    collect(scan)
    analyze(scan)
    logger.info("Done with relative wealth index analysis")
