### Integration Checklist

#### Frontend
**to do integrattion list**

- scripts/frontend.sh scan-id
    - add --gcs to only clone the subdir folders but not the files
        - authenticate
            - if fails, go back to cloning the files.

- but then again then again, as of now, we still need to be authenticated to download the file right? what should we do here 
    - check if scan-id/subdir is already in mnt


- frontend/run.sh
    - add check if --gcs flag was ever used
    - 






- **Map Scripts Pattern Inconsistency**
  - `map-ghs-expansion.R` and `map-economic-activity-1km.R` don't follow the YAML pattern
  - Other map scripts use `plot_static_layer()` with `yaml_key` from `layers.yml`
  - New scripts use manual ggplot + direct `save_plot()` calls
  - **TODO:** Refactor to use YAML pattern for consistency
    - Add entries to `layers.yml` for: ghs_residential_expansion, ghs_nonresidential_expansion, economic_residential_1km, economic_commercial_1km, economic_industrial_1km
    - Refactor scripts to use `plot_static_layer()` instead of manual ggplot
  - **For now:** Running as-is with direct sourcing in maps-static.R


#### Analytics Layer
- Economic activity mapping model integration


#### Backend 
- Adding new data sources possible - locally or in cloud
  - Test and run in machine
  - How easy is it to plug in new data sources?
    - GHS Built S
    - WorldPop
    - Black Marble vs VIIRS
- Local data availability checks / viewer
  - This should clear up what data is available for which city




### LOGS

#### 2025-10-24
- Task 10 works in US East1 not in US Central1 - somehting to do with AWS fanthom credentials
- Task 16 is missing GEE noncommercial eligibility verification
- Task 6-7 WorldPop - somehting
- to do with ISO3 code not matching / returning the right data



#### 2025-11-03 - Backend Data Issues
- Missing Flood data
  - MATAM - Coastal missing - Pluvial, Fluvial, Combined available
  - DIOURBEL - Pluvial, Coastal, Combined Fluvial available
  - TAMBACOUNDA Coastal missing - Fluvial, Pluvial, Combined available 
  