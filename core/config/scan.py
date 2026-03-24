import os
import shutil
import yaml
import geopandas as gpd
from datetime import datetime as dt
from .paths import INPUTS, OUTPUTS, PROJECT_ROOT
from core.py.aoi_module import find_country
from core.py.log_module import setup_logger

logger = setup_logger(__name__)


class Scan:
    def __init__(self, scan_id=None, sync_tasks=None):
        # Determine input source
        if scan_id:
            input_source = OUTPUTS / f'{scan_id}/01-user-input'
            self.cityscan_id = scan_id

            # If city folder exists but has no inputs, copy from inputs/
            if not (input_source / "city_inputs.yml").exists():
                logger.info(f"No city_inputs.yml in {input_source}, copying from {INPUTS}")
                self._copy_inputs(input_source)
        else:
            input_source = INPUTS

        # Load city inputs
        self.city_inputs_path = input_source / "city_inputs.yml"
        with open(self.city_inputs_path) as f:
            self.city_inputs = yaml.safe_load(f)

        import unicodedata
        self.city_name = (
            unicodedata.normalize('NFKD', self.city_inputs['city_name'])
            .encode('ascii', 'ignore').decode('ascii')
            .replace(' ', '_')
            .replace("'", "")
            .lower()
        )
        self.first_year = self.city_inputs['first_year']
        self.last_year = self.city_inputs['last_year']
        self.fwi_first_year = self.city_inputs.get('fwi_first_year')
        self.fwi_last_year = self.city_inputs.get('fwi_last_year')
        
        # flood related inputs
        flood_cfg = self.city_inputs.get("flood", {})
        self.flood_threshold = flood_cfg.get("threshold")
        self.flood_year = flood_cfg.get("year")
        self.flood_ssp = flood_cfg.get("ssp")
        self.flood_return_periods = flood_cfg.get("return_period", [])

        # Load AOI
        aoi_path = input_source / f"AOI/{self.city_inputs['AOI_shp_name']}.shp" # TO DO: allow geojson, gpkg, KML, KMZ in the future
        self.aoi = gpd.read_file(aoi_path).to_crs(4326)
        logger.info(f'Successfully loaded AOI from: {aoi_path}')

        # Country lookup
        self.country_iso3, self.country_name = find_country(aoi=self.aoi)

        # Build cityscan_id if not provided via --scan-id
        if not scan_id:
            # If running from a city folder (01-user-input exists), use the folder name as scan_id
            from .paths import _city_root
            if INPUTS.name == "01-user-input":
                self.cityscan_id = _city_root.name
            else:
                prev = self.city_inputs.get('prev_run_date', None)
                if prev is not None:
                    self.cityscan_id = f"{prev}-{self.country_name}-{self.city_name}"
                else:
                    self.cityscan_id = f"{dt.now().strftime('%Y-%m')}-{self.country_name}-{self.city_name}"

        logger.info(f'Working on {self.cityscan_id}')

        # Directory paths
        self.city_dir = OUTPUTS / self.cityscan_id
        self.input_dir = OUTPUTS / f'{self.cityscan_id}/01-user-input'
        self.output_dir = OUTPUTS / f'{self.cityscan_id}/02-process-output'
        self.render_dir = OUTPUTS / f'{self.cityscan_id}/03-render-output'
        self.spatial_dir = f'{self.output_dir}/spatial'
        self.tabular_dir = f'{self.output_dir}/tabular'

        # Create directories
        for d in [
            self.input_dir,
            f'{self.output_dir}/images/',
            self.spatial_dir,
            self.tabular_dir,
            self.render_dir,
            f'{self.render_dir}/plots/png',
            f'{self.render_dir}/plots/html',
        ]:
            os.makedirs(d, exist_ok=True)

        # Copy inputs and project files to city folder if first time
        city_root = OUTPUTS / self.cityscan_id
        if not scan_id and not (self.input_dir / "city_inputs.yml").exists():
            logger.info(f"First run — copying inputs to {self.input_dir}")
            self._copy_inputs(self.input_dir)

        # Copy project structure (core, tasks, source, etc.) if not present
        skip_patterns = {"__pycache__", ".quarto", "index_files", "index.html", ".Rproj.user", "node_modules"}
        def _ignore(dir, files):
            return [f for f in files if f in skip_patterns]

        create_once = ["logs"]

        if PROJECT_ROOT.resolve() != city_root.resolve():
            # Check if city folder already has synced code
            has_existing = (city_root / "source").exists() or (city_root / "core").exists()

            if has_existing:
                print("\n  City folder already has project files.")
                print("  [c] Copy tasks only")
                print("  [o] Override tasks + core + source (WARNING: overwrites city configs!)")
                print("  [a] Abort")
                choice = input("  Choose [c/o/a]: ").strip().lower()

                if choice == 'a':
                    logger.info("Aborted by user.")
                    raise SystemExit("Aborted.")
                elif choice == 'o':
                    sync_all = True
                else:
                    sync_all = False
            else:
                # First run — copy everything
                sync_all = True

            if sync_all:
                for folder in ["core", "source", "scan-calculations"]:
                    src = PROJECT_ROOT / folder
                    dst = city_root / folder
                    if src.exists():
                        shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)

            # Sync task folders — always copied
            if sync_tasks is None:
                src = PROJECT_ROOT / "tasks"
                dst = city_root / "tasks"
                if src.exists():
                    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)
            else:
                tasks_dst = city_root / "tasks"
                tasks_dst.mkdir(exist_ok=True)
                main_src = PROJECT_ROOT / "tasks" / "__main__.py"
                if main_src.exists():
                    shutil.copy2(main_src, tasks_dst / "__main__.py")
                for task_name in sync_tasks:
                    src = PROJECT_ROOT / "tasks" / task_name
                    dst = tasks_dst / task_name
                    if src.exists():
                        shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)

            for folder in create_once:
                src = PROJECT_ROOT / folder
                dst = city_root / folder
                if src.exists() and not dst.exists():
                    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)
        # Create .here marker for R's here package
        here_dst = city_root / ".here"
        if not here_dst.exists():
            here_dst.touch()

        # Load menu
        menu_path = input_source / "menu.yml"
        self.menu = yaml.safe_load(open(menu_path))

        # Plot font config
        self.font_dict = {
            'family': (
                'system-ui, -apple-system, "Segoe UI", Roboto, '
                '"Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", '
                'sans-serif, "Apple Color Emoji", "Segoe UI Emoji", '
                '"Segoe UI Symbol", "Noto Color Emoji"'
            ),
            'size': 12,
            'color': 'black',
        }

    def _copy_inputs(self, dest):
        os.makedirs(dest, exist_ok=True)
        for f in ["city_inputs.yml", "menu.yml"]:
            src = INPUTS / f
            if src.exists():
                shutil.copy2(src, dest / f)
        aoi_src = INPUTS / "AOI"
        aoi_dst = dest / "AOI"
        if aoi_src.exists() and not aoi_dst.exists():
            shutil.copytree(aoi_src, aoi_dst)
