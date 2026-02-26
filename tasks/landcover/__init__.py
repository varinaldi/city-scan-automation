from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    logger.info("Collecting land cover data...")
    datacollection(
        aoi=scan.aoi, city_name=scan.city_name,
        output_dir=scan.output_dir
    )


def analyze(scan):
    from .dataanalysis import dataanalysis

    logger.info("Analyzing land cover data...")
    dataanalysis(
        city_name=scan.city_name, output_dir=scan.output_dir
    )


def run(scan):
    collect(scan)
    analyze(scan)
    logger.info("Done with land cover analysis")
