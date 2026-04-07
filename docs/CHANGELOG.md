# Changelog

---
## 2026-04-07

### Changed
#### CLI & Orchestration
- `--sync` now accepts targets: `--sync tasks`, `--sync source`, `--sync core`, `--sync scan-calculations`. No target = sync all. `-t` is shortcut for `--sync tasks`
- Removed `-o` and `-c` flags — replaced by `--sync` targets
- Centralized CLI flag parsing in `core/config/cli.py` (single source of truth)
- `sync.py` accepts `sync_targets` list instead of boolean override/copy_tasks_only
- City header in CLI shows scan_id name (e.g. "Namibia Windhoek") instead of generic "City Scan Automation"

#### Benchmark System
- Benchmark cities: merge `bm_cities_manual` + `bm_cities_oxford` (auto-detect) instead of one overriding the other
- New `benchmark_mode` in city_inputs.yml: `sibling` (only sibling scans), `oxford` (only Oxford auto-detect), `auto` (both, default)
- New `benchmark_backup` in city_inputs.yml: `citypopulation` (citypopulation.de + OSM boundary), `worldpop_ucdb` (WorldPop + UCDB), or null
- Group labels in data: city name, "Benchmark - sibling", "Benchmark - Oxford", "Benchmark - backup"
- Oxford collection filters to non-sibling benchmarks only
- Consolidated `benchmark-worldpop.R` into `benchmark-helper.R`
- Added `docs/benchmarks.md` reference doc

#### Maps
- Ward lines: darkened from grey60 to grey40, linewidth 0.35 → 0.5
- Seismic hazard map: broader extent (like burnt area), uses raster extent instead of AOI
- Seismic hazard collection: buffer AOI by 1 degree for broader context
- Built-up area hatch overlay added to landslide, liquefaction, infrastructure maps
- Infrastructure hatch: underlay mode (hatch drawn beneath points, not on top)
- `add_builtup_hatch()` moved from `map-schools-health-proximity.R` to `fns.R`
- Standard plots loop: early check for valid SpatRaster/SpatVector before `vectorize_if_coarse()` — cleaner "No data" messages instead of cryptic cellSize errors

#### Charts
- WSF chart titles: "Built-up area expansion, 1985–2025" / "Built-up area exposed to X flooding"
- Donut plots: removed legend (same as map), added `show_legend` parameter to `ggdonut()`
- Donut plots: removed titles for elevation and slope, landcover keeps legend
- Elevation and slope charts: added data tables
- Solar PV chart: moved table below chart
- Landcover chart: fixed `print("\n")` debug output, added `cat("\n\n")` break
- RWI charts: removed subtitles, confirmed values are already z-scored by Meta (mean=0, sd=1 nationally)
- Removed bold title styling from RWI and fathom charts
- All 16 task charts: standardized `##` headers
- Worldpop: removed subtitles from G1/G2 individual and benchmark charts, removed "comparison (YYYY)" text
- Worldpop: renamed `wpop_df` to `wp_ridge`
- Worldpop: new "Benchmark Cities Population (WorldPop G1 + Oxford)" combined chart
- Worldpop: density scatter skips Oxford cities when many siblings and only 1 Oxford city
- Removed empty "Benchmark Cities" heading and UCDB note from worldpop charts

#### Fathom Charts Reorganization
- Reorganized by flood type: each section has max prob chart → return period chart → WSF stats table → population table → infrastructure table
- Used helper functions (`.flood_max_plot`, `.flood_rp_plot`, `.flood_wsf_table`, `.flood_pop_table`, `.flood_infra_table`)
- Narrative text (roads/infrastructure/population in flood zone) generated from current CSV format, placed after tables
- Section headers with `####` titles
- Harmonized WSF combined chart: uses points for individual types (matches combined max prob chart style)
- Combined flood labels: "River", "Rainwater", "Combined" instead of "fu", "pu", "comb"
- Harmonized WSF chart moved inside combined section (before tables)
- No-data guard: skips chart + text when all exposure is 0

### Fixed
- Fathom multianalysis: WSF harmonized CSV was read without filtering by source, causing 3x duplicate rows. Now reads only "WSF Harmonized" source
- Fathom multianalysis: `full_join` → `inner_join` with flood_wsf — no more NA rows for years without WSF data
- Fathom charts: `tail(df, 1)` picked unsorted NA rows — now filters + sorts by year
- Coastal erosion collection: case-insensitive country name match (was missing all data for Namibia)
- SLR collection: replaced `file.exists()` (doesn't work on `/vsigs/` paths) with `tryCatch` around `rast()`
- Oxford charts: `hues` mapped to "Benchmark - Oxford" group label
- ErrorTracker: added `no_data_count` and `NO_DATA` status

### New
- LST charts task (`tasks/lst/charts/`) — OJS-based chart using `plot_summer_area` from `core/ojs/plots.js`
- Scan-calculations: floating TOC (`toc: true`, `toc-location: right`)
- `core/ojs/plots.js` updated to latest version (from Nouakchott)

---
## 2026-04-02

### New 
#### CLI & Orchestration
- `scan` CLI entry point — install with `pip install -e .` from repo root, then run `scan` instead of `python -m tasks`
- Multi-city batch runner: `scan --all --multicities` reads `inputs/multi_inputs.yml`, auto-detects AOI shapefiles per city from `inputs/AOI/{city_name}/`
- `--render` flag: run maps-static, scan-calculations, or task charts from root (e.g. `scan --render maps --scan-id ...`)
- `--sync` flag: sync project files (core/, tasks/, source/) to city folder without running tasks
- `-k` / `--keep` flag: run tasks using code already in city folder, skip syncing
- Flag behavior: `-e` use existing folder, `-o` override everything, `-t` copy tasks only, `-k` keep as-is

#### Tasks & Data
- Water risk task (`tasks/water_risk/`) — WRI Aqueduct v4 from GEE
- Groundwater task (`tasks/groundwater/`) — G3P collection, auto-detects aquifer basin
- RWI charts task (`tasks/rwi/charts/`) with dual mode: standardized (fixed SD breaks) + city-relative (equal interval histogram)
- Building footprints plot in `maps-static.R`
- Built-up area 2025 hatch overlay on accessibility and flood maps (`ggpattern`)
- Infra + flooding stats tables in fathom charts (split by flood type)
- Task report (`logs/task_report.txt`) — persistent status table with source, messages, last update
- Data source tracking on `scan.sources` (elevation, demographics, groundwater)
- Task validation — typos caught early with suggestions

#### Architecture
Cleaning up scan initialization:
- `source/tasks.yml` — task config (auth, aliases, dependencies) in YAML instead of hardcoded
- `core/config/tasks.py` — reads tasks.yml, provides registry and helpers
- `core/config/utils.py` — shared `slugify()` (was duplicated 4 times)
- `core/config/sync.py` — `sync_project_files()` with t/o/a prompt, extracted from Scan
- `core/config/inputs.py` — `prepare_inputs()` unified from Scan._copy_inputs + multicities
- `core/config/scan.py` — `scan_init()` for folder detection, slim Scan class
- `core/py/error_tracker.py` — extracted from `__main__.py`
- `core/py/run.py` — extracted `run_task()` and `run_multicities()` from `__main__.py`

### Changed
#### Fathom / Flooding
- GCS tile naming: supports both flat (`1in10-FLUVIAL-UNDEFENDED-2020_s24e017.tif`) and folder (`GLOBAL-1ARCSEC-NW_OFFSET-1in10-.../s24e017.tif`) — tries flat first, falls back to folder
- Combined flood map: per-band merge (max across flood types per RP) instead of naive mosaic
- Flood maps: read only band 1 (max_probability) — fixes tidyterra multi-band warning
- Flood labels: changed from probability (0.1-1%, 1-10%, >10%) to return periods (1-in-1,000, 1-in-100, 1-in-10 year)
- Combined flooding line added to harmonized flood + WSF chart
- Fathom charts: reads CSVs directly (run `--multianalysis` separately), no longer sources multianalysis.R

### 
#### Data Sources
- Demographics: upgraded from WorldPop Global_2000_2020 (2020 only) to R2025A (current year, 2015-2030), downloads directly from WorldPop (no GCS dependency)
- WorldPop: parallel downloads (3 workers) for both G1 and demographics
- Elevation fallback chain: GCS FABDEM → GEE FABDEM → GEE SRTM
- Benchmark assembly: sibling scan collects both WorldPop G1 and G2, ensures GCS auth
- Worldpop charts: G1 and G2 benchmark sections filter by Source (no more mixing)

#### Maps & Charts
- RWI city-relative: equal interval bins with explicit numeric values (was quantile with "Least wealthy" labels)
- WSF charts: added titles to Evolution and Tracker plots
- AOI stroke linewidth 0.6, ward linewidth 0.25
- `cat("\n\n")` added after all plot `print()` calls across 16 chart qmds — prevents text rendering beside chart

#### Pipeline
- Multicities: detects country from AOI shapefile (no `country` field needed in multi_inputs.yml)
- Multicities: finds existing city folders instead of always creating new ones
- FABDEM download failure → warning (fallback succeeds)
- Forest "no pixels" → warning
- FWI missing dates → warning (skips and continues)
- Log file overwrites each run (no stale error accumulation)
- Summary table prints after both parallel and sequential runs
- `scan-calculations/index.qmd` deleted — always generated by `generate-index.R`
- RWI added to `scan-calculations/sections.yml`

### Fixed
- ggplot2 4.0: replaced removed `ggplot2:::print.ggplot()` with `print()` across 16 chart qmds + 2 core/R files. `setup.R` auto-updates ggplot2 if < 4.0
- `here::i_am()` added to all chart qmds — fixes `here()` resolving to `charts/` instead of city root in VSCode
- R `$` partial matching: `params$breaks` matched `params$breaks_method`. Renamed to `binning_method`
- Benchmark sibling scan: `base::list.files` (GCS override broke it), `as.character()` for integer year column
- Fathom charts: missing `prob_colors`/`prob_linetypes`, missing `flood_total` variable, `pivot_longer` crash on missing RP column, line gap between Evolution/Tracker periods
- Built-up hatch overlay zoom mismatch on flood + school/health maps: `coord_3857_bounds()` + clip to AOI
- Oxford `collection.R`: guards against empty `oxford_full` tibble
- `tryCatch_named()` prints error message inline
- Auto-exit parallel TUI with `--multicities`
- Missing imports in `core/py/run.py`: `shutil`, `OUTPUTS`
- Infrastructure points: `rbind` crash when OSM returns mixed point/polygon geometries — convert to centroids before combining
- Landcover analysis: `if max < 100: *=10` heuristic broke when raster had real ESA values (10-90) — changed to `max <= 10` + snap to nearest valid class (handles resampling artifacts)
- Fathom single-tile cities: `mosaic_raster()` tried `os.rename()` on `/vsigs/` cloud paths — now reads and writes for virtual paths
- Fathom charts: `flood_road`/`flood_osm`/`flood_pop` crash when no flood data — now reads CSVs with tryCatch, shows "No data available"

---
## 2026-03-24
### New
- Demographics charts task (age-sex distribution, demographic indicators)
- Scan.py prompts before overwriting city source files (c/o/a)

### Fixed
- Oxford Economics case-insensitive city lookup
- Elevation column name mismatch (Elevation_Band → Bin)
- GEE elevation fallback now masks to AOI, not just bbox
- Elevation static map crops to AOI boundary
- Fathom flood analysis uses nested return period bands instead of max probability bins

### Changed
- Setup docs: clone single branch only
- Demographics added to scan-calculations sections
