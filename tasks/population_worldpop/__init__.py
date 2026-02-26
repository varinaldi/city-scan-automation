from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    logger.info("Collecting WorldPop population data...")
    datacollection(
        aoi=scan.aoi, city_name=scan.city_name,
        country_iso3=scan.country_iso3, output_dir=scan.output_dir,
        return_raster=True
    )


def analyze(scan):
    from .dataanalysis import compute_stats, stats_worldpop
    from .datavisualization import plot_rastermap, plot_histogram

    logger.info("Analyzing WorldPop population data...")
    compute_stats(
        city_name=scan.city_name, output_dir=scan.output_dir,
        return_df=False
    )
    stats_worldpop(city_name=scan.city_name, output_dir=scan.output_dir, dataset="worldpop_2000_2020")
    stats_worldpop(city_name=scan.city_name, output_dir=scan.output_dir, dataset="worldpop_2015_2030")
    plot_rastermap(city_name=scan.city_name, output_dir=scan.output_dir)
    plot_histogram(city_name=scan.city_name, output_dir=scan.output_dir)


def run(scan):
    collect(scan)
    analyze(scan)
    logger.info("Done with population WorldPop analysis")
