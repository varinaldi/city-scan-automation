import os
import ee
from utils.log_module import setup_logger

logger = setup_logger(__name__)

GCS_CREDENTIALS = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
GEE_PROJECT = "city-scan-gee-test"


def init_gee():
    ee.Initialize(project=GEE_PROJECT)
    logger.info(f"GEE initialized with project: {GEE_PROJECT}")


def init_gcs():
    if not os.path.exists(GCS_CREDENTIALS):
        raise RuntimeError(f"GCS credentials not found: {GCS_CREDENTIALS}. Run: gcloud auth application-default login")
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GCS_CREDENTIALS
    logger.info(f"GCS credentials set: {GCS_CREDENTIALS}")
