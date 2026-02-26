import os
import shutil
import yaml
import geopandas as gpd
from datetime import datetime as dt
from config.paths import INPUTS, OUTPUTS
from utils.aoi_module import find_country
from utils.log_module import setup_logger

logger = setup_logger(__name__)


class Scan:
    def __init__(self, scan_id=None):
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

        self.city_name = (
            self.city_inputs['city_name']
            .replace(' ', '_')
            .replace("'", "")
            .lower()
        )
        self.first_year = self.city_inputs['first_year']
        self.last_year = self.city_inputs['last_year']
        self.fwi_first_year = self.city_inputs.get('fwi_first_year')
        self.fwi_last_year = self.city_inputs.get('fwi_last_year')

        # Load AOI
        aoi_path = input_source / f"AOI/{self.city_inputs['AOI_shp_name']}.shp"
        self.aoi = gpd.read_file(aoi_path).to_crs(4326)
        logger.info(f'Successfully loaded AOI from: {aoi_path}')

        # Country lookup
        self.country_iso3, self.country_name = find_country(aoi=self.aoi)

        # Build cityscan_id if not provided via --scan-id
        if not scan_id:
            prev = self.city_inputs.get('prev_run_date', None)
            if prev is not None:
                self.cityscan_id = f"{prev}-{self.country_name}-{self.city_name}"
            else:
                self.cityscan_id = f"{dt.now().strftime('%Y-%m')}-{self.country_name}-{self.city_name}"

        logger.info(f'Working on {self.cityscan_id}')

        # Directory paths
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

        # Copy inputs to city folder if first time
        if not scan_id and not (self.input_dir / "city_inputs.yml").exists():
            logger.info(f"First run — copying inputs to {self.input_dir}")
            self._copy_inputs(self.input_dir)

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
