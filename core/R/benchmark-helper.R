# Benchmark city selection + Oxford availability check
# Sourced by: worldpop/analysis.R, oxford/collection.R
# Requires: setup.R already sourced (city, country, bm_cities_manual, nearby_countries_string, tabular_dir)

message("\n=== Benchmark city selection ===")

# Download Oxford locations from GCS
if (!exists("oxford_location_file") || !file.exists(oxford_location_file)) {
  oxford_location_file <- tempfile(fileext = ".csv")
  googleCloudStorageR::gcs_get_object("oxford-economics/oxford-locations.csv", bucket = "city-scan-global-data", saveToDisk = oxford_location_file)
}

# Is city in Oxford Economics? --------------------------------------------------------------
oxford_locations <- readr::read_csv(oxford_location_file, col_types = "c")
oxford_locations_in_country <- dplyr::filter(oxford_locations, Country == country)
in_oxford <- city %in% oxford_locations_in_country$Location

message(glue("{city} in Oxford Economics: {in_oxford}"))

# Read only population indicator from Oxford for size-matching ---------------------------------
if (!exists("oxford_file") || !file.exists(oxford_file)) {
  oxford_file <- tempfile(fileext = ".csv")
  googleCloudStorageR::gcs_get_object("oxford-economics/Oxford Global Cities Data.csv", bucket = "city-scan-global-data", saveToDisk = oxford_file)
}
oxford_pop <- tryCatch({
  read_csv(oxford_file,
    col_types = "cccccccccdddddddddddddddddddddddddddddddddddddddddcllldlcclcc") %>%
  mutate(Location = case_when(Location == "Lom\u00e9" ~ "Lomé",
                              Location == "Yaound\u00e9" ~ "Yaoundé",
                              T ~ Location)) %>%
  subset(Indicator == "Total population") %>%
  select(Location, Country, `2021`)
}, error = function(e) {
  message(glue("Could not read Oxford data for size-matching: {e$message}"))
  tibble()
})

# Get population estimate for benchmark size-matching ----------------------------------------
# Need a pop estimate to filter benchmark cities to similar size (±50%)
pop <- tryCatch({
  if (in_oxford) {
    oxford_pop %>%
      subset(Location == city) %>%
      pull(`2021`)
  } else {
    # Try WorldPop
    wpop_csv <- fuzzy_read(tabular_dir, "worldpop_2015_2030.csv", read_csv)
    if (!is.null(wpop_csv) && nrow(wpop_csv) > 0) {
      wpop_csv %>% slice_max(year, n = 1) %>% pull(population) / 1000  # Oxford is in thousands
    } else NULL
  }
}, error = function(e) NULL)

if (is.null(pop)) message("Warning: could not get population estimate for benchmark size-matching")

# Benchmark countries auto-detect if not specified -------------------------------------------
if (is.null(nearby_countries_string) || nearby_countries_string == "") {
  tryCatch({
    # Load economic classification
    econ_class <- read_csv(here::here("source/countries_economies_classification.csv"))

    # Find focus country's region and income group
    focus_row <- econ_class %>%
      filter(Economy == country | str_detect(Economy, fixed(country)))

    if (nrow(focus_row) > 0) {
      focus_region <- focus_row$Region[1]
      focus_income <- focus_row$`Income group`[1]

      # Get countries with same region AND income group
      similar_countries <- econ_class %>%
        filter(Region == focus_region,
                `Income group` == focus_income,
                Economy != country) %>%
        pull(Economy)

      if (length(similar_countries) > 0) {
        nearby_countries_string <- paste(tolower(similar_countries), collapse = "|")
        message(glue("Auto-detected similar countries ({focus_region}, {focus_income}):
{paste(similar_countries, collapse = ', ')}"))
      }
    }
  }, error = function(e) {
    message(glue("Could not auto-detect similar countries: {e$message}"))
  })
}

# Benchmark city selection -------------------------------------------------------------------

nearby_cities <- if (is.null(nearby_countries_string)) NULL else {
    oxford_locations %>%
        subset(str_detect(tolower(Country), nearby_countries_string)) %>%
        subset(Location != Country & !str_detect(Location, "Total")) %>%
        pull(Location)
}

bm_cities_oxford <- if (is.null(nearby_countries_string) || is.null(pop) || nrow(oxford_pop) == 0) NULL else {
    oxford_pop %>%
    subset(str_detect(tolower(Country), nearby_countries_string)) %>%
    subset(Location %in% nearby_cities) %>%
    subset((between(`2021`, pop*.5, pop*1.5) | Country == country) & Location != city) %>%
    pull(Location)
}

# Benchmark cities: use manual selection if defined, otherwise auto-detect from Oxford
bm_cities <- if (length(bm_cities_manual) > 0) {
  bm_cities_manual %>% unique() %>% which_not(city)
} else {
  bm_cities_oxford %>% unique() %>% which_not(city)
}

has_manual_benchmarks <- length(bm_cities_manual) > 0

message(glue("Benchmark cities ({length(bm_cities)}): {paste(bm_cities, collapse = ', ')}"))
message(glue("Manual benchmarks: {has_manual_benchmarks}"))


# Generic sibling scan -----------------------------------------------------------------------
# Scans sibling scan directories for CSV data matching a dataset pattern
# Used by worldpop and ghs tasks to find benchmark city data
#
# dataset_pattern: regex for the CSV filename, e.g. "worldpop_2015_2030" or "ghs_pop"
# year_col / pop_col: column names in the sibling CSV
pop_sibling_scan <- function(cities, country, dataset_pattern = "worldpop_2015_2030",
                             source_label = "WorldPop Global 2",
                             year_col = "year", pop_col = "population") {
  parent_dir <- dirname(here::here())
  sibling_dirs <- list.dirs(parent_dir, full.names = TRUE, recursive = FALSE)

  results <- list()
  found_cities <- character()

  for (ct in cities) {
    # Normalize city name the same way setup.R creates city_string
    ct_normalized <- tolatin(ct) %>% tolower() %>% str_replace_all(" ", "-")
    ct_underscore <- str_replace_all(ct_normalized, "-", "_")

    # Find matching sibling directory (ends with the city string)
    match_dir <- sibling_dirs[str_detect(basename(sibling_dirs),
      paste0("(", ct_normalized, "|", ct_underscore, ")$"))]

    if (length(match_dir) == 0) next
    match_dir <- match_dir[1]

    # Look for CSV matching dataset_pattern
    tabular_path <- file.path(match_dir, "02-process-output", "tabular")
    if (!dir.exists(tabular_path)) next

    csv_files <- list.files(tabular_path, pattern = paste0(dataset_pattern, "\\.csv$"), full.names = TRUE)
    if (length(csv_files) == 0) next

    # Get area from sibling's AOI shapefile
    area_km <- tryCatch({
      sibling_yml <- yaml::read_yaml(file.path(match_dir, "01-user-input", "city_inputs.yml"))
      aoi_shp <- file.path(match_dir, "01-user-input", "AOI", paste0(sibling_yml$AOI_shp_name, ".shp"))
      sibling_aoi <- st_read(aoi_shp, quiet = TRUE) %>% vect()
      round(sum(expanse(sibling_aoi, unit = "km")), 2)
    }, error = function(e) NA_real_)

    result <- tryCatch({
      read.csv(csv_files[1]) %>%
        as_tibble() %>%
        mutate(
          Year = as.numeric(str_extract(.data[[year_col]], "\\d{4}")),
          Population = .data[[pop_col]],
          Location = ct,
          Country = country,
          Area_km = area_km,
          Source = source_label,
          Method = paste0(source_label, " (sibling)"),
          .keep = "none"
        )
    }, error = function(e) NULL)

    if (!is.null(result) && nrow(result) > 0) {
      results[[ct]] <- result
      found_cities <- c(found_cities, ct)
      message("  ", source_label, " from sibling: ", ct, " (", basename(match_dir), ")")
    }
  }

  list(data = bind_rows(results), found_cities = found_cities)
}

# Load benchmark WorldPop functions (UCDB-based G2 population for benchmarks)
source(here::here("core/R/benchmark-worldpop.R"))

message("=== Benchmark selection complete ===\n")
