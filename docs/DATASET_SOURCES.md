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

| Task Index | Topic | Dataset Name | Access Type | Authentication | STAC Available | STAC Catalog | Python File | Backend Output Files | Frontend Output Files |
|------------|-------|--------------|-------------|----------------|----------------|--------------|-------------|----------------------|----------------------|
| 0 | Accessibility | OpenStreetMap (OSM) | Public API | None | ❌ | - | [`accessibility.py`](backend/accessibility.py) | `{city}_osm_{tag}.gpkg`<br>`{city}_accessibility_{iso}_{dist}m.gpkg` | `school_zones.png`<br>`school_points.png`<br>`health_zones.png`<br>`health_points.png` |
| 1-5 | Burned Area | MODIS GlobFire MCD64A1 | GCS Bucket | Google Cloud | ❌ | - | [`burned_area.py`](backend/burned_area.py) | `{city}_globfire_centroids.gpkg`<br>`{city}_globfire_centroids_{task}.csv` | `burnt_area.png` |
| 6 | Demographics | WorldPop Age-Sex Structures (ASCIC 2020) | Public API | None | ✅ | [WorldPop STAC](https://stac.worldpop.org/) | [`demographics.py`](backend/demographics.py) | `{city}_demographics.csv` | Age-sex pyramid charts |
| 7 | Population | WorldPop Constrained Individual Countries (CIC 2020) | Public API | None | ✅ | [WorldPop STAC](https://stac.worldpop.org/) | [`main.py`](backend/main.py#L222) | `{city}_population.tif` | `population.png` |
| 8 | Urban Settlement | DLR World Settlement Footprint Evolution | Public Download | None | ✅ | [DLR Geoservice](https://geoservice.dlr.de/eoc/ogc/stac/v1) | [`wsf.py`](backend/wsf.py) | `{city}_wsf_evolution.tif`<br>`{city}_wsf_evolution_utm.tif`<br>`{city}_wsf_evolution_3857.tif`<br>`{city}_wsf_stats.csv`<br>`{city}_urban_built_up_area.png` | `wsf.png`<br>`wsf-built-up-area-plot.png` |
| 9 | Elevation & Slope | University of Bristol Global FABDEM | Public Download | None | ✅ | [Hugging Face](https://huggingface.co/datasets/links-ads/fabdem-v12) | [`elevation.py`](backend/elevation.py) | `{city}_elevation.tif`<br>`{city}_slope.tif`<br>`{city}_slope.csv` | `elevation.png`<br>`slope.png`<br>`wsf-elevation-*.png`<br>`wsf-slope-*.png` |
| 10 | Flood Risk | Fathom Global Flood Maps v3.0 | AWS S3 (WBG) | AWS Credentials Required | ❌ | - | [`fathom.py`](backend/fathom.py) | `{city}_{type}_{year}.tif`<br>`{city}_{type}_{year}_utm.tif`<br>`{city}_flood_wsf.csv`<br>`{city}_flood_pop.csv`<br>`{city}_flood_osm.csv`<br>`{city}_flood_road.csv` | `fluvial.png`<br>`pluvial.png`<br>`coastal.png`<br>`combined_flooding.png`<br>`wsf-{type}-plot.png` |
| 11 | Fire Weather Index | CRU Fire Weather Index | GCS Bucket | Google Cloud | ❌ | - | [`fwi.py`](backend/fwi.py) | `{city}_fwi.tif`<br>`{city}_fwi.csv` | Fire weather charts |
| 12 | Land Cover Burnability | ESA CCI Land Cover + Custom Burnability Index | GCS Bucket | Google Cloud | ✅ | [OpenLandMap](https://stac.openlandmap.org/) | [`landcover_burnability.py`](backend/landcover_burnability.py) | `{city}_lc_burn.tif`<br>`{city}_lc.csv` | `burnable.png`<br>`land_cover.png`<br>`wsf-landcover-*.png` |
| 13 | Road Network | OpenStreetMap (OSM) | Public API | None | ❌ | - | [`road_network.py`](backend/road_network.py) | `{city}_edges.gpkg`<br>`{city}_nodes.gpkg` | `roads.png`<br>`intersections.png` |
| 14 | Relative Wealth Index | Meta/Facebook Relative Wealth Index | GCS Bucket | Google Cloud | ❌ | - | [`rwi.py`](backend/rwi.py) | `{city}_rwi.gpkg` | `rwi.png` |
| 15 | Air Quality | WHO Air Quality Global Dataset | GCS Bucket | Google Cloud | ❌ | - | [`main.py`](backend/main.py#L281) | `{city}_air_quality.tif` | `air_quality.png` |
| 15 | Landslide Risk | NASA Global Landslide Susceptibility | GCS Bucket | Google Cloud | ❌ | - | [`main.py`](backend/main.py#L281) | `{city}_landslide.tif` | `landslides.png` |
| 15 | Liquefaction Risk | USGS Global Liquefaction Susceptibility | GCS Bucket | Google Cloud | ❌ | - | [`main.py`](backend/main.py#L281) | `{city}_liquefaction.tif` | `liquefaction.png` |
| 15 | Solar Potential | Global Solar Atlas | GCS Bucket | Google Cloud | ❌ | - | [`solar.py`](backend/solar.py) | `{city}_solar.tif` | `solar.png` |
| 16 | Forest Cover | Hansen Global Forest Change (GEE) | GEE API | Google Cloud + GEE | ❌ | - | [`gee_fun.py`](backend/gee_fun.py) | `{city}_forest_cover.tif`<br>`{city}_deforest.tif` | `forest.png`<br>`deforest.png`<br>`forest_deforest.png` |
| 16 | Green Space | Sentinel-2 NDVI (GEE) | GEE API | Google Cloud + GEE | ✅ | [Planetary Computer](https://planetarycomputer.microsoft.com/api/stac/v1), [AWS Earth Search](https://earth-search.aws.element84.com/v0) | [`gee_fun.py`](backend/gee_fun.py) | `{city}_ndvi_season.tif` | `vegetation.png` |
| 16 | Land Surface Temp | MODIS LST (GEE) | GEE API | Google Cloud + GEE | ✅ | [Planetary Computer](https://planetarycomputer.microsoft.com/api/stac/v1) | [`gee_fun.py`](backend/gee_fun.py) | `{city}_summer_lst.tif` | `summer_lst.png` |
| 16 | Moisture Index | Sentinel-2 NDMI (GEE) | GEE API | Google Cloud + GEE | ✅ | [Planetary Computer](https://planetarycomputer.microsoft.com/api/stac/v1), [AWS Earth Search](https://earth-search.aws.element84.com/v0) | [`gee_fun.py`](backend/gee_fun.py) | `{city}_ndmi_season.tif` | `drought.png` |
| 16 | Nightlight | VIIRS Nighttime Lights (GEE) | GEE API | Google Cloud + GEE | ⚠️ | [World Bank AWS](https://registry.opendata.aws/wb-light-every-night/) (outdated 2012-2020) | [`gee_fun.py`](backend/gee_fun.py) | `{city}_avg_rad_sum.tif`<br>`{city}_linfit.tif` | `economic_activity.png`<br>`economic_change.png` |
| 17 | Climate Classification | Köppen-Geiger Climate Classification | GCS Bucket | Google Cloud | ❌ | - | [`basic_info.py`](backend/basic_info.py) | `{city}_climate.txt` | Climate text summary |
| 18 | Economic Data | Oxford Economics City Database | GCS Bucket | Google Cloud | ❌ | - | [`oe_plot.py`](backend/oe_plot.py) | OE benchmark charts | Economic comparison charts |
| 18 | Population Growth | CityPopulation.de (Web Scraping) | Public Web | None | ❌ | - | [`oe_plot.py`](backend/oe_plot.py#L182) | `{city}_pop_growth.csv` | Population growth charts |
| 19 | Earthquake Events | NOAA NGDC Earthquake Database | Public API | None | ❌ | - | [`earthquake_event.py`](backend/earthquake_event.py) | `{city}_earthquake.csv` | Earthquake timeline charts |
| 20 | Flood Events | EM-DAT Flood Event Database | GCS Bucket | Google Cloud | ❌ | - | [`flood_event.py`](backend/flood_event.py) | `{city}_flood_archive.csv` | Flood event timeline charts |
| 21 | Population Density | JRC GHSL Population Grid (R2023A) | Public Download | None | ✅ | [OpenLandMap](https://stac.openlandmap.org/) | [`ghs_population.py`](backend/ghs_population.py) | `{city}_ghs_pop_{year}.tif` | `ghs_pop_{year}.png` |
| - | Building Footprints | Microsoft Global ML Building Footprints | Public Download | None | ❌ | - | [`buildings.py`](backend/buildings.py) | `{city}_buildings.gpkg` | Building footprint overlays |

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

## STAC Availability Analysis

### Summary Statistics

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| ✅ Available | 8 | ~35% | Full STAC catalog support |
| ⚠️ Limited | 1 | ~4% | Outdated or partial STAC access |
| ❌ Not Available | 15 | ~65% | No STAC catalog |

### Datasets with STAC Support (✅)

These datasets can be accessed through modern STAC APIs with cloud-optimized formats:

1. **WorldPop Demographics & Population** (Tasks 6, 7)
   - STAC API: https://stac.worldpop.org/
   - Coverage: 2015-2030 (Global 2)
   - Desktop app available for browsing
   - Status: Production-ready

2. **DLR World Settlement Footprint** (Task 8)
   - STAC Endpoint: https://geoservice.dlr.de/eoc/ogc/stac/v1
   - Collection: WSF_2019, WSF Evolution
   - Years: 1985-2015
   - Status: Production-ready

3. **FABDEM Elevation** (Task 9)
   - STAC Catalog: https://huggingface.co/datasets/links-ads/fabdem-v12
   - Format: Cloud-optimized
   - Resolution: 30m
   - Status: Production-ready

4. **ESA CCI Land Cover** (Task 12)
   - STAC Catalog: https://stac.openlandmap.org/
   - Collection: land.cover_esacci.lc.l4
   - Years: 1992-2020 (annual)
   - Status: Production-ready

5. **Sentinel-2 (NDVI, NDMI)** (Task 16)
   - Multiple STAC catalogs:
     - Microsoft Planetary Computer: https://planetarycomputer.microsoft.com/api/stac/v1
     - AWS Earth Search: https://earth-search.aws.element84.com/v0
     - Copernicus Data Space: https://catalogue.dataspace.copernicus.eu/stac/
   - Status: Production-ready, widely used

6. **Landsat 8/MODIS (LST)** (Task 16)
   - STAC catalogs:
     - Planetary Computer (recommended)
     - AWS Earth Search
     - USGS Landsat STAC
   - Status: Production-ready

7. **JRC GHSL Population** (Task 21)
   - STAC Catalog: https://stac.openlandmap.org/
   - Collection: pop.count_ghs.jrc
   - Years: 2000-2021
   - Status: Production-ready

### Datasets with Limited STAC Support (⚠️)

8. **VIIRS Nighttime Lights** (Task 16)
   - STAC Catalog: https://registry.opendata.aws/wb-light-every-night/
   - **Issue**: Outdated (2012-2020 only)
   - **Alternative**: Use GEE for latest data (up to 2024)
   - Status: Not recommended for current use

### Datasets Without STAC Support (❌)

#### Available via Alternative Cloud Platforms

9. **Microsoft Building Footprints** (standalone)
   - **Status**: ✅ Available on Planetary Computer
   - **Format**: GeoParquet (cloud-optimized vector)
   - **Access**: https://planetarycomputer.microsoft.com/dataset/ms-buildings
   - **Coverage**: 1.2B buildings globally (as of June 2023)
   - **Note**: Not using STAC spec but available via Planetary Computer API with TileJSON support
   - **Update**: Added 32.7M buildings in 2024
   - **Recommendation**: Should move from current direct download to Planetary Computer API

10. **MODIS Burned Area (GlobFire MCD64A1)** (Tasks 1-5)
    - **Status**: ✅ Available on Planetary Computer
    - **STAC Access**: https://planetarycomputer.microsoft.com/dataset/modis-64A1-061
    - **Format**: Monthly, global gridded 500m
    - **Coverage**: November 2000 - September 2024
    - **Note**: Currently using GCS bucket, but STAC alternative exists!
    - **Recommendation**: Migrate to Planetary Computer STAC API

11. **Hansen Global Forest Change** (Task 16)
    - **Status**: ⚠️ Partial STAC support
    - **STAC Browser**: https://stac-browser.maap-project.org/collections/glad-global-forest-change-1.11
    - **Collection**: GLAD Global Forest Change (MAAP platform)
    - **Coverage**: v1.11 (2000-2023), v1.12 (2000-2024) available
    - **Cloud-Optimized**: GitHub project provides COG version: https://github.com/ramiqcom/hansen-global-forest-change
    - **Original Access**: Google Cloud Storage tiles
    - **Note**: STAC access through MAAP requires JavaScript/special access
    - **Recommendation**: Continue using GEE for now, monitor MAAP STAC development

12. **Meta/Facebook Relative Wealth Index** (Task 14)
    - **Status**: ❌ No STAC, but publicly accessible
    - **Access Options**:
      - Humanitarian Data Exchange (HDX): https://data.humdata.org/dataset/relative-wealth-index
      - Google Earth Engine: projects/sat-io/open-datasets/facebook/relative_wealth_index
      - Meta Data for Good: https://dataforgood.facebook.com/dfg/tools/relative-wealth-index
    - **Coverage**: 135 low/middle-income countries at 2.4km resolution
    - **License**: CC0 (Public Domain)
    - **Note**: Available in GEE, could be accessed without GCS bucket
    - **Recommendation**: Consider switching to GEE access instead of GCS

13. **Global Solar Atlas** (Task 15)
    - **Status**: ❌ No STAC catalog
    - **Access Options**:
      - Direct download: https://globalsolaratlas.info/
      - Google Earth Engine: Available as asset
      - ArcGIS: Available as service
      - World Bank Data Catalog: https://datacatalog.worldbank.org/
    - **Format**: GeoTIFF (traditional, not cloud-optimized)
    - **Resolution**: 30 arc-sec (~1km), higher detail at 9 arc-sec (~250m)
    - **Version**: v2.12 (April 2025)
    - **Note**: No cloud-native STAC implementation exists yet
    - **Recommendation**: Continue current GCS approach or use GEE

#### Datasets Requiring Proprietary/Restricted Access

14. **Fathom Global Flood Maps** (Task 10)
    - **Status**: ❌ No public STAC
    - **Current Access**: AWS S3 (WBG bucket) with credentials required
    - **Version**: v3.0 (2024) - includes coastal, fluvial, pluvial
    - **Resolution**: 30m globally (using FABDEM)
    - **Coverage**: 56°S to 60°N
    - **Note**: Commercial/institutional license required
    - **Alternative**: No free global equivalent at comparable resolution
    - **Recommendation**: Continue current AWS S3 access

15. **Oxford Economics City Database** (Task 18)
    - **Status**: ❌ Proprietary data, no STAC
    - **Access**: Commercial license required
    - **Note**: No public alternative exists
    - **Recommendation**: Continue current GCS approach

#### Datasets Using Specialized APIs

16. **OpenStreetMap** (Tasks 0, 13)
    - **Status**: ❌ No STAC catalog (by design)
    - **Current Access**: OSMnx Python library
    - **Why No STAC**: Vector data doesn't fit STAC's spatiotemporal model well
    - **Standard**: OGC API - Features is recommended for vector data
    - **Note**: OSM has its own mature ecosystem (Overpass API, OSMnx)
    - **Recommendation**: Continue using OSMnx, no migration needed

17. **NOAA Earthquake Database** (Task 19)
    - **Status**: ❌ No STAC catalog
    - **Current Access**: Public REST API
    - **API**: http://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/earthquakes
    - **Note**: Event-based API, not raster/imagery (STAC not applicable)
    - **Recommendation**: Continue using REST API

18. **CityPopulation.de** (Task 18)
    - **Status**: ❌ No API/STAC
    - **Current Access**: Web scraping
    - **Note**: Unofficial data source with rate limits
    - **Recommendation**: Continue current approach

#### Datasets in GCS Buckets Without STAC Alternatives

19. **CRU Fire Weather Index** (Task 11)
    - **Status**: ❌ No known STAC catalog
    - **Current Access**: GCS bucket
    - **Note**: Niche climate dataset, limited distribution
    - **Recommendation**: Continue GCS approach

20. **WHO Air Quality Global Dataset** (Task 15)
    - **Status**: ❌ No STAC catalog
    - **Current Access**: GCS bucket
    - **Note**: WHO data typically distributed via direct download
    - **Recommendation**: Continue GCS approach

21. **NASA Global Landslide Susceptibility** (Task 15)
    - **Status**: ❌ No STAC catalog found
    - **Current Access**: GCS bucket
    - **Model**: LHASA 2.0 (1km resolution)
    - **Alternative Access**: NASA MapServer: https://maps.nccs.nasa.gov/mapping/rest/services/landslide_viewer/Landslide_Susceptibility_Update_2023/MapServer
    - **Data Access**: Available via NASA's mapping services
    - **Note**: Could potentially request from NASA's Earth Data portal
    - **Recommendation**: Continue GCS approach, monitor NASA Earth Data portal

22. **USGS Global Liquefaction Susceptibility** (Task 15)
    - **Status**: ❌ No STAC catalog
    - **Current Access**: GCS bucket
    - **Note**: Specialized hazard dataset
    - **Recommendation**: Continue GCS approach

23. **EM-DAT Flood Event Database** (Task 20)
    - **Status**: ❌ No STAC catalog
    - **Current Access**: GCS bucket
    - **Note**: Historical event database (tabular), not spatial raster (STAC not applicable)
    - **Recommendation**: Continue GCS approach

24. **Köppen-Geiger Climate Classification** (Task 17)
    - **Status**: ❌ No STAC catalog
    - **Current Access**: GCS bucket (CSV)
    - **Note**: Simple classification lookup table
    - **Recommendation**: Continue GCS approach

## Migration Opportunities

Based on this analysis, here are the **immediate migration opportunities** from current GCS/GEE to STAC catalogs:

### High Priority (Production-Ready STAC Alternatives)

1. **MODIS Burned Area** (Tasks 1-5): GCS Bucket → Planetary Computer STAC
   - Clear improvement: Better access, no GCS costs, same data source

2. **Microsoft Building Footprints**: Direct Download → Planetary Computer API
   - Cloud-optimized GeoParquet with TileJSON support

### Medium Priority (Evaluation Needed)

3. **Sentinel-2/Landsat processing** (Task 16): GEE → Planetary Computer STAC
   - Only if reducing GEE dependency is desired
   - Requires rewriting processing logic

4. **Meta RWI** (Task 14): GCS Bucket → GEE or HDX
   - Not STAC, but more accessible than current GCS approach

### Low Priority (Keep Current Approach)

- Fathom Flood (commercial license, no alternative)
- Oxford Economics (proprietary, no alternative)
- OSM (specialized API, working well)
- Event databases (STAC not applicable)
- Niche datasets in GCS (no better alternative)

## Recommendations Summary

| Dataset | Current | Recommended | Priority | Reason |
|---------|---------|-------------|----------|---------|
| MODIS Burned Area | GCS | Planetary Computer STAC | HIGH | Direct replacement available |
| MS Buildings | Direct DL | Planetary Computer API | HIGH | Cloud-optimized, better access |
| Meta RWI | GCS | GEE or HDX | MEDIUM | More accessible alternatives exist |
| Sentinel-2/Landsat | GEE | Planetary Computer STAC | LOW | GEE works well, migration complex |
| Hansen Forest | GEE | Keep GEE | LOW | Best access still via GEE |
| VIIRS Nightlights | GEE | Keep GEE | LOW | Most up-to-date via GEE |
| All others | Current | Keep Current | LOW | No better alternative |
