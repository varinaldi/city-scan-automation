# Backend-Local

Modified versions of backend functions for local processing. These save directly to `mnt/` folders without using GCP.

## Files

- **`gee_local.py`** - Task 16 (GEE outputs)
  - Exports to Google Drive folder: `city-scan-outputs`
  - You need to manually download files from Google Drive
  - Functions: `gee_forest`, `gee_ndvi`, `gee_landcover`, `gee_lst_summer`, `gee_lst_winter`, `gee_ndmi`, `gee_nightlight`

- **`population_local.py`** - Task 7 (WorldPop population)
  - Downloads and saves directly to `mnt/{city}/02-process-output/spatial/`
  - Function: `run_population(city_name_l, country_iso3, aoi_file, output_spatial)`

- **`demographics_local.py`** - Task 6 (Demographics)
  - Downloads and saves directly to `mnt/{city}/02-process-output/tabular/`
  - Function: `run_demographics(city_name_l, country_iso3, aoi_file, output_tabular)`

## Usage

See `run_tasks_locally.ipynb` for examples.

## Note

The original `backend/` folder is **NOT modified** and still works for GCP uploads.
