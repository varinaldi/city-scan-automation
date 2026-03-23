# Benchmark WorldPop: get WorldPop G2 population for benchmark cities
# Uses GHS Urban Centre Database (UCDB) for city boundaries
# Sourced by: benchmark-helper.R
# Requires: setup.R already sourced

message("\n=== benchmark-worldpop.R ===")

# GCS paths (supports /vsicurl/ windowed reads)
UCDB_URL <- "/vsicurl/https://storage.googleapis.com/city-scan-global-public/Urban_Centre_Database/GHS_STAT_UCDB2015MT_GLOBE_R2019A_V1_2.gpkg"
G2_GCS_BASE <- "/vsicurl/https://storage.googleapis.com/city-scan-global-public/world_population/WorldPop-Global-2"

# Direct WorldPop URL (does NOT support range requests — must download full file)
G2_WP_TEMPLATE <- "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/{year}/{ISO}/v1/100m/constrained/{iso}_pop_{year}_CN_100m_R2025A_v1.tif"


get_ucdb_boundary <- function(city_name, country_name = NULL) {
  # Get all cities for the country, then fuzzy match by name in R
  # This handles UCDB using local names (e.g. "Homel" instead of "Gomel")

  if (!is.null(country_name)) {
    query <- glue::glue("SELECT * FROM \"GHS_STAT_UCDB2015MT_GLOBE_R2019A_V1_2\" WHERE CTR_MN_NM = '{country_name}'")
  } else {
    # No country — try exact name match globally
    query <- glue::glue("SELECT * FROM \"GHS_STAT_UCDB2015MT_GLOBE_R2019A_V1_2\" WHERE UC_NM_MN = '{city_name}'")
  }

  all_cities <- tryCatch(
    st_read(UCDB_URL, query = query, quiet = TRUE),
    error = function(e) NULL
  )

  if (is.null(all_cities) || nrow(all_cities) == 0) {
    message("  UCDB: no results for country '", country_name, "'")
    return(NULL)
  }

  # Exact match first
  result <- all_cities %>% filter(UC_NM_MN == city_name)

  # Partial match (city name contained in UCDB name or vice versa)
  if (nrow(result) == 0) {
    city_lower <- tolower(tolatin(city_name))
    result <- all_cities %>%
      filter(str_detect(tolower(tolatin(UC_NM_MN)), fixed(city_lower)) |
             str_detect(city_lower, tolower(tolatin(UC_NM_MN))))
  }

  # Fuzzy match by string distance (handles Gomel→Homel, etc.)
  if (nrow(result) == 0) {
    city_lower <- tolower(tolatin(city_name))
    all_cities <- all_cities %>%
      mutate(.dist = stringdist::stringdist(city_lower, tolower(tolatin(UC_NM_MN)), method = "jw"))
    best <- all_cities %>% slice_min(.dist, n = 1)
    if (best$.dist[1] < 0.25) {
      result <- best %>% select(-.dist)
      message("  UCDB: fuzzy matched '", city_name, "' -> '", result$UC_NM_MN[1],
              "' (dist=", round(best$.dist[1], 3), ")")
    } else {
      all_cities <- all_cities %>% select(-.dist)
    }
  }

  if (nrow(result) == 0) {
    message("  UCDB: no match for '", city_name, "' in ", country_name)
    return(NULL)
  }

  # If multiple matches, pick largest by population
  if (nrow(result) > 1) {
    message("  UCDB: multiple matches for ", city_name, " — using largest")
    result <- result %>% slice_max(P15, n = 1)
  }

  message("  UCDB: matched '", city_name, "' -> '", result$UC_NM_MN[1], "'")
  result
}


get_worldpop_g2_for_city <- function(city_boundary, iso3, years = 2015:2030) {
  # Get WorldPop G2 population for a city boundary
  # Try GCS first (windowed reads), fallback to full download from WorldPop
  iso_lower <- tolower(iso3)
  iso_upper <- toupper(iso3)
  city_vect <- vect(city_boundary)
  results <- list()

  for (yr in years) {
    fname <- paste0(iso_lower, "_pop_", yr, "_CN_100m_R2025A_v1.tif")

    pop <- tryCatch({
      # Try GCS (supports /vsicurl/ windowed reads)
      r <- rast(file.path(G2_GCS_BASE, fname))
      r_crop <- crop(r, city_vect, mask = TRUE)
      sum(values(r_crop), na.rm = TRUE)
    }, error = function(e) {
      # Fallback: download full file from WorldPop (no range request support)
      tryCatch({
        url <- glue::glue(G2_WP_TEMPLATE, year = yr, ISO = iso_upper, iso = iso_lower)
        tmp <- tempfile(fileext = ".tif")
        download.file(url, tmp, mode = "wb", quiet = TRUE)
        r <- rast(tmp)
        r_crop <- crop(r, city_vect, mask = TRUE)
        pop_val <- sum(values(r_crop), na.rm = TRUE)
        unlink(tmp)
        pop_val
      }, error = function(e2) {
        message("    Failed year ", yr, ": ", e2$message)
        NA_real_
      })
    })

    results[[as.character(yr)]] <- pop
  }

  tibble(
    Year = as.numeric(names(results)),
    Population = round(unlist(results))
  ) %>% filter(!is.na(Population))
}


get_benchmark_worldpop <- function(cities, oxford_pop_df = NULL) {
  # For each benchmark city:
  #   1. Look up country from Oxford data
  #   2. Get UCDB boundary
  #   3. Download WorldPop G2 and sum population per year
  # Returns tibble matching pop_longitude format

  all_results <- list()

  for (ct in cities) {
    message("  Processing benchmark: ", ct)

    # Get country from Oxford data
    ct_country <- NULL
    if (!is.null(oxford_pop_df) && nrow(oxford_pop_df) > 0) {
      ct_row <- oxford_pop_df %>% filter(Location == ct)
      if (nrow(ct_row) > 0) ct_country <- ct_row$Country[1]
    }

    # Get UCDB boundary
    boundary <- get_ucdb_boundary(ct, ct_country)
    if (is.null(boundary)) next

    iso3 <- boundary$CTR_MN_ISO[1]
    area_km <- boundary$AREA[1]
    ct_country <- if (!is.null(ct_country)) ct_country else boundary$CTR_MN_NM[1]

    message("    ISO3: ", iso3, " | Area: ", area_km, " km²")

    # Get WorldPop G2 population
    pop_data <- tryCatch(
      get_worldpop_g2_for_city(boundary, iso3),
      error = function(e) {
        message("    WorldPop G2 failed for ", ct, ": ", e$message)
        tibble()
      }
    )

    if (nrow(pop_data) == 0) next

    pop_data <- pop_data %>%
      mutate(
        Location = ct,
        Country = ct_country,
        Area_km = area_km,
        Source = "WorldPop Global 2",
        Method = "WorldPop G2 (UCDB AOI)",
        Group = "Benchmark"
      )

    all_results[[ct]] <- pop_data
    message("    OK: ", nrow(pop_data), " years, latest pop = ",
            scales::comma(tail(pop_data$Population, 1)))
  }

  if (length(all_results) == 0) return(tibble())
  bind_rows(all_results)
}

message("=== benchmark-worldpop.R loaded ===\n")
