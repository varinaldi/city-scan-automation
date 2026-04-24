import os
import ee
from core.py.log_module import setup_logger

logger = setup_logger(__name__)

GEE_PROJECT = os.environ.get("GEE_PROJECT", "city-scan-gee-test")


def _on_cloud_run():
    return os.environ.get("K_SERVICE") is not None


def init_gee():
    """Initialize GEE. Uses existing credentials, falls back to gcloud ADC.

    Does NOT interactively authenticate — that would hang a task run.
    If both tiers fail, raises with a clear instruction to run `scan --check gee`
    as a one-time setup.
    """
    # Tier 1: existing credentials
    try:
        ee.Initialize(project=GEE_PROJECT)
        logger.info(f"GEE initialized (project={GEE_PROJECT})")
        return
    except Exception:
        pass

    # Tier 2: gcloud ADC. Requires ADC to have been created with the earthengine
    # scope — otherwise gcloud will trigger a browser re-login (bad UX mid-run).
    # See check_env.py for the one-time setup command.
    try:
        ee.Authenticate(auth_mode="gcloud", quiet=True, scopes=[
            "https://www.googleapis.com/auth/earthengine",
            "https://www.googleapis.com/auth/cloud-platform",
        ])
        ee.Initialize(project=GEE_PROJECT)
        logger.info(f"GEE initialized via gcloud (project={GEE_PROJECT})")
        return
    except Exception:
        pass

    raise RuntimeError(
        "GEE authentication failed. Run `scan --check gee` for a guided fix, or:\n"
        "  gcloud auth application-default login \\\n"
        "    --scopes=openid,https://www.googleapis.com/auth/userinfo.email,"
        "https://www.googleapis.com/auth/cloud-platform,"
        "https://www.googleapis.com/auth/earthengine"
    )


def init_gcs():
    """Ensure GCS access is available.

    - Cloud Run: ADC is injected by the runtime (nothing to do).
    - Local: relies on `gcloud auth application-default login`.
      google.cloud.storage.Client() picks up ADC automatically.
    """
    if _on_cloud_run():
        logger.info("GCS: running on Cloud Run, using service account ADC")
        return

    # Local: just verify ADC exists so we can give a helpful error early
    if os.name == "nt":  # Windows
        adc_path = os.path.join(os.environ["APPDATA"], "gcloud", "application_default_credentials.json")
    else:
        adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if not os.path.exists(adc_path):
        raise RuntimeError(
            "GCS credentials not found. Run:\n"
            "  gcloud auth application-default login"
        )
    # Configure GDAL to use the same ADC for /vsigs/ access
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = adc_path
    logger.info("GCS: using local ADC credentials")
