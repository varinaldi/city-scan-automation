# Getting Started

#### Step 1: Configure Setup

City Scan uses multiple programming languages and software to run, including:

- [Git](setup.md#git)
- [Python](setup.md#python)
- [R](setup.md#r)
- [Quarto](setup.md#quarto)
- [Google Cloud](setup.md#gcloud) - for acessing data, see [authentication](googlecloud.md) details.


See [setup.md](setup.md) for detailed instruction.


#### Step 2: Clone the Repository

```
git clone -b unified https://github.com/varinaldi/city-scan-automation.git
cd city-scan-automation
```


#### Step 3: Configure Inputs

Adjust the files in the `inputs/` folder for your specific project:
- Use `AOI/` folder and store your AOI boundary file there
- Modify `city_inputs.yml` and `menu.yml` with your analysis parameters

#### Step 4: Running Tasks

*Make sure the Python environment is activated*.


Executing task can be done using a terminal, either from `city-scan-automation` directory, or within the `mnt/scan-id`. To execute any task:
```
python -m tasks {TASKNAME} {FLAG}
```


Each task is divided into different steps, defined by `{FLAG}`:
- **`--collect`** runs data collection and save outputs in  `02-process-outputs/spatial or /tabular`
- **`--analyze`** runs data analysis and creates outputs .csvs in `02-process-outputs/tabular`
- **`--all`** runs both **`--collect`** and **`--analyze`** at the same time, reads `menu.yml`
- **`--multianalysis`** Runs multilayer analysis ** *Currently only for fathom* **
- **`--visualize`** ** *Legacy function, need to fix* **


To run both data collection and analysis for all tasks that are set to true in `menu.yml` in sequence:

```
python -m tasks --all
```


When running the above command from
- **`city-scan-automation`** root folder -  it will initialize the `mnt/scan-id` and create & copies all the necessary folders.
    - can also be used to run task for specific scan id using `--scan-id` flag
    ```
    python -m tasks --all --scan-id 2026-02-malta-malta
    ```
- inside **`mnt/scan-id`** - it will output files in `02-process-outputs/spatial or /tabular`


To run individual task, or a set of tasks:

```
# Individual task
python -m tasks wsf

# Multiple tasks
python -m tasks wsf population forest
```

Individual `{FLAG}` can also be used to run specific steps:
```
# Collect step only
python -m tasks wsf --collect

# Analyze step only for multiple task
python -m tasks wsf population green --analyze

```

Other available `{FLAG}`:
```
# Show available tasks
python -m tasks --list

# optional upload outputs to GCS, can be for all tasks or specific tasks
python -m tasks --all --upload
python -m accessibility --collect --upload
```

#### Experimential: Running parallel Task Processings
```
python -m task --all --parallel
```
This feature allows for running multiple task in parallel. It will create a Terminal UI (TUI) that allows for monitoring task progress and their logs. 

**Known Bug:**  

### Rendering Maps and Charts
> [!WARNING]
> Steps 5 and 6 must be run from the city root folder.
> ```
> cd mnt/2026-03-tunisia-tunis/
> ```

#### Step 4b: Multi-analysis

Some tasks have cross-task analysis scripts (e.g. flood exposure calculations that combine flood and WSF data). Run these after all individual tasks have completed:
```
python -m tasks --all --multianalysis
```

#### Step 5: Rendering Maps and Charts

After data collection and analysis, generate maps and the scan-calculations report.

**Static Maps** — run from the city folder (`mnt/scan-id`):
```
Rscript core/R/maps-static.R
```
This reads spatial data from `02-process-output/spatial/`, applies styling from `source/layers.yml`, and saves map PNGs to `03-render-output/maps/`.

**Charts** — each task has its own `charts/index.qmd` that can be rendered independently:
```
quarto render tasks/elevation/charts
```
This produces an HTML file at `tasks/elevation/charts/index.html` with the charts for that task.

#### Step 6: Scan Calculations Reference Sheet

The `scan-calculations` reads `sections.yml` to determine the section order, then assembles all per-task `charts/index.qmd` into a single combined HTML report:
```
quarto render scan-calculations
```
The compiled report is saved to `scan-calculations/scan-calculations.html`.

If `scan_calculations: True` is set in `menu.yml`, the scan-calculations folder is automatically copied to the city folder when running `python -m tasks --all`.

See [scan-calculations/README.md](../scan-calculations/README.md) for details.
