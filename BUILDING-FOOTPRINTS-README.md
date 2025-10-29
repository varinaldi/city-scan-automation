# Building Footprints Visualization

Generate building footprints maps for any city using Microsoft Bing building dataset.

## Quick Start

### 1. Download Building Data

```bash
cd city-scan-automation

# Activate conda environment
conda activate cityscan

# Download buildings for a city
python download-buildings.py 2025-10-senegal-matam
```

### 2. Generate Plot

```bash
# Create visualization
Rscript plot-building-footprints.R 2025-10-senegal-matam
```

Output will be saved to: `mnt/{city}/03-render-output/maps/{city}_building_footprints.png`

---

## For All Senegal Cities

Run for all Senegal cities at once:

```bash
cd city-scan-automation
conda activate cityscan

# Download building data for all cities
for city in matam diourbel tambacounda; do
  echo "================================"
  echo "Downloading buildings for $city..."
  echo "================================"
  python download-buildings.py 2025-10-senegal-$city
done

# Generate plots for all cities
for city in matam diourbel tambacounda; do
  echo "================================"
  echo "Creating plot for $city..."
  echo "================================"
  Rscript plot-building-footprints.R 2025-10-senegal-$city
done
```

---

## Scripts

### `download-buildings.py`

Downloads building footprints from Microsoft Bing dataset.

**Usage:**
```bash
python download-buildings.py <city-directory-name>
```

**Example:**
```bash
python download-buildings.py 2025-10-senegal-matam
```

**What it does:**
1. Reads AOI from `mnt/{city}/01-user-input/AOI/`
2. Calculates required quadkeys
3. Downloads building data from Microsoft Bing
4. Saves to `building-tiles/{Country}-{quadkey}.fgb`

**Output:**
- Building tiles in FlatGeobuf format (`.fgb`)
- Typically 10-100 MB per quadkey

---

### `plot-building-footprints.R`

Creates visualization of building footprints with road network.

**Usage:**
```bash
Rscript plot-building-footprints.R <city-directory-name>
```

**Example:**
```bash
Rscript plot-building-footprints.R 2025-10-senegal-matam
```

**What it does:**
1. Reads AOI from `mnt/{city}/01-user-input/AOI/`
2. Loads building data from `building-tiles/`
3. Loads roads from `mnt/{city}/02-process-output/spatial/edges-edit.gpkg`
4. Creates visualization:
   - Orange buildings (#FF9C28)
   - White roads
   - Black background
5. Saves to `mnt/{city}/03-render-output/maps/{city}_building_footprints.png`

**Output:**
- PNG image (8.77" × 7.55" @ 200 DPI)
- Typically 500KB - 2MB

---

## Directory Structure

```
city-scan-automation/
├── download-buildings.py          # Download script
├── plot-building-footprints.R     # Plotting script
│
├── building-tiles/                # Downloaded building data
│   ├── Senegal-33302131.fgb
│   ├── Senegal-33302133.fgb
│   └── ...
│
└── mnt/
    └── 2025-10-senegal-{city}/
        ├── 01-user-input/
        │   └── AOI/               # Input: City boundary
        ├── 02-process-output/
        │   └── spatial/
        │       └── edges-edit.gpkg # Input: Road network
        └── 03-render-output/
            └── maps/
                └── {city}_building_footprints.png  # Output!
```

---

## Requirements

### Python (download-buildings.py)
- pandas
- geopandas
- shapely

Install via conda:
```bash
conda activate cityscan
# Packages should already be installed in cityscan environment
```

### R (plot-building-footprints.R)
- terra
- ggplot2
- dplyr
- tidyterra
- stringr

Install in R:
```r
install.packages(c("terra", "ggplot2", "dplyr", "tidyterra", "stringr"))
```

---

## Troubleshooting

### "No module named 'pandas'"
Make sure to activate the cityscan conda environment:
```bash
conda activate cityscan
```

### "AOI not found"
The city must have an AOI in `mnt/{city}/01-user-input/AOI/`. Run the frontend pipeline first:
```bash
bash scripts/frontend.sh {city-directory-name}
```

### "No building data loaded"
Download buildings first:
```bash
python download-buildings.py {city-directory-name}
```

### "Roads file not found"
The script will still work, but without roads. To get roads, run the backend pipeline first.

---

## Examples

### Dakar (Already Done)
```bash
# Already have data in building-tiles/Senegal-33302131.fgb and Senegal-33302133.fgb
Rscript plot-building-footprints.R 2025-10-senegal-dakar
```

Output: `mnt/2025-10-senegal-dakar/03-render-output/maps/dakar_building_footprints.png`

### Matam (New)
```bash
# Download first
conda activate cityscan
python download-buildings.py 2025-10-senegal-matam

# Then plot
Rscript plot-building-footprints.R 2025-10-senegal-matam
```

Output: `mnt/2025-10-senegal-matam/03-render-output/maps/matam_building_footprints.png`

### Indonesia Sofifi
```bash
conda activate cityscan
python download-buildings.py 2025-10-indonesia-sofifi
Rscript plot-building-footprints.R 2025-10-indonesia-sofifi
```

---

## Data Source

Building footprints from:
- **Microsoft Bing Building Footprints**
- https://github.com/microsoft/GlobalMLBuildingFootprints
- Licensed under Open Data Commons Open Database License (ODbL)

---

## Notes

- Building data is cached in `building-tiles/` and reused across cities in the same country
- Each quadkey typically covers ~100km² at zoom level 9
- Large cities may require multiple quadkeys
- Total download size varies: 10-200 MB per city
- The script automatically detects country from directory name format: `YYYY-MM-country-city`
