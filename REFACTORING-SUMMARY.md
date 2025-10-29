# City Scan Automation - Workflow Refactoring Summary

**Date:** October 28, 2025
**Status:** ✅ Complete - Ready for Testing

## What Was Done

I've refactored your city scan workflow to integrate `scan-calculations.Rmd` into the `city-scan-automation` directory structure, eliminating the need for separate `01-current-scans/` folders and manual data copying.

---

## New Directory Structure

### Before (Scattered)
```
city-scan-automation/
├── mnt/{city}/
│   └── 02-process-output/     # Data here
│       └── tabular/

01-current-scans/{city}/        # Separate directory!
├── scan-calculations.Rmd       # Copy of code
├── user-inputs.R
├── AOI/                        # Manually copied
└── data-sharing/
    └── 04-tabular-data/        # Manually copied
```

### After (Integrated)
```
city-scan-automation/
└── mnt/{city}/
    ├── 01-user-input/          # User inputs
    │   ├── AOI/
    │   └── city_inputs.yml
    │
    ├── 02-process-output/      # Backend generates
    │   ├── spatial/
    │   └── tabular/
    │
    ├── 03-render-output/       # Frontend generates
    │   └── maps/
    │
    └── 04-analysis/            # ✨ NEW: Analysis reports
        ├── scan-calculations.Rmd
        ├── user-inputs.R
        ├── README.md
        └── scan-calculations.html  # Generated
```

---

## Files Created

### For Each City

I've created `04-analysis/` folders with these files:

**Dakar:**
- `/mnt/2025-10-senegal-dakar/04-analysis/scan-calculations.Rmd`
- `/mnt/2025-10-senegal-dakar/04-analysis/user-inputs.R`
- `/mnt/2025-10-senegal-dakar/04-analysis/README.md`

**Matam:**
- `/mnt/2025-10-senegal-matam/04-analysis/scan-calculations.Rmd`
- `/mnt/2025-10-senegal-matam/04-analysis/user-inputs.R`
- `/mnt/2025-10-senegal-matam/04-analysis/README.md`

**Diourbel:**
- `/mnt/2025-10-senegal-diourbel/04-analysis/scan-calculations.Rmd`
- `/mnt/2025-10-senegal-diourbel/04-analysis/user-inputs.R`
- `/mnt/2025-10-senegal-diourbel/04-analysis/README.md`

**Tambacounda:**
- `/mnt/2025-10-senegal-tambacounda/04-analysis/scan-calculations.Rmd`
- `/mnt/2025-10-senegal-tambacounda/04-analysis/user-inputs.R`
- `/mnt/2025-10-senegal-tambacounda/04-analysis/README.md`

**Sofifi:**
- `/mnt/2025-10-indonesia-sofifi/04-analysis/scan-calculations.Rmd`
- `/mnt/2025-10-indonesia-sofifi/04-analysis/user-inputs.R`
- `/mnt/2025-10-indonesia-sofifi/04-analysis/README.md`

---

## Key Features

### 1. Single Master Rmd Template
- All cities use the same `scan-calculations.Rmd`
- No more maintaining duplicate code
- Fix once, applies everywhere

### 2. City-Specific Configuration
Only `user-inputs.R` differs per city:
```r
city <- "Dakar"
bm_cities_manual <- c("Abidjan", "Accra", "Lagos", ...)
nearby_countries_string <- "ivory coast|ghana|nigeria|..."
```

### 3. Automatic Data Access
- Reads from `../02-process-output/tabular/`
- Reads from `../01-user-input/AOI/`
- Reads from `../03-render-output/maps/`
- No manual copying needed!

### 4. Plugin System for Custom Analysis
Create `custom-analysis/*.Rmd` files for city-specific analysis:

**Example: Port analysis for Dakar only**
```
04-analysis/
└── custom-analysis/
    └── port-analysis.Rmd  # Only in Dakar's folder
```

This gets automatically included when rendering.

---

## How to Use

### Test the New System

1. **Navigate to a city's analysis folder:**
   ```bash
   cd city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis
   ```

2. **Open in RStudio or render directly:**
   ```r
   rmarkdown::render("scan-calculations.Rmd")
   ```

3. **Compare with old version:**
   ```bash
   # Old version
   open /Users/vivaldirinaldi/Documents/Work/01-current-scans/2025-10-senegal-dakar/scan-calculations.html

   # New version
   open /Users/vivaldirinaldi/Documents/Work/city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis/scan-calculations.html
   ```

### Run for All Cities

```bash
cd city-scan-automation

# For each city
for city in 2025-10-senegal-dakar 2025-10-senegal-matam 2025-10-senegal-diourbel 2025-10-senegal-tambacounda 2025-10-indonesia-sofifi; do
  echo "Rendering $city..."
  cd mnt/$city/04-analysis
  Rscript -e "rmarkdown::render('scan-calculations.Rmd')"
  cd ../../..
done
```

---

## What Changed in the Rmd

### Path Updates

**Old paths (in 01-current-scans/):**
```r
oxford_file <- "../../03-multi-scan-materials/Oxford Global Cities Data.csv"
aoi <- read_sf("AOI")
```

**New paths (in mnt/{city}/04-analysis/):**
```r
oxford_file <- "../../../../03-multi-scan-materials/Oxford Global Cities Data.csv"
aoi <- read_sf("../01-user-input/AOI")
```

### Automatic Data Copying

The new Rmd automatically:
1. Creates `data-sharing/` subdirectories
2. Copies AOI from `../01-user-input/AOI/`
3. Copies tabular data from `../02-process-output/tabular/`

### Custom Analysis Support

New feature - automatically includes custom Rmd sections:
```r
custom_sections <- list.files("custom-analysis", pattern = "\\.Rmd$")
for (section_file in custom_sections) {
  knitr::knit_child(section_file)
}
```

---

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Maintenance** | Update Rmd in 5+ places | Update once |
| **Data copying** | Manual | Automatic |
| **Customization** | Edit entire Rmd | Add small custom file |
| **Organization** | Scattered folders | Single directory tree |
| **Consistency** | Hard to maintain | Guaranteed |

---

## Future: Plugin System for Maps

I also recommend implementing a similar plugin system for `maps-static.R`:

**Master script:** `frontend/R/maps-static.R` (works for all cities)

**City-specific overrides:** `mnt/{city}/01-user-input/custom-plots/`
- `aoi.R` - Custom AOI plot
- `elevation.R` - Custom elevation plot
- `port-analysis.R` - Completely new plot type

This way:
- 99% of cities use default plotting
- Special cases (like Matam's ward labels) can be customized
- New plot types can be added per city without touching master code

---

## Next Steps

1. **Test the new system** with Dakar:
   ```bash
   cd city-scan-automation/mnt/2025-10-senegal-dakar/04-analysis
   Rscript -e "rmarkdown::render('scan-calculations.Rmd')"
   ```

2. **Compare outputs** with old version in `01-current-scans/`

3. **If satisfied:**
   - Migrate any remaining analysis sections
   - Deprecate `01-current-scans/` folder
   - Update documentation

4. **Optional:** Implement plugin system for `maps-static.R` as well

---

## Questions or Issues?

Read the detailed README in each city's `04-analysis/` folder:
```
mnt/{city}/04-analysis/README.md
```

---

## Summary

✅ All 5 cities now have `04-analysis/` folders
✅ Single master Rmd template
✅ City-specific configs via `user-inputs.R`
✅ Automatic data access (no manual copying)
✅ Plugin system for custom analysis
✅ Documentation in each folder

**You can now test by running the Rmd in any city's `04-analysis/` folder and comparing with the old version!**
