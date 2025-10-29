# Plugin System Proposal - City Scan Automation

**Date:** October 28, 2025
**Status:** Proposal for Future Implementation

---

## Executive Summary

This document proposes a **plugin/override architecture** for the city-scan-automation workflow to solve the core problem: **How do we maintain a single master codebase while allowing city-specific customizations?**

### Current Pain Points

1. **Duplicated R scripts**: Each city has 28 identical R files that must be manually synced
2. **City-specific variations**: Some cities need different plotting logic (e.g., Matam's ward labels)
3. **Future customizations**: Cannot easily add city-specific plots without editing master code
4. **Maintenance burden**: Bug fixes must be applied to multiple copies

### Proposed Solution

A **three-tier system**:
1. **Master templates** - Single source of truth (99% of code)
2. **YAML configuration** - City-specific settings (simple variations)
3. **Plugin overrides** - Custom code files (complex variations)

---

## Architecture Overview

```
city-scan-automation/
├── frontend/R/                      # MASTER TEMPLATES (Tier 1)
│   ├── maps-static.R                # Orchestrator with plugin support
│   ├── map-elevation.R
│   ├── map-flooding.R
│   └── [all other R scripts]
│
└── mnt/{city}/
    ├── 01-user-input/
    │   ├── city_inputs.yml          # YAML CONFIG (Tier 2)
    │   │   # Simple settings: colors, labels, etc.
    │   │
    │   └── custom-plots/            # PLUGIN OVERRIDES (Tier 3)
    │       ├── aoi.R                # Replace default AOI plot
    │       ├── elevation.R          # Replace default elevation plot
    │       └── port-analysis.R      # New plot (doesn't exist in master)
    │
    ├── 02-process-output/
    ├── 03-render-output/
    └── 04-analysis/
        ├── scan-calculations.Rmd    # Uses same plugin system
        └── custom-analysis/
            └── demographics.Rmd     # City-specific analysis sections
```

---

## Tier 1: Master Templates

### Purpose
Single source of truth that works for 99% of cities.

### Location
```
frontend/R/maps-static.R
frontend/R/map-*.R
frontend/R/setup.R
etc.
```

### How It Works

**Before (Current):**
```r
# maps-static.R - copied to each city
plots$aoi <- plot_static_layer(...)

if (inherits(wards, "SpatVector")) {
  plots$wards <- plot_static_layer(...)
}
```

**After (Plugin System):**
```r
# frontend/R/maps-static.R - single master
source("R/setup.R")

# Plugin helper functions
custom_plots_dir <- file.path(user_input_dir, "custom-plots")

has_custom_plot <- function(plot_name) {
  file.exists(file.path(custom_plots_dir, paste0(plot_name, ".R")))
}

plot_with_override <- function(plot_name, default_code) {
  custom_file <- file.path(custom_plots_dir, paste0(plot_name, ".R"))

  if (file.exists(custom_file)) {
    message("📍 Using custom plot: ", plot_name)
    source(custom_file, local = parent.frame())
  } else {
    force(default_code)
  }
}

# Use in plotting
plot_with_override("aoi", {
  plots$aoi <- plot_static_layer(...)
  if (inherits(wards, "SpatVector")) {
    plots$wards <- plot_static_layer(...)
  }
})
```

### Benefits
- One file to maintain
- Automatic updates for all cities
- No code duplication

---

## Tier 2: YAML Configuration

### Purpose
Simple city-specific settings that don't require code changes.

### Location
```
mnt/{city}/01-user-input/city_inputs.yml
```

### Example Configuration

```yaml
city_name: Matam
country_name: Senegal

# Map rendering settings
map_rendering:
  enable_ward_labels: false        # Matam-specific: no ward labels
  enable_ward_boundaries: true
  zoom_adjustment: 0
  custom_basemap: null

  # Layer-specific overrides
  elevation:
    custom_breaks: [0, 50, 100, 200, 500, 1000]
    color_palette: "terrain"

  aoi:
    stroke_color: "yellow"
    stroke_width: 0.4

# Analysis settings
analysis:
  benchmark_cities:
    - Ouagadougou
    - N'Djamena
    - Conakry
  nearby_countries: "ivory coast|ghana|nigeria"
```

### How Master Code Reads It

```r
# In setup.R
city_params <- yaml::read_yaml(file.path(user_input_dir, "city_inputs.yml"))

# In maps-static.R
render_ward_labels <- city_params$map_rendering$enable_ward_labels %||% TRUE

if (inherits(wards, "SpatVector") && render_ward_labels) {
  plots$wards <- plot_static_layer(...)
}
```

### Use Cases for YAML
- ✅ Enable/disable features
- ✅ Color schemes
- ✅ Numeric parameters (zoom, breaks, thresholds)
- ✅ Text labels
- ✅ Basemap URLs
- ❌ Complex logic (use Tier 3 plugins instead)

---

## Tier 3: Plugin Overrides

### Purpose
Complete custom code for cities with unique requirements that can't be handled by YAML.

### Location
```
mnt/{city}/01-user-input/custom-plots/{plot-name}.R
```

### When to Use Plugins

**Use YAML if:**
- Simple on/off toggle
- Different numbers/colors
- Standard configuration

**Use Plugin if:**
- Completely different plotting logic
- New data sources
- City-specific analysis
- Complex conditional logic

### Example 1: Matam Ward Override

**File:** `mnt/2025-10-senegal-matam/01-user-input/custom-plots/aoi.R`

```r
# Matam: Custom AOI plot without ward labels

message("Matam: Using custom AOI visualization")

plots$aoi <- plot_static_layer(
  aoi_only = TRUE,
  plot_aoi = TRUE,
  plot_wards = !is.null(wards),
  expansion = 1.5,
  zoom_adj = zoom_adjustment,
  aoi_stroke = list(color = "yellow", linewidth = 0.4),
  baseplot = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}.jpg"
)

# Note: We simply omit the ward label plotting code
# This replaces the default AOI plotting section entirely
```

### Example 2: Dakar Port Analysis

**File:** `mnt/2025-10-senegal-dakar/01-user-input/custom-plots/port-accessibility.R`

```r
# Dakar: Port accessibility analysis (completely new plot type)

message("Dakar: Creating port accessibility analysis")

# Define port locations
port_locations <- vect(data.frame(
  name = c("Port of Dakar", "Industrial Terminal"),
  lon = c(-17.4377, -17.4290),
  lat = c(14.6937, 14.7053)
), geom = c("lon", "lat"), crs = "epsg:4326")

# Calculate drive time zones
accessibility_zones <- calculate_drive_time_zones(
  origins = port_locations,
  road_network = roads,
  max_time = 60,
  intervals = c(15, 30, 45, 60)
)

# Create plot
plots$port_accessibility <- plot_static_layer(
  data = accessibility_zones,
  plot_aoi = TRUE,
  plot_wards = TRUE
) +
  geom_spatvector(
    data = accessibility_zones,
    aes(fill = drive_time),
    alpha = 0.6
  ) +
  scale_fill_viridis_c(name = "Drive time\nto port (min)") +
  geom_spatvector(data = port_locations, color = "red", size = 3)
```

### Example 3: Custom Elevation for Mountain City

**File:** `mnt/2025-11-bolivia-la-paz/01-user-input/custom-plots/elevation.R`

```r
# La Paz: Custom elevation with contours and altitude zones

elevation_data <- fuzzy_read(spatial_dir, "elevation")

plots$elevation <- plot_static_layer(
  data = elevation_data,
  yaml_key = "elevation",
  plot_aoi = TRUE,
  plot_wards = TRUE
) +
  # Add contour lines
  geom_spatraster_contour(
    data = elevation_data,
    breaks = c(3000, 3500, 4000, 4500),
    color = "white",
    linewidth = 0.3
  ) +
  # Highlight high altitude zones
  annotate(
    "text",
    x = -68.1,
    y = -16.5,
    label = "High altitude zone\n(>4000m)",
    color = "white",
    size = 3
  )
```

---

## Implementation Strategy

### Phase 1: Core Plugin System (Priority)

**Modify: `frontend/R/maps-static.R`**

```r
# Add at top of file
custom_plots_dir <- file.path(user_input_dir, "custom-plots")

has_custom_plot <- function(plot_name) {
  file.exists(file.path(custom_plots_dir, paste0(plot_name, ".R")))
}

plot_with_override <- function(plot_name, default_code) {
  custom_file <- file.path(custom_plots_dir, paste0(plot_name, ".R"))

  if (file.exists(custom_file)) {
    message("📍 Using custom plot: ", plot_name, " (", custom_file, ")")
    source(custom_file, local = parent.frame())
  } else {
    force(default_code)
  }
}

# Wrap existing plotting sections
plot_with_override("aoi", {
  plots$aoi <- plot_static_layer(...)
  if (inherits(wards, "SpatVector")) {
    plots$wards <- plot_static_layer(...)
  }
})

plot_with_override("landmarks", {
  # existing landmarks code
})

# Standard plots with override support
for (yaml_key in names(layer_params)) {
  plot_with_override(yaml_key, {
    # existing standard plotting code
  })
}

# Check for NEW custom plots not in master
custom_plot_files <- list.files(custom_plots_dir, pattern = "\\.R$", full.names = FALSE)
custom_plot_names <- gsub("\\.R$", "", custom_plot_files)
new_custom_plots <- setdiff(custom_plot_names, names(plots))

if (length(new_custom_plots) > 0) {
  message("📍 Found ", length(new_custom_plots), " new custom plots")
  for (custom_name in new_custom_plots) {
    plot_with_override(custom_name, {})
  }
}
```

### Phase 2: YAML Configuration Support

**Modify: `frontend/R/setup.R`**

```r
# Load city_inputs.yml with map rendering settings
if (file.exists(file.path(user_input_dir, "city_inputs.yml"))) {
  city_params <- yaml::read_yaml(file.path(user_input_dir, "city_inputs.yml"))

  # Extract map rendering settings
  if (!is.null(city_params$map_rendering)) {
    map_rendering <- city_params$map_rendering
  } else {
    map_rendering <- list()
  }
} else {
  map_rendering <- list()
}
```

**Use in plotting:**

```r
# Example: Ward labels
render_ward_labels <- map_rendering$enable_ward_labels %||% TRUE

if (inherits(wards, "SpatVector") && render_ward_labels) {
  ward_labels <- site_labels(wards, simplify = FALSE)
  plots$wards <- plot_static_layer(...)
}
```

### Phase 3: Extend to Analysis Pipeline

Apply same system to `scan-calculations.Rmd`:

**In scan-calculations.Rmd:**

```r
## Custom Analysis Sections
```{r load-custom-sections, echo=FALSE, results='asis'}
custom_analysis_dir <- "custom-analysis"

if (dir.exists(custom_analysis_dir)) {
  custom_sections <- list.files(
    custom_analysis_dir,
    pattern = "\\.Rmd$",
    full.names = TRUE
  )

  for (section_file in custom_sections) {
    result <- knitr::knit_child(section_file, quiet = TRUE)
    cat(result, sep = '\n')
  }
}
```
```

---

## Migration Plan

### Step 1: Create Plugin Infrastructure
- Modify `maps-static.R` with plugin helpers
- Test with one city (Dakar)

### Step 2: Migrate Matam
- Create `mnt/2025-10-senegal-matam/01-user-input/custom-plots/aoi.R`
- Test that it overrides default
- Remove edited maps-static.R from Matam folder

### Step 3: Roll Out to All Cities
- Remove duplicate R/ folders from all city directories
- Cities use master `frontend/R/` directly
- Only keep custom-plots/ for cities that need it

### Step 4: Add YAML Support
- Extend city_inputs.yml schema
- Migrate simple config to YAML
- Reduce number of plugin files needed

---

## Decision Tree: When to Use What

```
Need city-specific behavior?
│
├─ YES
│  │
│  ├─ Is it a simple setting (color, on/off, number)?
│  │  │
│  │  ├─ YES → Use YAML (Tier 2)
│  │  │     Example: enable_ward_labels: false
│  │  │
│  │  └─ NO  → Use Plugin (Tier 3)
│  │        Example: custom-plots/aoi.R
│  │
│  └─ Is it a completely new analysis/plot?
│     │
│     └─ YES → Use Plugin (Tier 3)
│           Example: custom-plots/port-analysis.R
│
└─ NO → Use Master Template (Tier 1)
      Works for 99% of cities
```

---

## Examples by City

### Dakar
**Needs:**
- Default behavior ✅
- Port analysis (new plot) ✅

**Structure:**
```
mnt/2025-10-senegal-dakar/
└── 01-user-input/
    ├── city_inputs.yml          # Standard config
    └── custom-plots/
        └── port-analysis.R      # NEW plot type
```

### Matam
**Needs:**
- No ward labels ✅

**Option A - Plugin:**
```
mnt/2025-10-senegal-matam/
└── 01-user-input/
    ├── city_inputs.yml
    └── custom-plots/
        └── aoi.R                # Override AOI plotting
```

**Option B - YAML (preferred):**
```yaml
# city_inputs.yml
map_rendering:
  enable_ward_labels: false
```

### Diourbel
**Needs:**
- Default behavior ✅

**Structure:**
```
mnt/2025-10-senegal-diourbel/
└── 01-user-input/
    └── city_inputs.yml          # Standard config only
```

### Future: La Paz (Mountain City)
**Needs:**
- Custom elevation with contours ✅
- Altitude zone annotations ✅

**Structure:**
```
mnt/2025-11-bolivia-la-paz/
└── 01-user-input/
    ├── city_inputs.yml
    └── custom-plots/
        └── elevation.R          # Override elevation plot
```

---

## Benefits Summary

### For Maintainers
- ✅ Single source of truth (one `maps-static.R`)
- ✅ Bug fixes apply to all cities
- ✅ Easy to add new features
- ✅ Clear separation of concerns

### For City-Specific Work
- ✅ Override only what's different
- ✅ Add new plots without touching master
- ✅ YAML for simple changes
- ✅ Full R code for complex changes

### For Scalability
- ✅ Works for 100+ cities
- ✅ No code duplication
- ✅ Easy onboarding of new cities
- ✅ Flexible enough for edge cases

---

## Comparison: Before vs After

### Before (Current)
```
frontend/R/maps-static.R (master)
mnt/dakar/R/maps-static.R (copy #1)
mnt/matam/R/maps-static.R (copy #2 - edited)
mnt/diourbel/R/maps-static.R (copy #3)
...
```
- ❌ 28 files × N cities
- ❌ Manual sync required
- ❌ Hard to track differences
- ❌ Bug fixes needed everywhere

### After (Plugin System)
```
frontend/R/maps-static.R (master - with plugin support)

mnt/matam/01-user-input/city_inputs.yml
    enable_ward_labels: false

mnt/dakar/01-user-input/custom-plots/port-analysis.R
```
- ✅ 1 master file
- ✅ Automatic updates
- ✅ Clear what's custom
- ✅ Fix once, applies everywhere

---

## Future Enhancements

### Auto-Discovery
Automatically detect available custom plots:
```r
# Show user what custom plots are available
custom_plots <- list.files(custom_plots_dir, pattern = "\\.R$")
message("Available custom plots: ", paste(custom_plots, collapse = ", "))
```

### Validation
Validate YAML config:
```r
validate_city_config <- function(config) {
  required <- c("city_name", "country_name")
  missing <- setdiff(required, names(config))
  if (length(missing) > 0) {
    stop("Missing required fields: ", paste(missing, collapse = ", "))
  }
}
```

### Plugin Documentation
Auto-generate documentation:
```r
# List all plugins and what they override
document_plugins <- function() {
  plugins <- list.files(custom_plots_dir, pattern = "\\.R$")
  for (p in plugins) {
    cat("- ", p, ": Overrides", gsub("\\.R$", "", p), "plot\n")
  }
}
```

---

## Conclusion

The plugin system provides a **scalable, maintainable architecture** that:

1. **Eliminates code duplication** (single master template)
2. **Supports customization** (YAML + plugins)
3. **Scales to 100+ cities** (tested pattern)
4. **Handles edge cases** (full R code in plugins)

Implementation can be **gradual**:
- Phase 1: Add plugin support to master
- Phase 2: Migrate Matam as proof-of-concept
- Phase 3: Roll out to all cities
- Phase 4: Add YAML configuration

This approach has been successfully used in many large-scale projects (Drupal, WordPress, Jenkins, etc.) and is well-suited for the city-scan-automation workflow.
