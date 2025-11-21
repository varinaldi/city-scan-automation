# STAC Catalogs & Cloud-Optimized Data Sources

Notes on alternative data sources to Google Earth Engine for city scan automation.

## Overview

STAC (SpatioTemporal Asset Catalog) provides standardized metadata for geospatial data, enabling easier discovery and access to satellite imagery across different cloud platforms.

## Major Public STAC Catalogs

### 1. AWS Earth Search (Element 84)

- **API Endpoint:** `https://earth-search.aws.element84.com/v0`
- **Datasets:** Sentinel-2 COGs, Landsat Collection 2, Sentinel-1, Copernicus DEM, NAIP
- **Cost:** Free access (requester pays for egress)
- **Documentation:** https://element84.com/earth-search/

### 2. Microsoft Planetary Computer

- **API Endpoint:** `https://planetarycomputer.microsoft.com/api/stac/v1`
- **Datasets:** 100+ datasets including Sentinel-2, Landsat 8, ESA WorldCover
- **Cost:** First 1TB compute free per month
- **Documentation:** https://planetarycomputer.microsoft.com/docs/
- **Python Access:** `pystac-client`, `planetary-computer` library

### 3. Copernicus Data Space Ecosystem (NEW 2025)

- **API Endpoint:** `https://catalogue.dataspace.copernicus.eu/stac/`
- **Datasets:** Sentinel-1, Sentinel-2, Sentinel-3
- **Cost:** Free (European)
- **Documentation:** https://dataspace.copernicus.eu/

### 4. USGS Landsat STAC

- **API Endpoint:** `https://landsatlook.usgs.gov/stac-server`
- **Browser:** `https://landsatlook.usgs.gov/stac-browser`
- **Datasets:** Complete Landsat Collection 2 archive
- **Cost:** Free

## Dataset Availability by Source

| Dataset | GEE | Planetary Computer | AWS Earth Search | Other STAC |
|---------|-----|-------------------|------------------|------------|
| **Sentinel-2** (NDVI/NDMI) | ✅ | ✅ | ✅ | ✅ Copernicus |
| **Landsat 8** (LST) | ✅ | ✅ | ✅ | ✅ USGS |
| **ESA WorldCover** | ✅ | ✅ | ❌ | ❌ |
| **Hansen Forest** | ✅ | ❌ | ❌ | ❌ |
| **VIIRS Nightlights** | ✅ | ❌ | ⚠️ (outdated) | ❌ |

## Specific Dataset Sources

### Sentinel-2 & Landsat 8
**Recommendation:** Use Planetary Computer or AWS Earth Search
- Both provide cloud-optimized GeoTIFFs
- STAC API for programmatic access
- Free compute (with limits on Planetary Computer)

### ESA WorldCover (Land Cover)
**Recommendation:** Use Planetary Computer
- Recently added to catalog
- 10m resolution global land cover
- Alternative: Direct download from ESA

### Hansen Global Forest Change
**Sources:**
1. **Google Earth Engine** (easiest)
   - Asset: `UMD/hansen/global_forest_change_2024_v1_12`

2. **Google Cloud Storage** (free direct download)
   - URL: `https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/`
   - Download 10x10 degree tiles manually
   - No STAC interface

3. **Global Forest Watch Portal**
   - URL: `https://data.globalforestwatch.org/`
   - Web interface for downloads

**⚠️ Not available on AWS or Planetary Computer**

### VIIRS Nighttime Lights

**Option 1: NASA Black Marble (RECOMMENDED for latest data)**
- **Source:** NASA LAADS DAAC
- **URL:** `https://ladsweb.modaps.eosdis.nasa.gov`
- **Products:**
  - VNP46A1 (daily)
  - VNP46A2 (monthly)
  - VNP46A4 (yearly)
- **Coverage:** 2012 to present
- **Requirements:** Free NASA Earthdata account
- **Format:** HDF5

**Option 2: Earth Observation Group (EOG)**
- **URL:** `https://eogdata.mines.edu/products/vnl/`
- **Coverage:** Monthly composites, near real-time
- **Format:** GeoTIFF
- **Cost:** Free, no registration

**Option 3: World Bank Light Every Night (AWS)**
- **URL:** `https://registry.opendata.aws/wb-light-every-night/`
- **Coverage:** 2012-2020 only (OUTDATED)
- **Format:** Cloud-Optimized GeoTIFF with STAC
- **Cost:** Free on AWS

**Option 4: Google Earth Engine**
- **Dataset:** `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`
- **Coverage:** April 2012 - July 2024
- **Easiest programmatic access**

## Recommended Strategy for City Scan Automation

### Current Setup (All GEE)
- Sentinel-2 → NDVI, NDMI
- Landsat 8 → LST
- ESA WorldCover → Land cover
- Hansen → Forest cover/deforestation
- VIIRS → Nighttime lights

### Alternative 1: Planetary Computer + GEE Hybrid
```
Planetary Computer:
  - Sentinel-2 (NDVI, NDMI)
  - Landsat 8 (LST)
  - ESA WorldCover (land cover)

Google Earth Engine:
  - Hansen (forest cover)
  - VIIRS (nighttime lights)
```

### Alternative 2: Full Manual Download
```
Planetary Computer STAC API:
  - Sentinel-2, Landsat 8, WorldCover

Direct Downloads:
  - Hansen from Google Cloud Storage
  - VIIRS from NASA LAADS DAAC or EOG
```

## Python Access Examples

### Planetary Computer
```python
from pystac_client import Client
import planetary_computer as pc

catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

# Search for Sentinel-2 data
search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=[-74.5, 40.5, -73.5, 41.5],
    datetime="2023-06-01/2023-09-01",
    query={"eo:cloud_cover": {"lt": 10}}
)

items = search.item_collection()
signed_items = [pc.sign(item) for item in items]
```

### AWS Earth Search
```python
from pystac_client import Client

catalog = Client.open("https://earth-search.aws.element84.com/v0")

search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=[-74.5, 40.5, -73.5, 41.5],
    datetime="2023-06-01/2023-09-01"
)

items = search.item_collection()
```

## Key Considerations

### Advantages of STAC/Cloud-Optimized
- No authentication required (except NASA Earthdata)
- Direct access to COGs (Cloud-Optimized GeoTIFFs)
- Standardized metadata across platforms
- Can process locally or in cloud compute
- No GEE quota limits

### Disadvantages
- Hansen forest data not available via STAC
- VIIRS requires NASA account or older data
- More manual processing required
- Egress costs on AWS (if downloading large amounts)
- Need to handle projection/processing locally

### When to Use GEE
- Need Hansen forest data (easiest access)
- Want latest VIIRS nighttime lights (up to July 2024)
- Prefer server-side processing
- Working with large areas (avoid download costs)
- Already have GEE authentication set up

### When to Use STAC Catalogs
- Want to avoid GEE authentication issues
- Processing locally or in other cloud environments
- Need specific control over data versions
- Building pipeline independent of GEE
- Primarily using Sentinel-2/Landsat data

## Additional Resources

- **STAC Index:** https://stacindex.org/catalogs
- **STAC Specification:** https://stacspec.org/
- **Planetary Computer Examples:** https://planetarycomputer.microsoft.com/docs/quickstarts/reading-stac/
- **NASA Earthdata Search:** https://search.earthdata.nasa.gov/

## Status of Our GEE Functions

All `backend-local/gee_local.py` functions currently use Google Earth Engine:
- `gee_forest()` - Hansen (UMD/hansen/global_forest_change_2023_v1_11)
- `gee_landcover()` - ESA WorldCover (ESA/WorldCover/v200)
- `gee_ndvi()` - Sentinel-2 (COPERNICUS/S2_HARMONIZED)
- `gee_ndmi()` - Sentinel-2 (COPERNICUS/S2_HARMONIZED)
- `gee_lst_summer/winter()` - Landsat 8 (LANDSAT/LC08/C02/T1_L2)
- `gee_nightlight()` - VIIRS (NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG)

**Conclusion:** For now, staying with GEE is probably easiest since we need Hansen and VIIRS anyway. STAC alternatives are good to know for future flexibility.
