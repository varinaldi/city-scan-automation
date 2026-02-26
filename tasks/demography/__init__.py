from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    logger.info("Collecting demographic data...")
    datacollection(
        aoi=scan.aoi, city_name=scan.city_name,
        country_iso3=scan.country_iso3, output_dir=scan.output_dir,
        return_raster=False
    )


def analyze(scan):
    from .dataanalysis import demographic_aggregate
    from .datavisualization import age_distribution_plot

    logger.info("Analyzing demographic data...")
    demographic_aggregate(
        city_name=scan.city_name, output_dir=scan.output_dir,
        return_df=True
    )
    age_distribution_plot(
        city_name=scan.city_name, output_dir=scan.output_dir,
        render_dir=scan.render_dir, font_dict=scan.font_dict
    )


def run(scan):
    collect(scan)
    analyze(scan)
    logger.info("Done with demographic analysis")
