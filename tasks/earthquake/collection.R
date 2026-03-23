# Earthquake data collection
# Sources: NOAA Hazard Service API

if (!exists("aoi")) source(here::here("core/R/setup.R"))

get_earthquake_data <- function() {
  library(httr2)
  resps <- request("http://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/earthquakes") %>%
    req_url_query(minYear = 1900, maxYear = lubridate::year(Sys.Date())) %>%
    req_perform_iterative(iterate_with_offset("page"))
  eq <- resps %>%
    resps_successes() %>%
    resps_data(\(resp) bind_rows(resp_body_json(resp)$items)) %>%
    bind_rows()
    return(eq)
}

eq <- tryCatch(get_earthquake_data(), error = function(e) { message("Earthquake data not available: ", e$message); NULL })

if (!is.null(eq) && nrow(eq) > 0) {
  write_csv(eq, file.path(tabular_dir, paste0(city_string, "_earthquake.csv")))
}
