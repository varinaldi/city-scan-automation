import ee
import numpy
import xee


# Flatten a geometry to 2D by removing Z coordinates, if present
def flatten_to_2d(geom):
    import shapely
    
    if geom.has_z:
        # If it's a Polygon, handle the exterior and any interiors (holes)
        if geom.geom_type == 'Polygon':
            # Convert to 2D by ignoring the Z coordinate
            new_exterior = [(x, y) for x, y, _ in geom.exterior.coords]
            new_interiors = [[(x, y) for x, y, _ in interior.coords] for interior in geom.interiors]
            return shapely.geometry.Polygon(new_exterior, new_interiors)
        
        # If it's a MultiPolygon, process each Polygon within it
        elif geom.geom_type == 'MultiPolygon':
            new_polygons = []
            for polygon in geom.geoms:
                new_exterior = [(x, y) for x, y, _ in polygon.exterior.coords]
                new_interiors = [[(x, y) for x, y, _ in interior.coords] for interior in polygon.interiors]
                new_polygons.append(shapely.geometry.Polygon(new_exterior, new_interiors))
            return shapely.geometry.MultiPolygon(new_polygons)
    
    # Return the geometry unchanged if it does not have Z coordinates or is not a Polygon/MultiPolygon
    return geom

# returns an ee.Geometry object and its bounds 
def aoi_to_ee_geometry(aoi_file):
    import shapely

    # Conver to 4326
    aoi_file = aoi_file.to_crs(epsg=4326)

    # Remove Z coordinates (convert to 2D)
    aoi_file['geometry'] = aoi_file['geometry'].apply(flatten_to_2d)
    
    AOI = ee.Geometry(shapely.geometry.mapping(aoi_file.unary_union))
    bounds = AOI.bounds()
    
    return AOI, bounds


# simple function to create daterange filter and bounds (for image collection)
def create_criteria(aoi, first_year, last_year):
      return ee.Filter.And(
          ee.Filter.calendarRange(first_year, last_year, 'year'),
          ee.Filter.bounds(aoi)
      )



class Composite:
    """
    Server-side temporal composite for ee.ImageCollection.
    Seasonal month detection uses ERA5-Land and is cached after first call.

    Usage:
        criteria = create_criteria(AOI, 2017, 2024)
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filter(criteria)
        comp = Composite(col, AOI, 2017, 2024)

        comp.monthly('median')
        comp.seasonal('summer', 'median')
        comp.yearly('median')
        comp.period('median')
    """
    def __init__(self, col, aoi, first_year, last_year):
        self.col = col
        self.aoi = aoi
        self.first_year = first_year
        self.last_year = last_year
        self._seasonal_months = {}

    def _reduce(self, img_col, reducer='median'):
        return getattr(img_col, reducer)()

    def _get_seasonal_months(self, season='summer'):
        import xarray as xr

        if season not in self._seasonal_months:
            # Load Era 5 (replacing CRU with ERA5-Land for better spatial resolution and more recent data)
            era5 = ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR') \
                .select('temperature_2m') \
                .filter(create_criteria(self.aoi, self.first_year, self.last_year))

            # load in meemory via xarray and compute monthly averages across the AOI
            ds = xr.open_dataset(era5, engine='ee', geometry=self.aoi, scale=11132,
                                 projection=era5.first().projection())
            
            # compute monthly avereage
            monthly_avg = ds['temperature_2m'].groupby('time.month').mean().mean(dim=['lon', 'lat'])

            #convert to dictionary
            vals = {int(m): float(monthly_avg.sel(month=m)) for m in monthly_avg.month}
            
            # compute 3-month rolling average and find peak month for summer (or trough for winter) 
            avg = {}
            for m in range(1, 13):
                avg[m] = numpy.nanmean([vals[m], vals[m % 12 + 1], vals[(m + 1) % 12 + 1]])

            # find max for summer, min for winter
            peak = max(avg, key=avg.get) if season == 'summer' else min(avg, key=avg.get)
            self._seasonal_months[season] = [peak, peak % 12 + 1, (peak + 1) % 12 + 1]

        return self._seasonal_months[season]

    def monthly(self, reducer='median'):
        months = ee.List.sequence(1, 12)
        return ee.ImageCollection(months.map(lambda m:
            self._reduce(
                self.col.filter(ee.Filter.calendarRange(m, m, 'month')), reducer
            ).set('month', m)
        ))

    def seasonal(self, season='summer', reducer='median'):
        months = self._get_seasonal_months(season)
        return self._reduce(
            self.col.filter(ee.Filter.Or(*[ee.Filter.calendarRange(m, m, 'month') for m in months])),
            reducer
        )

    def yearly(self, reducer='median'):
        years = ee.List.sequence(self.first_year, self.last_year)
        return ee.ImageCollection(years.map(lambda y:
            self._reduce(
                self.col.filter(ee.Filter.calendarRange(y, y, 'year')), reducer
            ).set('system:time_start', ee.Date.fromYMD(y, 1, 1).millis())
              .set('year', y)
        ))

    def period(self, reducer='median'):
        months = ee.List.sequence(1, 12)
        years = ee.List.sequence(self.first_year, self.last_year)
        return ee.ImageCollection(years.map(lambda y:
            months.map(lambda m:
                self._reduce(
                    self.col.filter(ee.Filter.calendarRange(y, y, 'year'))
                           .filter(ee.Filter.calendarRange(m, m, 'month')),
                    reducer
                ).set('system:time_start', ee.Date.fromYMD(y, m, 1).millis())
                  .set('year', y).set('month', m)
            )
        ).flatten())


def to_geotiff(da, output_path, bands=None, resampling=None, aoi=None):
    """
    Export xarray Dataset/DataArray to GeoTIFF via xee_to_rio.

    da: xarray Dataset or DataArray from xr.open_dataset with xee
    output_path: path to save the .tif file
    bands: list of band names to export (Dataset only), e.g. ['B4', 'B3', 'B2']
    resampling: rasterio.enums.Resampling for categorical data (e.g. Resampling.nearest)
    aoi: GeoDataFrame to clip the raster to (optional)
    """
    import rioxarray

    if bands:
        da = da[bands]

    da = xee_to_rio(da, resampling=resampling, aoi=aoi)
    da.rio.to_raster(output_path)
    


def xee_to_rio(da, resampling=None, aoi=None):
    """Convert xee xarray DataArray/Dataset to rasterio-compatible format.
    Handles: time dim drop, transpose to (Y, X), CRS, reproject to 4326, clip to AOI.

    resampling: rasterio.enums.Resampling, use Resampling.nearest for categorical data
    aoi: GeoDataFrame to clip the raster to (optional)
    """
    x_dim = 'X' if 'X' in da.dims else 'lon'
    y_dim = 'Y' if 'Y' in da.dims else 'lat'

    if 'time' in da.dims:
        da = da.isel(time=0).drop_vars('time')

    da = da.transpose(y_dim, x_dim)
    da = da.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim)
    da = da.rio.write_crs('EPSG:3857')

    reproject_kwargs = {'dst_crs': 'EPSG:4326'}
    if resampling:
        reproject_kwargs['resampling'] = resampling
    da = da.rio.reproject(**reproject_kwargs)

    if aoi is not None:
        aoi_4326 = aoi.to_crs("EPSG:4326") if aoi.crs != "EPSG:4326" else aoi
        da = da.rio.clip(aoi_4326.geometry, aoi_4326.crs)

    return da