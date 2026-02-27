from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    logger.info("Collecting GHS population data...")
    datacollection(
        aoi=scan.aoi, city_name=scan.city_name,
        output_dir=scan.output_dir
    )


def analyze(scan):
    from .dataanalysis import compute_stats

    logger.info("Analyzing GHS population data...")
    compute_stats(
        city_name=scan.city_name, output_dir=scan.output_dir,
        start_year=1975, end_year=2030
    )


def visualize(scan):
    from .datavisualization import run_viz

    logger.info("Visualizing GHS population data...")
    run_viz(
        city_name=scan.city_name, output_dir=scan.output_dir,
        start_year=1975, end_year=2030
    )


def run(scan):
    collect(scan)
    analyze(scan)
    logger.info("Done with GHS population analysis")
