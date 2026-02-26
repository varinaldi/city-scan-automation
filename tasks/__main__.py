"""
Run city scan tasks.

Usage:
    python -m tasks wsf                                        # new city (reads from inputs/)
    python -m tasks wsf --scan-id 2026-02-malta-malta          # existing city (reads from mnt/)
    python -m tasks wsf population forest                      # multiple tasks
    python -m tasks wsf --collect                              # collect only
    python -m tasks wsf --analyze                              # analyze only
    python -m tasks --all                                      # all tasks enabled in menu.yml
    python -m tasks --all --scan-id 2026-02-malta-malta        # all tasks for existing city
    python -m tasks --list                                     # show available tasks
"""
import sys
import importlib
from utils.log_module import setup_logger

logger = setup_logger("tasks")

# Tasks that require GEE authentication
GEE_TASKS = {"forest", "landcover", "lst", "green", "ndmi", "nightlight"}

# Tasks that require private GCS authentication
GCS_TASKS = {"wsf"}

# Registry: CLI name -> (module_path, collect_func, analyze_func, run_func)
# Order follows migrate.notes Part 5: Backend Task Index
TASK_REGISTRY = {
    # 0 — accessibility
    "accessibility":  ("tasks.accessibility", "collect", "analyze", "run"),
    # 1-5 — burned area
    "burned_area":    ("tasks.burned_area", "collect", "analyze", "run"),
    # 6 — demographics
    "demographics":   ("tasks.demography", "collect", "analyze", "run"),
    # 7 — population (WorldPop)
    "population":     ("tasks.population_worldpop", "collect", "analyze", "run"),
    # 8 — WSF
    "wsf":            ("tasks.wsf", "collect", "analyze", "run"),
    # 9 — elevation + slope
    "elevation":      ("tasks.elevation", "collect", "analyze", "run"),
    "slope":          ("tasks.slope", "collect", "analyze", "run"),
    # 11 — FWI
    "fwi":            ("tasks.fwi", "collect", "analyze", "run"),
    # 14 — RWI
    "rwi":            ("tasks.rwi", "collect", "analyze", "run"),
    # 15 — raster masking (air, landslide, liquefaction, solar)
    "air":            ("tasks.air_quality", "collect", "analyze", "run"),
    "landslide":      ("tasks.landslide", "collect", "analyze", "run"),
    "liquefaction":   ("tasks.liquefaction", "collect", "analyze", "run"),
    "solar":          ("tasks.solar", "collect", "analyze", "run"),
    # 16 — GEE tasks
    "forest":         ("tasks.forest", "collect", "analyze", "run"),
    "landcover":      ("tasks.landcover", "collect", "analyze", "run"),
    "lst":            ("tasks.lst", "collect", "analyze", "run"),
    "green":          ("tasks.ndxi", "collect_ndvi", None, "run_ndvi"),
    "ndmi":           ("tasks.ndxi", "collect_ndmi", None, "run_ndmi"),
    "nightlight":     ("tasks.nightlight", "collect", "analyze", "run"),
    # 21-22 — GHS
    "ghs_population": ("tasks.ghs_population", "collect", "analyze", "run"),
    "ghs_builtup":    ("tasks.ghs_builtup", "collect", "analyze", "run"),
}

# Menu keys that map to each CLI task (for --all mode)
MENU_KEYS = {
    "lst": ["lst_summer", "lst_winter"],
}


def _menu_enabled(menu, task_name):
    keys = MENU_KEYS.get(task_name, [task_name])
    return any(menu.get(k) for k in keys)


def run_task(task_name, scan, step=None):
    if task_name not in TASK_REGISTRY:
        logger.error(f"Unknown task: {task_name}")
        return False

    module_path, collect_fn, analyze_fn, run_fn = TASK_REGISTRY[task_name]
    try:
        module = importlib.import_module(module_path)

        if step == "collect":
            func = getattr(module, collect_fn)
            func(scan)
        elif step == "analyze":
            if analyze_fn is None:
                logger.warning(f"Task '{task_name}' has no analyze step")
                return True
            func = getattr(module, analyze_fn)
            func(scan)
        else:
            func = getattr(module, run_fn)
            func(scan)

        return True
    except Exception as e:
        logger.error(f"Error in task '{task_name}': {e}")
        return False


def main():
    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        return

    if "--list" in args:
        for name in TASK_REGISTRY:
            print(f"  {name}")
        return

    # Determine step
    step = None
    if "--collect" in args:
        step = "collect"
    elif "--analyze" in args:
        step = "analyze"

    # Parse --scan-id
    scan_id = None
    if "--scan-id" in args:
        idx = args.index("--scan-id")
        if idx + 1 < len(args):
            scan_id = args[idx + 1]
        else:
            logger.error("--scan-id requires a value")
            return

    # Build scan config (one-time setup)
    from config.scan import Scan
    scan = Scan(scan_id=scan_id)

    run_all = "--all" in args
    task_names = [a for a in args if not a.startswith("--") and a != scan_id]

    if run_all:
        task_names = [
            name for name in TASK_REGISTRY
            if _menu_enabled(scan.menu, name)
        ]

    if not task_names:
        logger.warning("No tasks to run.")
        return

    # Authenticate if needed — skip tasks that need failed auth
    from config.auth import init_gee, init_gcs
    skip_tasks = set()

    if GEE_TASKS & set(task_names):
        try:
            init_gee()
        except Exception as e:
            logger.warning(f"GEE auth failed: {e} — skipping GEE tasks")
            skip_tasks |= GEE_TASKS

    if GCS_TASKS & set(task_names):
        try:
            init_gcs()
        except Exception as e:
            logger.warning(f"GCS auth failed: {e} — skipping private GCS tasks")
            skip_tasks |= GCS_TASKS

    # Run tasks, skip failed auth and failed tasks
    failed = []
    step_label = f" ({step})" if step else ""
    logger.info(f"Running tasks{step_label}: {', '.join(task_names)}")
    for name in task_names:
        if name in skip_tasks:
            logger.warning(f"Skipping '{name}' (auth not available)")
            failed.append(name)
            continue
        if not run_task(name, scan, step=step):
            failed.append(name)

    # Summary
    if failed:
        logger.warning(f"Failed/skipped tasks: {', '.join(failed)}")
    else:
        logger.info("All tasks completed successfully")


if __name__ == "__main__":
    main()
