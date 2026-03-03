from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    logger.info("Collecting WSF data...")
    datacollection(
        aoi=scan.aoi, city_name=scan.city_name,
        output_dir=scan.output_dir, return_raster=True
    )


def analyze(scan):
    from .dataanalysis import stats_wsf, harmonize_wsf

    logger.info("Analyzing WSF data...")
    stats_wsf(city_name=scan.city_name, output_dir=scan.output_dir, dataset="tracker")
    stats_wsf(city_name=scan.city_name, output_dir=scan.output_dir, dataset="evolution")
    harmonize_wsf(city_name=scan.city_name, output_dir=scan.output_dir)


def run(scan):
    collect(scan)
    analyze(scan)
    logger.info("Done with WSF analysis")
