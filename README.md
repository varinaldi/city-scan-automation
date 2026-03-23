# City Scan

A City Scan is a rapid geospatial assessment of a city's demographic, socioeconomic, climate, and risk conditions. It is a collection of maps and charts made from global and publicly available datasets that provide quick high-level insights into resilience-related topics for a city. These scans are especialy useful for grounding early-stage conversations in geospatial data.


This repository provides automation tools for city scanning and analysis. The new task-based structure organizes each topic and data source into its own module under `tasks/`, with standardized data collection, analysis, visualization components. 

---

## Getting Started

See [docs/getting-started.md](docs/getting-started.md) for setup, configuration, and usage instructions.

```
  city-scan-automation/                      mnt/2026-03-tunisia-tunis/                03-render-output/
 - - - - - - - - - - - -                    - - - - - - - - - - - - - -             - - - - - - - - - - - -
  inputs/             ──────── copy ──────▶   01-user-input/
    city_inputs.yml                             city_inputs.yml
    menu.yml                                    menu.yml
    AOI/                                        AOI/

  tasks/             `python -m tasks --all`  02-process-output/
    elevation/        ───── --collect ────▶     spatial/            ──▶ `Rscript 
    fathom/           ───── --analyze ────▶     tabular/                  core/R/maps-static.R` ──▶ maps/*.png
    worldpop/
    ...               ── --multianalysis ─▶     tabular/
      charts/
        index.qmd ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  ─ ─ ─ ─ ─  ┐
                                                                            ▼
        └──────────────────── copy ───────▶  tasks/                      includes      ──▶ plots/*.png
  core/                                      core/                          :
  source/                                    source/                        :
  scan-calculations/                         scan-calculations/    ──▶ `quarto render` ──▶ scan-calculations.html
  .here (R Path Resolution)
                                          
```

### Workflow

While this repository provides a modular structure, the general workflow is as follow:
1. **Configure** — set up AOI boundary and city parameters in `inputs/`
2. **Collect** — download and clip global datasets to the AOI
3. **Analyze** — compute statistics, generate CSVs and processed data
4. **Map** — generate static maps from spatial data using `layers.yml` styling
5. **Chart** — render / sandbox per-topic Quarto charts
6. **Compile** — assemble charts into a single scan-calculations referece sheet

Steps 2–3 are handled per task via `python -m tasks`. Steps 4–6 are handled by `Rscripts` and the `quarto render`, and must be run from the city root (e.g. `mnt/2026-03-tunisia-tunis/`).




### Structure

The main components to run a city scan are

- **`inputs/`** — User config for new scans (city_inputs.yml, menu.yml, AOI/)
- **`tasks/`** — Scan topics, each with collection, analysis, and charts
    - **`charts`** — contains `index.qmd`to create / sandbox charts 
- **`core/`** — Shared infrastructure (config, Python utils, R functions, OJS charts)
- **`source/`** — Canonical configs copied to each city (layers.yml, text, styling)
- **`logs/`** — Auto-created log files

The output scan folder will be saved in **`mnt/`** under the directory name: **`YYYY-MM-country-city`**, automaticaly generated and referencing `city-inputs.yml`. 

This scan directory will include:

- copies of **`tasks/`**, **`core/`** ,**`source/`**, **`logs/`**
- files in **`inputs/`** will be copied to **`01-user-inputs`**
- output spatila/raster and tabular data in **`02-process-outputs`**
- empty **`03-render-outputs`** for saving static maps and charts 
- **`scan-calculations/`** — Quarto project that compiles `tasks/*/charts` into a reference sheet (see [scan-calculations](scan-calculations/README.md))


Other folders that will stay in root:

- **`docs/`** — Setup guides and reference
- **`notebook/`** — sample notebooks for exploration, testing, and data cleaning
- **`templates/`** — Boilerplate files for creating new tasks (see [docs/tasks.md](docs/tasks.md)) ** *need improvement* **

See [docs/structure.md](docs/structure.md) for detailed breakdown of each folder.



### Path Resolution

The CLI and scripts can run from two locations:

- **Root** (`city-scan-automation/`) — on first run, `python -m tasks --all` creates the city folder in `mnt/` and copies `tasks/`, `core/`, `source/` into it. Use `--scan-id` to target an existing city.
- **City folder** (`mnt/YYYY-MM-country-city/`) — run directly from here after the first run. All paths resolve relative to this folder.

R scripts use the `here` package (`.here` file) to resolve the project root. Python uses `core/config/paths.py` which auto-detects whether it's running from root or a city folder by looking for `01-user-input/`. Both approaches ensure the same code works from either location.

