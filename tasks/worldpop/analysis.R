# Population assembly: main city + benchmark cities
# Sources benchmark-helper.R, oxford/datacollection.R, pop-backup.R
# Saves: {city}_pop_benchmark.csv, {city}_density_benchmark.csv
#
if (!exists("aoi")) source(here::here("core/R/setup.R"))
if (!exists("in_oxford")) source(here::here("core/R/benchmark-helper.R"))
if (!exists("get_oxford_pop")) source(here::here("tasks/oxford/collection.R"))
source(here::here("core/R/pop-backup.R"))

message("\n=== Population assembly ===")

# Manual population data if exists
pop_manual <- tryCatch({readr::read_csv("./manual-data-entry/pop.csv", col_types = "ccddc") %>%
  mutate(Method = "Manual")}, error = function(e) tibble())

# AOI area (convert to sf then back to vect, matching pre-charting.R)
aoi_area <- tryCatch(
  round(sum(expanse(aoi %>% st_as_sf() %>% vect(), unit = "km")), 2),
  error = function(e) { message("Could not compute AOI area: ", e$message); NA_real_ })

# WorldPop growth for main city (from own task's CSVs)
wpop_growth <- tryCatch({
  fuzzy_read(tabular_dir, "worldpop_2015_2030.csv", read_csv) %>%
    rename_with(str_to_title) %>%
    mutate(
      Year = as.numeric(str_extract(Year, "\\d{4}")),
      Location = city,
      Country = country,
      Group = city,
      Area_km = aoi_area
    )
}, error = function(e) { message("WorldPop G2 CSV not found: ", e$message); tibble() })

wpop_growth_g1 <- tryCatch({
  fuzzy_read(tabular_dir, "worldpop_2000_2020.csv", read_csv) %>%
    rename_with(str_to_title) %>%
    mutate(
      Year = as.numeric(str_extract(Year, "\\d{4}")),
      Location = city,
      Country = country,
      Group = city,
      Area_km = aoi_area
    )
}, error = function(e) { message("WorldPop G1 CSV not found: ", e$message); tibble() })


# =============================================================================
# assemble_benchmark_pop: assembles population for city + benchmark cities
# =============================================================================

# DUMMY DF
pop_longitude <- tibble()

# Check if WorldPop Global2 available for main city (prioritize over Oxford)
use_wpop_for_city <- nrow(wpop_growth) > 0

# Add WorldPop Global2 for main city if available (priority over Oxford)
if (use_wpop_for_city) {
    message("Using WorldPop Global2 population data for ", city)
    pop_longitude <- pop_longitude %>%
        bind_rows(wpop_growth %>% mutate(Source = "WorldPop Global 2", Method = "WorldPop Global2", Group = city))
}

# Add WorldPop Global1 for main city (separate line on chart)
if (nrow(wpop_growth_g1) > 0) {
    message("Adding WorldPop Global1 population data for ", city)
    pop_longitude <- pop_longitude %>%
        bind_rows(wpop_growth_g1 %>% mutate(Source = "WorldPop Global 1", Method = "WorldPop Global1", Group = city))
}

# Sibling scan for benchmark cities (only if manual benchmarks defined)
bm_cities_no_city <- setdiff(bm_cities, city)
wp_found_cities <- character()
if (has_manual_benchmarks && length(bm_cities_no_city) > 0) {
    message("Looking for WorldPop CSVs in sibling scan directories...")
    wp_siblings <- pop_sibling_scan(bm_cities_no_city, country)
    if (nrow(wp_siblings$data) > 0) {
        pop_longitude <- pop_longitude %>%
            bind_rows(wp_siblings$data %>% mutate(Group = "Benchmark"))
        wp_found_cities <- wp_siblings$found_cities
    }
}

# Population for benchmarks not found via sibling
remaining_bm <- setdiff(bm_cities_no_city, wp_found_cities)

if (in_oxford && !use_wpop_for_city) {
    # City is in Oxford but no WorldPop — use Oxford for city + remaining benchmarks
    oxford_pop_subset <- get_oxford_pop(c(city, remaining_bm))
    if (!is.null(oxford_pop_subset) && nrow(oxford_pop_subset) > 0)
        pop_longitude <- pop_longitude %>% bind_rows(oxford_pop_subset)
} else if (in_oxford) {
    # City uses WorldPop, but benchmarks can use Oxford (same data source)
    oxford_pop_subset <- get_oxford_pop(remaining_bm)
    if (!is.null(oxford_pop_subset) && nrow(oxford_pop_subset) > 0)
        pop_longitude <- pop_longitude %>% bind_rows(oxford_pop_subset)
} else if (length(remaining_bm) > 0) {
    # City NOT in Oxford — use WorldPop G2 for benchmarks too (via UCDB boundaries)
    message("City not in Oxford — downloading WorldPop G2 for benchmark cities...")
    wpop_bm <- tryCatch(
        get_benchmark_worldpop(remaining_bm, oxford_pop),
        error = function(e) { message("WorldPop benchmark download failed: ", e$message); tibble() }
    )
    if (nrow(wpop_bm) > 0) {
        pop_longitude <- pop_longitude %>% bind_rows(wpop_bm)
        wp_found_cities <- c(wp_found_cities, unique(wpop_bm$Location))
    }

    # Oxford fallback for any benchmarks WorldPop couldn't get
    still_remaining <- setdiff(remaining_bm, wp_found_cities)
    if (length(still_remaining) > 0) {
        oxford_pop_subset <- get_oxford_pop(still_remaining)
        if (!is.null(oxford_pop_subset) && nrow(oxford_pop_subset) > 0)
            pop_longitude <- pop_longitude %>% bind_rows(oxford_pop_subset)
    }
}

# Remaining cities not yet in pop_longitude — citypopulation.DE (only for manual benchmarks)
non_oxford_cities <- setdiff(c(city, bm_cities_manual), pop_longitude$Location %>% unique()) %>% .[!duplicated(.)]

if (has_manual_benchmarks && length(non_oxford_cities) > 0) {
    non_oxford_pop <- non_oxford_cities %>%
        lapply(function(x) {
            country_temp <- non_oxford_cities[(non_oxford_cities == x)][1] %>% names()
            if (length(country_temp) != 0) if (country_temp != "") country <- country_temp
            data <- get_de_pop_growth(x, country = country)
            return(data)
            }) %>%
        bind_rows() %>%
        mutate(Location = str_extract(tolatin(Location), tolatin(c(city, bm_cities)) %>%
            paste(collapse = "|")),
                Method = "get_de_pop_growth()",
            Group = case_when(Location == city ~ city, T ~ "Benchmark"))

    pop_longitude <- pop_longitude %>%
        bind_rows(non_oxford_pop)
}


# Final Population data assembly -----------------------------------------------------------------------
if (nrow(pop_longitude) > 0 && "Year" %in% names(pop_longitude)) {

  # add manual data if exists
  if (nrow(pop_manual) > 0) pop_longitude <- bind_rows(pop_longitude, pop_manual) %>%
    filter(!is.na(Population))

  # Final Population data
  if (!"Area_km" %in% names(pop_longitude)) pop_longitude$Area_km <- NA_real_
  pop_longitude <- pop_longitude %>%
    mutate(Area_km = case_when(
           Area_km == 0 ~ NA_real_,
           T ~ Area_km
         )) %>%
    group_by(Year, Location) %>%
    fill(Area_km, Population, Country, .direction = "updown") %>%
    ungroup() %>%
    distinct(Location, Year, Source, .keep_all = T)

  write_csv(pop_longitude, file.path(tabular_dir, paste0(city_string, "_pop_benchmark.csv")))
  message("Saved: _pop_benchmark.csv")

  # Population Density
  target_year <- as.numeric(format(Sys.Date(), "%Y"))
  density <- pop_longitude %>%
      filter(Area_km != 0 & !is.na(Area_km)) %>%
      slice_min(order_by = abs(Year - target_year), by = Location, with_ties = FALSE)
  density$Density <- density$Population/density$Area_km
  density <- density %>% arrange(desc(Density))
  write_csv(density, file.path(tabular_dir, paste0(city_string, "_density_benchmark.csv")))
  message("Saved: _density_benchmark.csv")

  # Population growth (main city only)
  pop_growth <- pop_longitude %>% filter(Group == city) %>% select(-Area_km)
  pop_growth <- arrange(pop_growth, Year)
  write_csv(pop_growth, file.path(tabular_dir, paste0(city_string, "_pop_growth.csv")))
  message("Saved: _pop_growth.csv")

} else {
  message("No population data available — skipping benchmark assembly")
}

# Population density distribution (ridge plot data) -------------------------------------------------------
tryCatch({
  pop_file <- list.files(spatial_dir, pattern = "_population\\.tif$", full.names = TRUE) %>%
    str_subset("dense", negate = TRUE)
  wpop_df <- rast(pop_file[1]) %>%
    as_tibble() %>%
    rename(pop = 1) %>%
    filter(!is.na(pop), pop > 0)
  write_csv(wpop_df, file.path(tabular_dir, paste0(city_string, "_pop_density_pixels.csv")))
  message("Saved: _pop_density_pixels.csv")
}, error = function(e) message("Population raster not available for ridge plot: ", e$message))


message("=== Population assembly complete ===\n")
