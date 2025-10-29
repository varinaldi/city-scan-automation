# Download buildings using bing-buildings-csv-to-geojson.py
source("R/setup.R")

get_quadkey <- \(lat, lng, zoom) {
      x <- as.integer((lng + 180) / 360 * (2^zoom))
      y <- as.integer((1 - log(tan(pi/180 * lat) + 1 / cos(pi/180 * lat)) / pi) / 2 * (2^zoom))
      quadkey <- ""
      for (i in seq(zoom, 1, -1)) {
        digit <- 0
        mask <- bitwShiftL(1, i - 1)
        if (bitwAnd(x, mask) != 0) {
          digit <- digit + 1
        }
        if (bitwAnd(y, mask) != 0) {
          digit <- digit + 2
        }
        quadkey <- paste0(quadkey, digit)
      }
      quadkey
}

find_covered_extent <- function(polygon, min_coverage = 0.75, max_iterations = 100, shrink_factor = 0.1, start_extent = NULL) {
  # Check if terra package is available
  if (!requireNamespace("terra", quietly = TRUE)) {
    stop("The terra package is required for this function")
  }
  
  # Input validation
  if (!inherits(polygon, "SpatVector")) {
    stop("Input must be a SpatVector")
  }
  
  if (terra::geomtype(polygon) != "polygons") {
    stop("Input SpatVector must contain polygons")
  }
  # browser()
  # Get initial extent from polygon
  if (!is.null(start_extent)) {
    extent <- start_extent
  } else {
    extent <- terra::ext(polygon)
  }
  
  # Calculate original extent area
  extent_width <- terra::xmax(extent) - terra::xmin(extent)
  extent_height <- terra::ymax(extent) - terra::ymin(extent)
  
  # Create initial extent by expanding the original

  # Binary search approach
  iterations <- 0
  
  while (iterations < max_iterations) {
    iterations <- iterations + 1
    if (iterations %% 10 == 0) {
      message(paste("Iteration:", iterations))
      browser()
    }
    extent_vect <- vect(extent, crs = crs(polygon))
    extent_area <- expanse(extent_vect)
    intersection_area <- sum(expanse(terra::intersect(extent_vect, polygon)))
    coverage <- intersection_area/extent_area

    # If we've achieved the desired coverage, return the extent
    if (coverage >= min_coverage) {
      return(extent)
    }

    # Adjust the extent based on coverage
    extent <- extent - diff(extent[1:2]) * shrink_factor
  }
  
  warning("Maximum iterations reached without finding optimal extent. Returning best result.")
  return(extent)
}

dir <- "/Users/bennotkin/Documents/world-bank/crp/city-scans/city-scan-automation/mnt/2025-04-colombia-cartagena"
subset_box <- vect("/Users/bennotkin/Documents/world-bank/crp/city-scans/city-scan-automation/mnt/2025-04-colombia-cartagena_main/01-user-input/AOI") %>%
  ext() %>%
  grow_extent(-c(.3, .2, .1, .3))

# aoi <- vect(file.path(dir, "01-user-input/AOI"))
aoi <- aggregate(disagg(vect(file.path(dir, "01-user-input/AOI")))[subset_box])
city_string <- str_extract(basename(dir), "[a-z_]*$")

focus <- find_covered_extent(aoi, start_extent = subset_box)
focus <- aspect_buffer(vect(ext(-75.52, -75.48, 10.35, 10.38), crs = crs(aoi)), 1.16, buffer_percent = .5) %>% ext()
# focus <- terra::ext(
#   xmin(focus) + (xmax(focus) - xmin(focus)) / 3,
#   xmax(focus) - (xmax(focus) - xmin(focus)) / 3,
#   ymin(focus), # ymin(focus) + (ymax(focus) - ymin(focus)) / 3,
#   ymax(focus) # ymax(focus) - (ymax(focus) - ymin(focus)) / 3
# )

roads <- fuzzy_read(file.path(dir, "02-process-output/spatial"), "edges-edit.gpkg")[focus]

quadkeys <- unique(apply(geom(vect(focus, crs = crs(aoi))), 1, \(x) get_quadkey(x["y"], x["x"], 9)))
buildings <- lapply(quadkeys, \(x) {
  x <- as.character(as.numeric(x))
  file <- fuzzy_read("~/Documents/world-bank/crp/city-scans/city-scan-automation/frontend/building-tiles", x, paste)
  v <- vect(file, extent = focus)
  return(v)
})
plot(aoi)
buildings <- buildings %>% reduce(rbind)

p <- ggplot() +
  geom_spatvector(data = buildings, color = NA, fill = "#FF9C28") +
  geom_spatvector(data = roads, color = "white", size = 0.0125) +
  theme_void() +
  theme(panel.background = element_rect(fill = "black"))
p

ggsave(filename = file.path(dir, "02-process-output", "images", paste0(city_string, "_city_network_plus_building_footprints.png")), plot = p, width = 8.77, height = 7.55)
 

qk1 <- vect(fuzzy_read("~/Documents/world-bank/crp/city-scans/city-scan-automation/frontend/building-tiles", quadkeys[1], paste))
writeVector(qk1, str_replace(fuzzy_read("~/Documents/world-bank/crp/city-scans/city-scan-automation/frontend/building-tiles", quadkeys[1], paste), "geojson", "fgb"), filetype = "FlatGeobuf")


microbenchmark::microbenchmark(
  test <- vect("/Users/bennotkin/Documents/world-bank/crp/city-scans/city-scan-automation/frontend/building-tiles/ukraine-120330030.fgb", extent = focus),
  test <- vect("/Users/bennotkin/Documents/world-bank/crp/city-scans/city-scan-automation/frontend/building-tiles/ukraine-120330030.geojson", extent = focus),
  times = 5
)