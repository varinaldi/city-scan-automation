# Repository Structure

```
city-scan-automation/
├── tasks/
├── core/
├── source/
├── inputs/
├── mnt/
├── scan-calculations-compiler/
├── docs/
└── logs/
```

---

## tasks/

```
tasks/
├── elevation/
│   ├── __init__.py
│   ├── collection.py
│   ├── analysis.py
│   └── charts/
│       └── index.qmd
├── fathom/
│   ├── __init__.py
│   ├── collection.py
│   ├── analysis.py
│   ├── multianalysis.R
│   └── charts/
│       └── index.qmd
├── worldpop/
├── wsf/
└── ...
```

- Each scan topic is a self-contained module
- `__init__.py` defines entry points: `collect()`, `analyze()`, `visualize()`
- `collection.py` downloads and clips data to AOI
- `analysis.py` computes statistics and generates CSVs
- `charts/index.qmd` renders Quarto charts for the scan-calculations report
- Some tasks have R scripts (e.g. `multianalysis.R`, `analysis.R`) for R-based processing
- Tasks are auto-discovered from folders with `__init__.py`
- GEE-based tasks (forest, landcover, LST, NDVI, nightlight) live under `tasks/gee/` with shared utilities in `tasks/gee/fns.py`

---

## core/

### core/config/

```
core/config/
├── scan.py
├── auth.py
├── paths.py
└── gdal_auth.py
```

- `scan.py` — Scan class: loads AOI, city config, creates city output folders in `mnt/`
- `auth.py` — initializes GEE and GCS authentication
- `paths.py` — auto-detects input/output directories based on project structure
- `gdal_auth.py` — configures GDAL for `/vsigs/` access to private GCS buckets

### core/py/

```
core/py/
├── log_module.py
├── gcs_module.py
├── aoi_module.py
└── multitask.py
```

- `log_module.py` — logging setup (console + rotating file output)
- `gcs_module.py` — GCS upload/download, file tracking for `--upload` flag
- `aoi_module.py` — detects country name and ISO3 code from AOI intersection
- `multitask.py` — parallel task runner with TUI for `--parallel` flag

### core/R/

```
core/R/
├── setup.R
├── fns.R
├── pre-mapping.R
├── maps-static.R
├── map-flooding.R
├── map-elevation.R
├── benchmark-helper.R
├── benchmark-worldpop.R
├── pop-backup.R
├── global-data-paths.R
├── plot-building-footprints.R
└── ...
```

- `setup.R` — R session setup: loads packages, reads AOI, sets directory paths
- `fns.R` — `plot_static_layer()`, `prepare_parameters()`, `save_plot()`, `fuzzy_read()` and other shared helpers
- `pre-mapping.R` — data preprocessing before mapping (combine zones, edit WSF tracker, adjust deforestation years)
- `maps-static.R` — orchestrates static map generation: standard layers loop + custom map scripts
- `map-*.R` — custom map scripts for layers that need special handling (flood overlays, elevation breakpoints, etc.)
- `benchmark-helper.R` — benchmark city selection and size-matching from Oxford
- `benchmark-worldpop.R` — WorldPop G2 population for benchmark cities via UCDB boundaries
- `pop-backup.R` — population fallback functions (UN data, citypopulation.de, GHS-POP)

### core/ojs/

```
core/ojs/
└── plots.js
```

- Observable JS interactive charts (D3-based) used in the web report

---

## source/

```
source/
├── layers.yml
├── generic-text.yml
├── custom.scss
└── pagedtable-fix.scss
```

- Canonical config files, copied to each city folder on first run
- `layers.yml` — map layer styling (palettes, breaks, labels, fuzzy_string per layer)
- `generic-text.yml` — report text templates per section
- `custom.scss` — report CSS styling
- `pagedtable-fix.scss` — Bootstrap table styling overrides

---

## inputs/

```
inputs/
├── city_inputs.yml
├── menu.yml
└── AOI/
```

- User-facing configuration for new scans
- `city_inputs.yml` — city name, AOI shapefile name, country, flood parameters
- `menu.yml` — toggle which topics to enable or disable
- `AOI/` — boundary shapefile(s) for the city

---

## mnt/

```
mnt/
└── 2026-03-tunisia-tunis/
    ├── 01-user-input/
    ├── 02-process-output/
    │   ├── spatial/
    │   └── tabular/
    ├── 03-render-output/
    │   ├── maps/
    │   └── plots/
    ├── tasks/
    ├── core/
    └── source/
```

- City output folders, auto-created per scan by the `Scan` class
- Each city gets its own copy of `tasks/`, `core/`, `source/`
- `01-user-input/` — copied from `inputs/`
- `02-process-output/spatial/` — rasters and vector data (.tif, .gpkg, .fgb)
- `02-process-output/tabular/` — CSVs and statistics
- `03-render-output/maps/` — static map PNGs
- `03-render-output/plots/` — chart PNGs

---

## scan-calculations-compiler/

```
scan-calculations-compiler/
├── _quarto.yml
├── generate-index.R
└── order.yml
```

- Assembles per-task `charts/index.qmd` files into a single scan-calculations HTML report
- `order.yml` defines the section order
- `generate-index.R` reads the order and combines the task qmds

---

## docs/

```
docs/
├── setup.md
├── googlecloud.md
├── structure.md
├── finding-aoi.md
├── frontend.md
└── backend.md
```

- `setup.md` — installation and environment setup
- `googlecloud.md` — GEE and GCS authentication
- `structure.md` — this file
- `finding-aoi.md` — how to obtain AOI boundaries

---

## logs/

```
logs/
└── app.log
```

- Auto-created on first task run
- Rotating log file (5MB, 3 backups)
