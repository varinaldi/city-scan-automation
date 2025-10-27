# Backend Dataset Sources

This document outlines where the City Scan automation backend fetches datasets from for various analysis components.

## Quick Reference: All Data Sources by Topic

| Task Index | Topic | Primary Data Source | Source Type |
|------------|-------|---------------------|-------------|
| 0 | Accessibility | OpenStreetMap (OSMnx) | API |
| 1-5 | Burned Area | GlobFire | GCS Bucket |
| 6 | Demographics | WorldPop API | API |
| 7 | Population | WorldPop Hub API | API |
| 8 | Urban Settlement (WSF) | DLR WSF Evolution | Direct Download |
| 9 | Elevation & Slope | Global DEM | GCS Bucket |
| 10 | Flood Risk | Fathom Global | AWS S3 |
| 11 | Fire Weather Index | FWI Dataset | GCS Bucket |
| 12 | Land Cover Burnability | ESA CCI Land Cover | GCS Bucket |
| 13 | Road Network | OpenStreetMap (OSMnx) | API |
| 14 | Relative Wealth Index | Meta/Facebook RWI | GCS Bucket |
| 15 | Air/Landslide/Liquefaction/Solar | Global Rasters | GCS Bucket |
| 16 | GEE (Forest/Green/LST/NDMI/Nightlight) | Google Earth Engine | GEE API |
| 17 | Basic Info | Köppen Classification | GCS Bucket |
| 18 | Oxford Economics | Oxford Economics + CityPopulation.de | GCS Bucket + Web Scrape |
| 19 | Earthquake Events | Earthquake Archive | API |
| 20 | Flood Events | Flood Archive | GCS Bucket |
| 21 | GHS Population | JRC Global Human Settlement Layer | Direct Download |
| - | Buildings (optional) | Microsoft Global ML | Direct Download |

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

### 3. World Settlement Footprint Evolution (`wsf.py`)
**Source**: DLR (German Aerospace Center) World Settlement Footprint Evolution
- **URL**: `https://download.geoservice.dlr.de/WSF_EVO/files/`
- **Data**: Urban built-up area evolution by year (1985-2015)
- **Resolution**: 2° x 2° tiles at 30m resolution
- **Processing**: Downloads tiles based on AOI bounds, mosaics, masks to AOI, calculates cumulative growth statistics
- **Reference**: `wsf.py:19`

### 4. OpenStreetMap Data (`GOSTnets/`, `accessibility.py`, `road_network.py`)
**Source**: OpenStreetMap via OSMnx
- **Components**:
  - Points of Interest (`fetch_pois.py`, `accessibility.py`)
  - Road networks (`load_osm.py`, `road_network.py`)
  - Origin-destination matrices (`fetch_od.py`)
  - Accessibility isochrones (`accessibility.py`)
- **APIs**: OSRM, Mapbox for routing calculations
- **Network Analysis**: Edge/node centrality, bearings, connectivity

### 5. Google Earth Engine (`gee_fun.py`)
**Source**: Google Earth Engine
- **Datasets**:
  - Forest cover (`gee_forest()`)
  - NDVI/Green coverage (`gee_ndxi()`)
  - Land cover classification (`gee_landcover()`)
  - Land surface temperature (`gee_lst()`)
  - NDMI moisture index (`gee_ndxi()`)
  - Nighttime lights (`gee_nightlight()`)

### 6. Flood Data (`fathom.py`)
**Source**: Fathom Global AWS S3
- **Access**: Via AWS credentials stored in `fathom_aws_credentials.yml`
- **Data**: Flood risk layers (coastal, fluvial, pluvial)
- **Processing**: Downloads and processes flood depth/probability data

### 7. Global Reference Datasets
Stored in `city-scan-global-data` bucket:

#### Urban Boundaries
- **UCDB**: Urban Centre Database for city boundary extraction
- **Countries**: Global country shapefiles for spatial queries

#### Climate & Environment
- **Fire Weather Index** (`fwi.py`): Historical fire risk data (weekly FWI rasters)
- **Burned Area** (`burned_area.py`): GlobFire monthly shapefiles (2009-2021)
- **Land Cover Burnability** (`landcover_burnability.py`): ESA CCI Land Cover-derived vegetation flammability
- **Köppen Climate Classification** (`basic_info.py`): Global climate classification CSV

#### Hazards & Risks
- **Elevation** (`elevation.py`): Digital elevation models
- **Air Quality** (`main.py:278`): Global air pollution data
- **Earthquake** (`earthquake_event.py`): Seismic hazard data
- **Landslide/Liquefaction** (`main.py:278`): Ground instability risk

#### Socioeconomic
- **Relative Wealth Index** (`rwi.py`): Facebook/Meta wealth estimates (QuadKey-based, country-specific)
- **Oxford Economics** (`oe_plot.py`): Population, GDP, employment data for benchmark cities
- **CityPopulation.de** (`oe_plot.py:182`): Web-scraped population growth data (fallback source)

#### Infrastructure
- **Solar Potential** (`solar.py`): Renewable energy capacity (monthly PV yield data)
- **Road Networks** (`road_network.py`): OpenStreetMap transport infrastructure

### 8. GHS Population (`ghs_population.py`)
**Source**: JRC Global Human Settlement Layer Population Grid
- **URL Base**: `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A`
- **Tile Index**: `https://ghsl.jrc.ec.europa.eu/download/GHSL_data_54009_shapefile.zip`
- **Data**: Population density grids for years 1975-2030 (5-year intervals)
- **Resolution**: 100m in Mollweide projection (EPSG:54009)
- **Processing**: Downloads intersecting tiles, mosaics in Mollweide, clips to AOI, reprojects to EPSG:4326
- **Years Available**: 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025, 2030
- **Reference**: `ghs_population.py:28`, `main.py:353`

### 9. Optional/Standalone Datasets

#### Microsoft Building Footprints (`buildings.py`)
**Note**: This is a standalone script not integrated into the main pipeline
- **Source**: Microsoft Global ML Building Footprints
- **URL**: `https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv`
- **Data**: AI-detected building footprints by country and QuadKey
- **Format**: FlatGeobuf (.fgb) tiles
- **Reference**: `buildings.py:81`

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

### 3. Component Execution (`main.py:197-356`)
- Each component (task_index) processes specific datasets
- Parallel execution across 22 different analysis components (0-21)
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
- **Fathom**: AWS credentials required (`fathom_aws_credentials.yml`)
- **Google Earth Engine**: Service account authentication
- **WorldPop**: Public API, no authentication
- **OSM**: Public data via OSMnx
- **JRC GHSL**: Public data, no authentication

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
- Controls task execution (0-21)

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
