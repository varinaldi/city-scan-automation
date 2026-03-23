"""
Run city scan tasks.

Usage:
    python -m tasks wsf                                        # new city (reads from inputs/)
    python -m tasks wsf --scan-id 2026-02-malta-malta          # existing city (reads from mnt/)
    python -m tasks wsf population forest                      # multiple tasks
    python -m tasks wsf --collect                              # collect only
    python -m tasks wsf --analyze                              # analyze only
    python -m tasks wsf --visualize                            # visualize only
    python -m tasks --all                                      # all tasks enabled in menu.yml
    python -m tasks --all --scan-id 2026-02-malta-malta        # all tasks for existing city
    python -m tasks --list                                     # show available tasks

Optional flags:
    --parallel                                                 # run tasks concurrently with TUI
    --upload                                                   # upload outputs to GCS after each step
"""
import sys
import os
import logging
import importlib


class ErrorTracker:
    """Counts ERROR+ log calls for the current thread only."""
    def __init__(self):
        self.count = 0
        self.messages = []
        self._original = None
        self._thread_id = None

    def __enter__(self):
        import threading
        self._thread_id = threading.current_thread().ident
        self._original = logging.Logger._log
        tracker = self
        original = self._original
        def _counting_log(logger_self, level, msg, args, **kwargs):
            if level >= logging.ERROR and threading.current_thread().ident == tracker._thread_id:
                tracker.count += 1
                try:
                    tracker.messages.append(str(msg) % args if args else str(msg))
                except Exception:
                    tracker.messages.append(str(msg))
            original(logger_self, level, msg, args, **kwargs)
        logging.Logger._log = _counting_log
        return self

    def __exit__(self, *exc):
        logging.Logger._log = self._original
        return False

# Add city root (parent of tasks/) to sys.path so core.py imports work from anywhere
_city_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _city_root not in sys.path:
    sys.path.insert(0, _city_root)

from core.py.log_module import setup_logger

logger = setup_logger("tasks")

# Tasks that require GEE authentication
GEE_TASKS = {"forest", "landcover", "lst", "green", "ndmi", "nightlight"}

# Tasks that require private GCS authentication
GCS_TASKS = {"wsf", "fathom", "landcover_burn", "basic_info", "oxford", "coastal_erosion", "sea_level_rise", "elevation"}

# CLI aliases: when CLI/menu name != folder name or functions have non-standard names
ALIASES = {
    "population": "worldpop",
    "green":      ("ndxi", {"collect": "collect_ndvi", "run": "run_ndvi"}),
    "ndmi":       ("ndxi", {"collect": "collect_ndmi", "run": "run_ndmi"}),
}


def discover_tasks():
    """Auto-discover tasks from tasks/ folders that have __init__.py."""
    from pathlib import Path
    tasks_dir = Path(__file__).parent
    registry = {}

    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir() or not (task_dir / "__init__.py").exists():
            continue
        name = task_dir.name
        module_path = f"tasks.{name}"
        try:
            mod = importlib.import_module(module_path)
            registry[name] = (
                module_path,
                "collect" if hasattr(mod, "collect") else None,
                "analyze" if hasattr(mod, "analyze") else None,
                "visualize" if hasattr(mod, "visualize") else None,
                "run" if hasattr(mod, "run") else None,
            )
        except Exception as e:
            logger.warning(f"Skipping task '{name}': {e}")

    # Add aliases
    for alias, target in ALIASES.items():
        if isinstance(target, str):
            if target in registry:
                registry[alias] = registry[target]
        elif isinstance(target, tuple):
            folder, fns = target
            if folder in registry:
                base = list(registry[folder])
                for step, fn_name in fns.items():
                    idx = {"collect": 1, "analyze": 2, "visualize": 3, "run": 4}[step]
                    base[idx] = fn_name
                registry[alias] = tuple(base)

    return registry


TASK_REGISTRY = discover_tasks()

# Menu keys that map to each CLI task (for --all mode)
MENU_KEYS = {
    "lst": ["lst_summer", "lst_winter"],
    "fathom": ["flood_pluvial", "flood_fluvial", "flood_coastal", "flood_comb"],
    "worldpop": ["population"],
}


def _menu_enabled(menu, task_name):
    keys = MENU_KEYS.get(task_name, [task_name])
    return any(menu.get(k) for k in keys)


def run_task(task_name, scan, step=None):
    """
    Run a single task. Returns a dict of phase results like:
      {"collect": "ok", "analyze": "fail", "visualize": "skip"}
    If running a single step (--collect/--analyze/--visualize), only that phase is in the dict.
    If running full (no step flag), runs collect → analyze → visualize in order.
    A phase failure does NOT stop the next phase — all phases are attempted.
    """
    if task_name not in TASK_REGISTRY:
        logger.error(f"Unknown task: {task_name}")
        return {"error": "unknown"}

    module_path, collect_fn, analyze_fn, visualize_fn, run_fn = TASK_REGISTRY[task_name]
    results = {}

    # Task header — visible in both sequential and parallel log views
    logger.info(f"\n{'='*50}\n  {task_name.upper()}\n{'='*50}")

    try:
        module = importlib.import_module(module_path)
    except Exception as e:
        logger.error(f"[{task_name}] import failed: {e}")
        return {"error": str(e)}

    if step == "multianalysis":
        # Multianalysis: run multianalysis.R or multianalysis.py if present
        import subprocess
        from pathlib import Path
        task_dir = Path(module.__file__).parent
        results["multianalysis"] = "skip"
        for ext in [".R", ".py"]:
            ma_file = task_dir / f"multianalysis{ext}"
            if ma_file.exists():
                header = f"  {task_name}: multianalysis"
                logger.info(f"\n{header}\n  {'─' * (len(header) - 2)}")
                with ErrorTracker() as tracker:
                    if ext == ".R":
                        subprocess.run(
                            ["Rscript", "-e", f"source(here::here('{ma_file.relative_to(task_dir.parent.parent)}'))"],
                            check=True
                        )
                    else:
                        exec(open(ma_file).read())
                results["multianalysis"] = "ERROR" if tracker.count > 0 else "OK"
                print()
                break
    elif step:
        # Single step mode: only run the requested phase
        fn_map = {"collect": collect_fn, "analyze": analyze_fn, "visualize": visualize_fn}
        fn_name = fn_map.get(step)
        if fn_name is None:
            results[step] = "skip"
        else:
            header = f"  {task_name}: {step}"
            logger.info(f"\n{header}\n  {'─' * (len(header) - 2)}")
            with ErrorTracker() as tracker:
                getattr(module, fn_name)(scan)
            results[step] = "ERROR" if tracker.count > 0 else "OK"
            if tracker.messages:
                for msg in tracker.messages:
                    logger.error(f"  [{task_name}:{step}] {msg}")
            print()
    else:
        # Full run: collect → analyze (visualize only runs with --visualize flag)
        for phase, fn_name in [("collect", collect_fn), ("analyze", analyze_fn)]:
            if fn_name is None:
                results[phase] = "skip"
                continue
            header = f"  {task_name}: {phase}"
            logger.info(f"\n{header}\n  {'─' * (len(header) - 2)}")
            with ErrorTracker() as tracker:
                getattr(module, fn_name)(scan)
            results[phase] = "ERROR" if tracker.count > 0 else "OK"
            if tracker.messages:
                for msg in tracker.messages:
                    logger.error(f"  [{task_name}:{phase}] {msg}")
            print()

    # Per-task summary
    parts = [f"{phase}: {status}" for phase, status in results.items()]
    logger.info(f"  [{task_name}] {' | '.join(parts)}\n")

    return results




def main():
    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        return

    if "--list" in args:
        # Show discovered tasks with their available steps
        print(f"  {'Task':<20} {'Steps'}")
        print(f"  {'-'*45}")
        for name, entry in sorted(TASK_REGISTRY.items()):
            _, collect_fn, analyze_fn, vis_fn, run_fn = entry
            steps = []
            if collect_fn: steps.append("collect")
            if analyze_fn: steps.append("analyze")
            if vis_fn: steps.append("visualize")
            if run_fn: steps.append("run")
            print(f"  {name:<20} {', '.join(steps)}")
        return

    # Determine step
    step = None
    if "--collect" in args:
        step = "collect"
    elif "--analyze" in args:
        step = "analyze"
    elif "--visualize" in args:
        step = "visualize"
    elif "--multianalysis" in args:
        step = "multianalysis"

    # Parse --scan-id
    scan_id = None
    if "--scan-id" in args:
        idx = args.index("--scan-id")
        if idx + 1 < len(args):
            scan_id = args[idx + 1]
        else:
            logger.error("--scan-id requires a value")
            return

    # Parse --upload flag (default: uploads disabled, opt-in with --upload)
    upload_enabled = "--upload" in args

    # Parse --parallel flag
    parallel_mode = "--parallel" in args

    # =========================================================
    # INITIALIZE
    # =========================================================
    print(f"\n  City Scan Automation")
    print(f"  {'─'*40}")

    from core.config.scan import Scan
    from core.config.paths import INPUTS, OUTPUTS

    # Check city folder when running from root
    if INPUTS.name == "inputs" and not scan_id:
        import yaml as _yaml
        with open(INPUTS / "city_inputs.yml") as _f:
            _ci = _yaml.safe_load(_f)
        import unicodedata
        _city = unicodedata.normalize('NFKD', _ci['city_name']).encode('ascii', 'ignore').decode('ascii').replace(' ', '_').replace("'", "").lower()
        from core.py.aoi_module import find_country as _fc
        import geopandas as _gpd
        _aoi = _gpd.read_file(str(INPUTS / f"AOI/{_ci['AOI_shp_name']}.shp")).to_crs(4326)
        _iso3, _country = _fc(aoi=_aoi)
        _expected_id = f"{__import__('datetime').datetime.now().strftime('%Y-%m')}-{_country}-{_city}"
        _existing = OUTPUTS / _expected_id
        if _existing.exists():
            print(f"\n  City folder exists: {_existing.name}")
            print(f"  [o] Override (re-copy tasks, core, source)")
            print(f"  [a] Abort")
            choice = input("  Choice (o/a):  ").strip().lower()
            if choice == 'o':
                scan_id = _expected_id
            else:
                print(f"\n  Run from the city folder instead:")
                print(f"    cd mnt/{_expected_id}")
                print(f"    python -m tasks --all\n")
                return
    elif INPUTS.name == "inputs" and scan_id:
        if not (OUTPUTS / scan_id).exists():
            print(f"  City folder not found: {scan_id}")
            return

    # Determine if running specific tasks (for selective sync)
    run_all = "--all" in args
    _specific_tasks = [a for a in args if not a.startswith("--") and a != scan_id]
    sync_tasks = None if run_all or not scan_id else (_specific_tasks or None)

    scan = Scan(scan_id=scan_id, sync_tasks=sync_tasks)

    # Set up file logging in city folder
    city_dir = os.path.dirname(str(scan.input_dir))
    from core.py.log_module import set_log_dir
    set_log_dir(os.path.join(city_dir, "logs"))

    # chdir to city folder
    if os.path.isdir(city_dir):
        os.chdir(city_dir)

    # Determine tasks
    run_all = "--all" in args
    task_names = [a for a in args if not a.startswith("--") and a != scan_id]
    if run_all:
        # Exclude simple aliases (e.g. population→worldpop) but keep function aliases (green, ndmi)
        simple_aliases = {k for k, v in ALIASES.items() if isinstance(v, str)}
        task_names = [name for name in TASK_REGISTRY
                      if _menu_enabled(scan.menu, name) and name not in simple_aliases]
    if not task_names:
        print("  No tasks to run.")
        return

    # Sort tasks so dependencies run first
    TASK_DEPENDENCIES = {
        "fathom": {"wsf"},
        "slope": {"elevation"},
        "worldpop": {"wsf", "oxford"},
        "landcover_burn": {"landcover"},
    }

    def _topo_sort(names, deps):
        """Sort tasks so dependencies come before dependents."""
        name_set = set(names)
        sorted_list = []
        visited = set()

        def visit(n):
            if n in visited:
                return
            visited.add(n)
            for dep in deps.get(n, set()):
                if dep in name_set:
                    visit(dep)
            sorted_list.append(n)

        for n in names:
            visit(n)
        return sorted_list

    task_names = _topo_sort(task_names, TASK_DEPENDENCIES)

    # Config summary
    print(f"\n  City:      {scan.city_inputs.get('city_name', scan.city_name)}")
    print(f"  Country:   {scan.country_name} ({scan.country_iso3})")
    print(f"  Scan ID:   {scan.cityscan_id}")

    # Task list
    print(f"\n  Tasks: {', '.join(task_names)}")

    # Authenticate
    from core.config.auth import init_gee, init_gcs
    skip_tasks = set()

    gee_needed = GEE_TASKS & set(task_names)
    gcs_needed = GCS_TASKS & set(task_names)

    if gee_needed:
        try:
            init_gee()
            print(f"  GEE:       authenticated")
        except Exception:
            print(f"  GEE:       not authenticated — {len(gee_needed)} tasks will be skipped")
            skip_tasks |= GEE_TASKS

    if gcs_needed:
        try:
            init_gcs()
            print(f"  GCS:       authenticated")
        except Exception:
            print(f"  GCS:       not authenticated — {len(gcs_needed)} tasks will be skipped")
            skip_tasks |= GCS_TASKS

    print(f"  {'─'*40}\n")

    # --- Run tasks ---
    step_label = f" ({step})" if step else ""

    if parallel_mode and len(task_names) > 1:
        # Parallel mode with TUI
        from core.py.multitask import run_parallel
        all_results = run_parallel(
            task_names, scan, step=step,
            run_task_fn=run_task, skip_tasks=skip_tasks
        )
    else:
        # Sequential mode (default)
        from core.py.gcs_module import get_all_files, upload_task_outputs
        all_results = {}

        for name in task_names:
            if name in skip_tasks:
                logger.warning(f"Skipping '{name}' (auth not available)")
                all_results[name] = "skipped"
                continue

            files_before = get_all_files(scan.output_dir) | get_all_files(scan.render_dir) if upload_enabled else None

            results = run_task(name, scan, step=step)
            all_results[name] = results

            if upload_enabled:
                upload_task_outputs(scan, name, step=step, files_before=files_before)

        # Sequential summary table
        if len(all_results) > 1:
            logger.info(f"\n{'='*50}\n  SUMMARY\n{'='*50}\n")

            phases = []
            for phase in ["collect", "analyze", "visualize"]:
                if any(phase in r for r in all_results.values() if isinstance(r, dict)):
                    phases.append(phase)

            col_w = 12
            header = f"  {'task':<20}" + "".join(f"{p:>{col_w}}" for p in phases)
            logger.info(header)
            logger.info(f"  {'─'*20}" + "".join(f"{'─'*col_w}" for _ in phases))

            for name, result in all_results.items():
                if isinstance(result, str):
                    row = f"  {name:<20}" + f"{'SKIP':>{col_w}}" * len(phases)
                else:
                    row = f"  {name:<20}" + "".join(f"{result.get(p, '—'):>{col_w}}" for p in phases)
                logger.info(row)

            print()

    # --- Copy scan-calculations to city folder ---
    if scan.menu.get("scan_calculations"):
        import shutil
        sc_src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scan-calculations")
        sc_dst = os.path.join(scan.city_dir, "scan-calculations")
        if os.path.exists(sc_src) and not os.path.exists(sc_dst):
            logger.info("Copying scan-calculations to city folder...")
            shutil.copytree(sc_src, sc_dst)


if __name__ == "__main__":
    main()
