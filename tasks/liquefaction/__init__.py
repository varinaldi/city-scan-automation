from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    logger.info("Collecting liquefaction data...")
    datacollection(
        aoi=scan.aoi, city_name=scan.city_name,
        output_dir=scan.output_dir, return_raster=True
    )


def analyze(scan):
    from .dataanalysis import compute_stats

    logger.info("Analyzing liquefaction data...")
    compute_stats(
        city_name=scan.city_name, output_dir=scan.output_dir,
        return_df=False
    )


def visualize(scan):
    from .datavisualization import plot_rastermap, plot_histogram

    logger.info("Visualizing liquefaction data...")
    plot_rastermap(city_name=scan.city_name, output_dir=scan.output_dir)
    plot_histogram(city_name=scan.city_name, output_dir=scan.output_dir)


def run(scan):
    collect(scan)
    analyze(scan)
    logger.info("Done with liquefaction analysis")
