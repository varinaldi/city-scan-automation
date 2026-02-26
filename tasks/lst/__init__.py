from utils.log_module import setup_logger
logger = setup_logger(__name__)


def collect(scan):
    from .datacollection import datacollection

    composite = []
    if scan.menu.get("lst_summer"):
        composite.append('summer')
    if scan.menu.get("lst_winter"):
        composite.append('winter')
    if not composite:
        composite = ['summer', 'winter']

    logger.info(f"Collecting LST data ({composite})...")
    datacollection(
        aoi=scan.aoi, city_name=scan.city_name,
        output_dir=scan.output_dir, composite=composite,
        first_year=scan.first_year, last_year=scan.last_year
    )


def analyze(scan):
    logger.info("LST has no separate analysis step")


def run(scan):
    collect(scan)
    analyze(scan)
    logger.info("Done with LST data collection")
