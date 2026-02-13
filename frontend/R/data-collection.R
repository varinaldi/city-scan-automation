#!/usr/bin/env Rscript
# Data collection for WSF Tracker and WorldPop Global 2
# Run from city directory after setup.R has been sourced
# Usage: source("R/data-collection.R") from scan-calculations.Rmd or standalone

# Requires: aoi, city_string, country, spatial_dir, tabular_dir from setup.R
# Requires: GCS credentials (gcloud auth application-default login)

suppressPackageStartupMessages({
  library(terra)
  library(dplyr)
  library(glue)
  library(stringr)
})

Sys.setenv(GOOGLE_APPLICATION_CREDENTIALS = path.expand("~/.config/gcloud/application_default_credentials.json"))

# Clear GDAL cloud cache to avoid stale data from prior GCS reads (e.g. setup.R)
setGDALconfig("CPL_VSIL_CURL_CACHE_SIZE", "0")
setGDALconfig("VSI_CACHE", "FALSE")

#### WSF Tracker ----------------------------------------------------------------

# Currently runs locally and only for Africa (other data is downloaded already)
# collect_wsf_tracker <- function(aoi, output_dir = NULL, source = "/Volumes/notkin-ssd/world-bank/data/wsf-tracker/Global") {
collect_wsf_tracker <- function(aoi, output_dir = NULL, source = "/vsigs/city-scan-global-private/wsf_tracker") {

  # Get extent
  aoi_ext <- ext(aoi)
  minx <- aoi_ext[1]
  maxx <- aoi_ext[2]
  miny <- aoi_ext[3]
  maxy <- aoi_ext[4]

  # Create sequences for x and y
  x_seq <- seq(floor(minx - minx %% 2), ceiling(maxx), by = 2)
  y_seq <- seq(floor(miny - miny %% 2), ceiling(maxy), by = 2)

  # Create all combinations of x and y
  xy_grid <- expand.grid(x = x_seq, y = y_seq)

  # Find relevant tiles
  wsf_file_list <- file.path(source, glue("WSFtracker_20160701-20250701_{xy_grid$x}_{xy_grid$y}.tif"))

  # Merge tiles if needed, crop to AOI extent
  if (length(wsf_file_list) == 1) {
    wsf_tracker <- crop(rast(wsf_file_list), aoi, mask = T)
  } else {
    wsf_tracker_sprc <- sprc(wsf_file_list)
    wsf_tracker <- merge(wsf_tracker_sprc, filename = file.path(tempdir(), "wsf_tracker_20160701-20250701_merge.tif"), overwrite = TRUE)
    wsf_tracker <- crop(wsf_tracker, aoi, mask = T)
  }

  # Clean data for mapping
  NAflag(wsf_tracker) <- 0
  wsf_tracker$era <- seq(from = 2016.5, by = .5, length = global(wsf_tracker$mode, "max", na.rm = TRUE))[wsf_tracker$mode[,,1]]

  # Save map-ready output
  if (!is.null(output_dir)) {
    path <- file.path(output_dir, paste0(city_string, "_wsf_tracker_extended.tif"))
    wsf_tracker %>% writeRaster(path, overwrite = TRUE, datatype = "FLT4S")
    wsf_tracker <- rast(path)
  }

  return(wsf_tracker)
}

# Create table of cumulative built-up area over time
stats_wsf_tracker <- function(x) {
  if (is.character(x)) x <- rast(x)
  x$area <- cellSize(x)
  df <- as_tibble(x) %>%
      filter(!is.na(era)) %>%
      arrange(era) %>%
      summarize(.by = era, AREA_sq_km = sum(area) / 1e6) %>%
      mutate(AREA_sq_km = cumsum(AREA_sq_km)) %>%
      mutate(.keep = "unused", year = floor(era), month = if_else(era %% 1 == 0, 1L, 7L)) %>%
      select(year, month, AREA_sq_km)
  return(df)
}

#### WorldPop ------------------------------------------------------------------

collect_worldpop <- function(aoi, output_dir = NULL, source = "/vsigs/city-scan-global-public/world_population/WorldPop-Global-2") {

  # Clear GDAL cloud cache before reading from GCS (avoids stale cached data)
  setGDALconfig("CPL_VSIL_CURL_CACHE_SIZE", "0")
  setGDALconfig("VSI_CACHE", "FALSE")

  iso <- countrycode::countrycode(country, "country.name", "iso3c")
  years <- 2015:2030

  # # For downloading from WorldPop directly
  # # Task: Only download from WorldPop if the files don't already exist on cloud
  # # Check if files exist on cloud and if not, proceed, uploading them to cloud
  # temp_dir <- "WorldPop-Global2"
  # dir.create(temp_dir, showWarnings = F)
  # country_rasters_urls <- glue::glue("https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/{years}/{iso}/v1/100m/constrained/{tolower(iso)}_pop_{years}_CN_100m_R2025A_v1.tif")
  # rast_paths <- file.path(temp_dir, basename(country_rasters_urls))
  # map2(country_rasters_urls[!file.exists(rast_paths)], rast_paths[!file.exists(rast_paths)], \(url, local) {
  #   curl::curl_download(url, destfile = local)
  # })

  rast_paths <- glue::glue("{source}/{tolower(iso)}_pop_{years}_CN_100m_R2025A_v1.tif")

  # Download cropped region to temp to avoid GDAL vsigs cache issues
  temp_dir <- file.path(tempdir(), "WorldPop-Global2")
  dir.create(temp_dir, showWarnings = FALSE)
  local_paths <- file.path(temp_dir, paste0(tolower(iso), "_pop_", years, "_cropped.tif"))
  for (i in seq_along(rast_paths)) {
    if (!file.exists(local_paths[i])) {
      message("  Downloading: ", basename(rast_paths[i]))
      crop(rast(rast_paths[i]), ext(aoi)) %>%
        writeRaster(local_paths[i], overwrite = TRUE)
    }
  }

  country_rasters <- rast(local_paths)
  names(country_rasters) <- paste0("pop_", years)

  # Crop and mask to AOI
  worldpop_2015_2030 <- crop(country_rasters, aoi, mask = T)

  if (!is.null(output_dir)) {
    path <- file.path(output_dir, paste0(city_string, "_worldpop_2015_2030_extended.tif"))
    writeRaster(worldpop_2015_2030, filename = path, overwrite = T)
    # writeRaster(worldpop_2015_2030$pop_2025, filename = file.path(output_dir, paste0(city_string, "_worldpop_2025.tif")), overwrite = T)
    worldpop_2015_2030 <- rast(path)
  }

  return(worldpop_2015_2030)
}

collect_worldpop_global1 <- function(aoi, output_dir = NULL) {

    iso <- countrycode::countrycode(country, "country.name", "iso3c")
    years <- 2000:2020

    temp_dir <- file.path(tempdir(), "WorldPop-Global1")
    dir.create(temp_dir, showWarnings = F)

    # WorldPop Global1 URL pattern (verified)
    # country_rasters_urls <- glue::glue(
    #   "https://data.worldpop.org/GIS/Population/Global_2000_2020/{years}/{toupper(iso)}/{tolower(iso)}_ppp_{years}_UNadj.tif"
    # )
    country_rasters_urls <- glue::glue(
      "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/{years}/{toupper(iso)}/{tolower(iso)}_ppp_{years}_1km_Aggregated_UNadj.tif"
    )
    rast_paths <- file.path(temp_dir, basename(country_rasters_urls))

    # Download only if not already downloaded
    purrr::walk2(country_rasters_urls, rast_paths, \(url, local) {
      if (!file.exists(local)) {
        message("Downloading: ", basename(url))
        curl::curl_download(url, destfile = local)
      }
    })

    country_rasters <- rast(rast_paths)
    names(country_rasters) <- paste0("pop_", years)

    # Crop and mask to AOI
    worldpop_2000_2020 <- crop(country_rasters, aoi, mask = T)

    if (!is.null(output_dir)) {
      path <- file.path(output_dir, paste0(city_string, "_worldpop_2000_2020_extended.tif"))
      writeRaster(worldpop_2000_2020, filename = path, overwrite = T)
      worldpop_2000_2020 <- rast(path)
    }

    return(worldpop_2000_2020)
  }

stats_worldpop <- function(x) {
  if (is.character(x)) x <- rast(x)
  worldpop_df <- as_tibble(x) %>%
    summarize(.by = NULL, across(everything(), ~ sum(.x, na.rm = T))) %>%
    t() %>% as.data.frame() %>%
  mutate(year = as.numeric(str_extract(rownames(.), "\\d{4}")), population = V1, .keep = "none") %>%
  as_tibble()
  return(worldpop_df)
}


#### Run data collection -------------------------------------------------------

if (!exists("aoi") || !exists("city_string") || !exists("country")) {
  stop("Run setup.R first to set aoi, city_string, country, spatial_dir, tabular_dir")
}

# Buffer AOI for data collection (same as Nouakchott data-processing.R)
aoi_ext <- ext(aoi)
buffer_dist_deg <- max(aoi_ext[2] - aoi_ext[1], aoi_ext[4] - aoi_ext[3])
buffer_dist_m <- buffer_dist_deg * 111000
aoi_buffered <- buffer(aoi, buffer_dist_m)

# --- WSF Tracker ---
message("\n=== Collecting WSF Tracker ===")
wsf_tracker_path <- file.path(spatial_dir, paste0(city_string, "_wsf_tracker_extended.tif"))
if (!file.exists(wsf_tracker_path)) {
  wsf_tracker <- collect_wsf_tracker(aoi_buffered, spatial_dir)
  stats_wsf_tracker(wsf_tracker %>% crop(aoi, mask = T)) %>%
    readr::write_csv(file.path(tabular_dir, paste0(city_string, "_wsf_tracker.csv")))
  message("WSF Tracker saved.")
} else {
  message("WSF Tracker already exists, recalculating stats...")
  wsf_tracker <- rast(wsf_tracker_path)
  stats_wsf_tracker(wsf_tracker %>% crop(aoi, mask = T)) %>%
    readr::write_csv(file.path(tabular_dir, paste0(city_string, "_wsf_tracker.csv")))
}

# --- WorldPop Global 2 (2015-2030) ---
message("\n=== Collecting WorldPop Global 2 ===")
worldpop_path <- file.path(spatial_dir, paste0(city_string, "_worldpop_2015_2030_extended.tif"))
if (!file.exists(worldpop_path)) {
  worldpop <- collect_worldpop(aoi_buffered, spatial_dir)
  stats_worldpop(worldpop %>% crop(aoi, mask = T)) %>%
    readr::write_csv(file.path(tabular_dir, paste0(city_string, "_worldpop_2015_2030.csv")))
  message("WorldPop Global 2 saved.")
} else {
  message("WorldPop Global 2 already exists, recalculating stats...")
  worldpop <- rast(worldpop_path)
  stats_worldpop(worldpop %>% crop(aoi, mask = T)) %>%
    readr::write_csv(file.path(tabular_dir, paste0(city_string, "_worldpop_2015_2030.csv")))
}

message("\n=== Data collection complete ===")
