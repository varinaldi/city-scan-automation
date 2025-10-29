# Backend Dataset Sources

This document outlines where the City Scan automation backend fetches datasets from for various analysis components.

## Processing Architecture: Server-Side vs Client-Side

Understanding where data processing happens is crucial for efficiency and cost optimization.

| Data Source | Current Backend | Processing Location | Network Transfer | Efficiency |
|-------------|----------------|---------------------|------------------|------------|
| **GEE datasets** | Server-side ✅ | Google's servers | Tiny (~KB) | High ✅ |
| **GCS TIFs** | Client-side ❌ | Cloud Run container | Huge (~GB) | Low ❌ |
| **WorldPop API** | Server-side ✅ | WorldPop servers | Medium (~MB for tiles) | Medium |
| **OSM API** | Server-side ✅ | OSM servers | Small (~MB for AOI) | High ✅ |
| **Fathom AWS** | Client-side ❌ | Cloud Run container | Large (~GB) | Low ❌ |

### What This Means:

**Server-Side Processing (Efficient):**
- Processing happens on the data provider's servers
- Only results are downloaded to your environment
- Example: GEE clips a global landcover dataset and returns only histogram → downloads ~1KB

**Client-Side Processing (Inefficient):**
- Entire dataset downloaded to Cloud Run container
- Processing happens in the container (uses your compute/memory)
- Example: Download 50GB DEM, clip to small AOI, use 1GB → wasted 49GB transfer

**Optimization Opportunity:** Converting client-side operations to server-side (or COG-based streaming) could reduce network costs by ~80%.

## Quick Reference: All Data Sources by Topic

| Task Index | Topic | Dataset Name | Access Type | Authentication | Python File |
|------------|-------|--------------|-------------|----------------|-------------|
| 0 | Accessibility | OpenStreetMap (OSM) | Public API | None | [`accessibility.py`](backend/accessibility.py) |
| 1-5 | Burned Area | MODIS GlobFire MCD64A1 | GCS Bucket | Google Cloud | [`burned_area.py`](backend/burned_area.py) |
| 6 | Demographics | WorldPop Age-Sex Structures (ASCIC 2020) | Public API | None | [`demographics.py`](backend/demographics.py) |
| 7 | Population | WorldPop Constrained Individual Countries (CIC 2020) | Public API | None | [`main.py`](backend/main.py#L222) |
| 8 | Urban Settlement | DLR World Settlement Footprint Evolution | Public Download | None | [`wsf.py`](backend/wsf.py) |
| 9 | Elevation & Slope | University of Bristol Global FABDEM | Public Download | None | [`elevation.py`](backend/elevation.py) |
| 10 | Flood Risk | Fathom Global Flood Maps v3.0 | AWS S3 (WBG) | AWS Credentials Required | [`fathom.py`](backend/fathom.py) |
| 11 | Fire Weather Index | CRU Fire Weather Index | GCS Bucket | Google Cloud | [`fwi.py`](backend/fwi.py) |
| 12 | Land Cover Burnability | ESA CCI Land Cover + Custom Burnability Index | GCS Bucket | Google Cloud | [`landcover_burnability.py`](backend/landcover_burnability.py) |
| 13 | Road Network | OpenStreetMap (OSM) | Public API | None | [`road_network.py`](backend/road_network.py) |
| 14 | Relative Wealth Index | Meta/Facebook Relative Wealth Index | GCS Bucket | Google Cloud | [`rwi.py`](backend/rwi.py) |
| 15 | Air Quality | WHO Air Quality Global Dataset | GCS Bucket | Google Cloud | [`main.py`](backend/main.py#L281) |
| 15 | Landslide Risk | NASA Global Landslide Susceptibility | GCS Bucket | Google Cloud | [`main.py`](backend/main.py#L281) |
| 15 | Liquefaction Risk | USGS Global Liquefaction Susceptibility | GCS Bucket | Google Cloud | [`main.py`](backend/main.py#L281) |
| 15 | Solar Potential | Global Solar Atlas | GCS Bucket | Google Cloud | [`solar.py`](backend/solar.py) |
| 16 | Forest Cover | Hansen Global Forest Change (GEE) | GEE API | Google Cloud + GEE | [`gee_fun.py`](backend/gee_fun.py) |
| 16 | Green Space | Sentinel-2 NDVI (GEE) | GEE API | Google Cloud + GEE | [`gee_fun.py`](backend/gee_fun.py) |
| 16 | Land Surface Temp | MODIS LST (GEE) | GEE API | Google Cloud + GEE | [`gee_fun.py`](backend/gee_fun.py) |
| 16 | Moisture Index | Sentinel-2 NDMI (GEE) | GEE API | Google Cloud + GEE | [`gee_fun.py`](backend/gee_fun.py) |
| 16 | Nightlight | VIIRS Nighttime Lights (GEE) | GEE API | Google Cloud + GEE | [`gee_fun.py`](backend/gee_fun.py) |
| 17 | Climate Classification | Köppen-Geiger Climate Classification | GCS Bucket | Google Cloud | [`basic_info.py`](backend/basic_info.py) |
| 18 | Economic Data | Oxford Economics City Database | GCS Bucket | Google Cloud | [`oe_plot.py`](backend/oe_plot.py) |
| 18 | Population Growth | CityPopulation.de (Web Scraping) | Public Web | None | [`oe_plot.py`](backend/oe_plot.py#L182) |
| 19 | Earthquake Events | NOAA NGDC Earthquake Database | Public API | None | [`earthquake_event.py`](backend/earthquake_event.py) |
| 20 | Flood Events | EM-DAT Flood Event Database | GCS Bucket | Google Cloud | [`flood_event.py`](backend/flood_event.py) |
| 21 | Population Density | JRC GHSL Population Grid (R2023A) | Public Download | None | [`ghs_population.py`](backend/ghs_population.py) |
| - | Building Footprints | Microsoft Global ML Building Footprints | Public Download | None | [`buildings.py`](backend/buildings.py) |

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

### Required Authentication

#### 1. Google Cloud (Required for all operations)
- **Setup**:
  ```bash
  gcloud auth login
  gcloud auth application-default login
  gcloud config set project <your-project-id>
  ```
- **Used for**:
  - Google Cloud Storage (inputs/outputs)
  - Google Earth Engine API
- **Default Project**: `city-scan-gee-test`
- **Default Region**: `us-central1`
- **Location**: Uses system default Google Cloud credentials

#### 2. Fathom Flood Data (Required if `menu.yml` flood options enabled)
- **Type**: AWS S3 credentials
- **File**: `backend/fathom_aws_credentials.yml` (gitignored - must create manually)
- **Format**:
  ```yaml
  aws_access_key_id: YOUR_ACCESS_KEY
  aws_secret_access_key: YOUR_SECRET_KEY
  ```
- **Used in**: `main.py:251`, `fathom.py:8`
- **Bucket**: World Bank Group AWS bucket (from `global_inputs.yml`)
- **Data**: Fathom 3.0 flood maps (coastal, fluvial, pluvial)

#### 3. Google Earth Engine (Required if `menu.yml` GEE options enabled)
- **Type**: Service account authentication
- **Setup**: `ee.Initialize()` in `gee_fun.py:4`
- **Used for**: Forest cover, green space, LST, NDMI, nightlight data
- **Note**: Runs automatically if GCloud credentials are set up

### No Authentication Required

The following data sources are **publicly accessible** and require no credentials:

#### Public APIs (No login needed)
- **WorldPop**:
  - Demographics API: `https://www.worldpop.org/rest/data/age_structures/ascic_2020?iso3={country_iso3}`
  - Population API: `https://hub.worldpop.org/rest/data/pop/cic2020_100m?iso3={country_iso3}`
  - Used in: `demographics.py:10`, `main.py:222`

- **OpenStreetMap** (via OSMnx):
  - Road networks and accessibility
  - Used in: `road_network.py`, `accessibility.py`
  - API: `http://api.openstreetmap.org/api/0.6/map?bbox=...`

- **NOAA Earthquake Archive**:
  - URL: `http://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/earthquakes`
  - Used in: `earthquake_event.py:6`

#### Public Direct Downloads (No login needed)
- **JRC Global Human Settlement Layer (GHSL)**:
  - Base URL: `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A`
  - Tile index: `https://ghsl.jrc.ec.europa.eu/download/GHSL_data_54009_shapefile.zip`
  - Used in: `ghs_population.py:50-51`

- **DLR World Settlement Footprint (WSF)**:
  - URL: `https://download.geoservice.dlr.de/WSF_EVO/files/`
  - Used in: `wsf.py`

- **Microsoft Global ML Building Footprints**:
  - URL: `https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv`
  - Used in: `buildings.py:81`

- **University of Bristol Global DEM**:
  - URL: `https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/`
  - Used in: `elevation.py:23`

- **CityPopulation.de** (web scraping):
  - URL: `https://www.citypopulation.de/en/{country}/cities/`
  - Used in: `oe_plot.py:182`
  - No authentication, but rate limits may apply

### Optional Authentication

#### Mapbox (Optional - for traffic times in road network)
- **Type**: Mapbox API token
- **Used in**: `GOSTnets/core.py:1088` (optional feature)
- **Format**: Token starts with "pk:"
- **Note**: Only needed if using `assign_traffic_times()` function
- **Currently**: Not used in main pipeline

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
