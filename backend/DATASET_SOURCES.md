# Backend Dataset Sources

This document outlines where the City Scan automation backend fetches datasets from for various analysis components.

## Configuration and Infrastructure

### Google Cloud Storage
- **Main Bucket**: `crp-city-scan` - Stores user inputs, processed outputs, and rendered results
- **Data Bucket**: `city-scan-global-data` - Contains global reference datasets
- **Key Functions**: `utils.py:12-26`
  - `download_blob()` - Downloads data from GCS buckets
  - `upload_blob()` - Uploads processed results to GCS buckets

### Directory Structure
```
cloud/
├── bucket: 'crp-city-scan'
├── data_bucket: 'city-scan-global-data'
├── input_dir: '01-user-input'
├── output_dir: '02-process-output'
└── render_dir: '03-render-output'
```

## Dataset Sources by Component

### 1. Demographics (`demographics.py:10`)
**Source**: WorldPop API
- **URL**: `https://www.worldpop.org/rest/data/age_structures/ascic_2020?iso3={country_iso3}`
- **Data**: Age-structured population data by gender
- **Processing**: Downloads raster files, masks to AOI, aggregates by age groups

### 2. Population (`main.py:219`)
**Source**: WorldPop Hub API
- **URL**: `https://hub.worldpop.org/rest/data/pop/cic2020_100m?iso3={country_iso3}`
- **Data**: 100m resolution population density
- **Processing**: Mosaics multiple tiles, masks to AOI

### 3. OpenStreetMap Data (`GOSTnets/`)
**Source**: OpenStreetMap via OSMnx
- **Components**:
  - Points of Interest (`fetch_pois.py`)
  - Road networks (`load_osm.py`)
  - Origin-destination matrices (`fetch_od.py`)
- **APIs**: OSRM, Mapbox for routing calculations

### 4. Google Earth Engine (`gee_fun.py`)
**Source**: Google Earth Engine
- **Datasets**:
  - Forest cover (`gee_forest()`)
  - NDVI/Green coverage (`gee_ndxi()`)
  - Land cover classification (`gee_landcover()`)
  - Land surface temperature (`gee_lst()`)
  - NDMI moisture index (`gee_ndxi()`)
  - Nighttime lights (`gee_nightlight()`)

### 5. Flood Data (`fathom.py`)
**Source**: Fathom Global AWS S3
- **Access**: Via AWS credentials stored in `fathom_aws_credentials.yml`
- **Data**: Flood risk layers (coastal, fluvial, pluvial)
- **Processing**: Downloads and processes flood depth/probability data

### 6. Global Reference Datasets
Stored in `city-scan-global-data` bucket:

#### Urban Boundaries
- **UCDB**: Urban Centre Database for city boundary extraction
- **Countries**: Global country shapefiles for spatial queries

#### Climate & Environment
- **Fire Weather Index** (`fwi.py`): Historical fire risk data
- **Burned Area** (`burned_area.py`): Global fire occurrence records
- **Land Cover Burnability** (`landcover_burnability.py`): Vegetation flammability

#### Hazards & Risks
- **Elevation** (`elevation.py`): Digital elevation models
- **Air Quality** (`main.py:278`): Global air pollution data
- **Earthquake** (`earthquake_event.py`): Seismic hazard data
- **Landslide/Liquefaction** (`main.py:278`): Ground instability risk

#### Socioeconomic
- **Relative Wealth Index** (`rwi.py`): Facebook/Meta wealth estimates
- **World Settlement Footprint** (`wsf.py`): Built-up area classification

#### Infrastructure
- **Solar Potential** (`solar.py`): Renewable energy capacity
- **Road Networks** (`road_network.py`): Global transport infrastructure

## Data Processing Pipeline

### 1. Initialization (`main.py:102-123`)
```python
# Download configuration files
utils.download_blob(cloud_bucket, f"{input_dir}/city_inputs.yml", 'city_inputs.yml')
utils.download_blob(cloud_bucket, f"{input_dir}/global_inputs.yml", 'global_inputs.yml')
utils.download_blob(cloud_bucket, f"{input_dir}/menu.yml", 'menu.yml')
```

### 2. AOI Processing (`main.py:139-153`)
- Downloads city boundary from UCDB if not provided
- Uses country shapefiles for spatial context
- Saves AOI in local and cloud storage

### 3. Component Execution (`main.py:197-349`)
- Each component (task_index) processes specific datasets
- Parallel execution across 21 different analysis components
- Results uploaded to organized cloud storage structure

### 4. Output Organization
```
{city_dir}/02-process-output/
├── spatial/     # .tif, .gpkg files
├── tabular/     # .csv, .txt, .yml files
└── images/      # .png files
```

## Authentication & Access

### Google Cloud
- Uses default Google Cloud credentials
- Project: `city-scan-gee-test` (default)
- Region: `us-central1` (default)

### External APIs
- **Fathom**: AWS credentials required
- **Google Earth Engine**: Service account authentication
- **WorldPop**: Public API, no authentication
- **OSM**: Public data via OSMnx

## Configuration Files

### `city_inputs.yml`
- City-specific parameters
- AOI definitions
- Analysis timeframes
- Data source overrides

### `global_inputs.yml`
- Global dataset blob paths
- Default data sources
- Reference dataset locations

### `menu.yml`
- Analysis component toggles
- Defines which datasets to fetch/process

## Key Utilities

### `raster_pro.py`
- Raster data processing and masking
- Download and mosaic operations
- Spatial analysis functions

### `utils.py`
- Cloud storage operations
- Blob existence checking
- File upload/download management

### `aoi_helper.py`
- Boundary extraction from UCDB
- Country identification
- Spatial relationship queries