#!/usr/bin/env Rscript
# Plot building footprints — run from city directory
# Reads clipped buildings from 02-process-output/spatial/
# Usage: Rscript R/plot-building-footprints.R <city-directory-name>

suppressPackageStartupMessages({
  library(terra)
  library(ggplot2)
  library(dplyr)
  library(tidyterra)
  library(stringr)
  library(yaml)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  cat("Usage: Rscript R/plot-building-footprints.R <city-directory-name>\n")
  quit(status = 1)
}

city_dir_name <- args[1]
city_string <- str_match(city_dir_name, "\\d{4}-\\d{2}-[a-z]+-(.+)$")[1, 2]

# Read AOI using AOI_shp_name from city_inputs.yml
city_inputs <- read_yaml("01-user-input/city_inputs.yml")
aoi_shp <- city_inputs$AOI_shp_name
aoi_path <- if (!is.null(aoi_shp)) file.path("01-user-input/AOI", paste0(aoi_shp, ".shp")) else "01-user-input/AOI"
aoi <- vect(aoi_path)
focus <- ext(aoi)

# Read clipped buildings
buildings_path <- file.path("02-process-output/spatial", paste0(city_string, "_building_footprints.fgb"))
if (!file.exists(buildings_path)) {
  cat("Error: No building footprints found at", buildings_path, "\n")
  cat("Run download-buildings.py first\n")
  quit(status = 1)
}
buildings <- vect(buildings_path)
cat("Loaded", nrow(buildings), "buildings\n")

# Roads (optional)
roads_path <- "02-process-output/spatial/edges-edit.gpkg"
roads <- if (file.exists(roads_path)) vect(roads_path)[focus] else NULL
if (!is.null(roads)) cat("Loaded", nrow(roads), "road segments\n")

# Plot
p <- ggplot() +
  geom_spatvector(data = buildings, color = NA, fill = "#FF9C28") +
  theme_void() +
  theme(panel.background = element_rect(fill = "black"))

if (!is.null(roads)) {
  p <- p + geom_spatvector(data = roads, color = "white", size = 0.0125)
}

# Save
output_dir <- "03-render-output/maps"
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
output_file <- file.path(output_dir, paste0(city_string, "_building_footprints.png"))

ggsave(filename = output_file, plot = p, width = 8.77, height = 7.55, dpi = 200)
cat("Saved:", output_file, "\n")
