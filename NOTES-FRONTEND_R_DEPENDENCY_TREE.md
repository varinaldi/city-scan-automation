# Frontend R File Dependency Tree

```
frontend/R/
│
├─── MASTER SCRIPTS (Run directly via Rscript or run.sh)
│    │
│    ├── maps-static.R ⭐ PRIMARY MAP GENERATOR
│    │   ├── sources: setup.R
│    │   ├── sources: pre-mapping.R
│    │   ├── sources: map-schools-health-proximity.R
│    │   ├── sources: map-elevation.R
│    │   ├── sources: map-deforestation.R
│    │   ├── sources: map-flooding.R
│    │   └── sources: map-historical-burnt-area.R
│    │   └── outputs: 03-render-output/maps/*.png
│    │
│    ├── maps-web.R ⭐ INTERACTIVE WEB MAPS
│    │   ├── sources: setup.R
│    │   └── sources: pre-mapping.R
│    │   └── outputs: Interactive leaflet maps for HTML
│    │
│    ├── plots.R ⭐ CHART/PLOT GENERATOR
│    │   ├── sources: setup.R
│    │   ├── sources: urban-extent.R
│    │   ├── sources: flooding.R
│    │   ├── sources: landcover.R
│    │   ├── sources: elevation.R
│    │   ├── sources: slope.R
│    │   ├── sources: solar-pv.R
│    │   ├── sources: fwi.R
│    │   ├── sources: age-sex-distribution.R
│    │   ├── sources: flood-archive.R
│    │   └── sources: earthquakes.R
│    │   └── outputs: 03-render-output/charts/*.png
│    │
│    └── pdf-prep.R ⭐ PDF POST-PROCESSOR
│        └── sources: fns.R
│        └── outputs: Processes HTML for PDF generation
│
├─── DEPENDENCY SCRIPTS (Sourced by masters)
│    │
│    ├── setup.R 🔧 CORE SETUP (sourced by ALL masters)
│    │   ├── sources: fns.R
│    │   ├── loads: ALL libraries (ggplot2, sf, terra, tidyverse, etc.)
│    │   ├── sets: Directory paths (spatial_dir, tabular_dir, etc.)
│    │   ├── reads: layers.yml (map parameters)
│    │   ├── reads: city_inputs.yml (city config)
│    │   └── reads: AOI and wards shapefiles
│    │
│    ├── fns.R 🔧 CORE FUNCTIONS
│    │   ├── plot_static_layer() - Main map plotting function
│    │   ├── plot_web_layer() - Interactive map function
│    │   ├── theme_custom() - Map theme
│    │   ├── fill_scale(), color_scale() - Color mapping
│    │   ├── fuzzy_read() - Smart file reader
│    │   └── 50+ utility functions
│    │
│    └── pre-mapping.R 🔧 PRE-PROCESSING
│        ├── Processes rasters before mapping
│        ├── Vectorizes coarse rasters
│        └── Prepares spatial data
│
├─── MAP-SPECIFIC SCRIPTS (Sourced by maps-static.R)
│    │
│    ├── map-schools-health-proximity.R
│    ├── map-elevation.R
│    ├── map-deforestation.R
│    ├── map-flooding.R
│    ├── map-historical-burnt-area.R
│    ├── map-intersections.R
│    └── map-ghs-expansion.R (newly refactored)
│
└─── PLOT-SPECIFIC SCRIPTS (Sourced by plots.R)
     │
     ├── urban-extent.R - WSF built-up area line chart
     ├── flooding.R - Flood exposure bar charts
     ├── landcover.R - Land cover pie charts
     ├── elevation.R - Elevation distribution charts
     ├── slope.R - Slope distribution charts
     ├── solar-pv.R - Solar potential charts
     ├── fwi.R - Fire weather index charts
     ├── age-sex-distribution.R - Population pyramids
     ├── flood-archive.R - Historical flood timeline
     └── earthquakes.R - Earthquake timeline
```

<!-- ## Execution Flow

### Option 1: Maps Only (run.sh line 248-254)
```
Rscript R/maps-static.R
  └→ setup.R
      └→ fns.R
  └→ pre-mapping.R
  └→ map-*.R files
  → Outputs: 03-render-output/maps/*.png
```

### Option 2: Charts Only (run.sh line 257-263 - currently placeholder)
```
Rscript R/plots.R
  └→ setup.R
      └→ fns.R
  └→ urban-extent.R, flooding.R, etc.
  → Outputs: 03-render-output/charts/*.png
```

### Option 3: Web Maps (for HTML output)
```
Rscript R/maps-web.R
  └→ setup.R
  └→ pre-mapping.R
  → Outputs: Interactive leaflet maps in HTML
```

## Key Files by Priority

### Don't Touch (Core Dependencies)
1. ✋ `setup.R` - Everything depends on this
2. ✋ `fns.R` - Core functions, very stable
3. ✋ `pre-mapping.R` - Data preprocessing

### Focus On (Integration Points)
1. 🎯 `plots.R` - This should be called by run.sh but isn't
2. 🎯 Map-specific files like `map-flooding.R` - Add missing visualizations
3. 🎯 Plot-specific files like `flooding.R` - Generate missing charts

### Maybe Modify (If Needed)
4. ⚠️ `maps-static.R` - Only if you need to add new map types
5. ⚠️ `maps-web.R` - Only for interactive HTML maps -->
