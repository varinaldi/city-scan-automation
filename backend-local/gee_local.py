"""
GEE Functions for Local Processing (Task 16)
All exports go to Google Drive folder 'city-scan-outputs'
Download files manually and move to your mnt/ city folder
"""

import ee

def flatten_to_2d(geom):
    import shapely

    if geom.has_z:
        if geom.geom_type == 'Polygon':
            new_exterior = [(x, y) for x, y, _ in geom.exterior.coords]
            new_interiors = [[(x, y) for x, y, _ in interior.coords] for interior in geom.interiors]
            return shapely.geometry.Polygon(new_exterior, new_interiors)
        elif geom.geom_type == 'MultiPolygon':
            new_polygons = []
            for polygon in geom.geoms:
                new_exterior = [(x, y) for x, y, _ in polygon.exterior.coords]
                new_interiors = [[(x, y) for x, y, _ in interior.coords] for interior in polygon.interiors]
                new_polygons.append(shapely.geometry.Polygon(new_exterior, new_interiors))
            return shapely.geometry.MultiPolygon(new_polygons)

    return geom

def aoi_to_ee_geometry(aoi_file):
    import shapely
    aoi_file['geometry'] = aoi_file['geometry'].apply(flatten_to_2d)
    AOI = ee.Geometry(shapely.geometry.mapping(aoi_file.unary_union))
    return AOI

def gee_forest(city_name_l, aoi_file):
    """Export forest cover to Google Drive"""
    print('Running gee_forest - exporting to Google Drive...')

    AOI = aoi_to_ee_geometry(aoi_file)
    fc = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")

    no_data_val = 0

    deforestation0023 = fc.select('loss').eq(1).clip(AOI).unmask(value=no_data_val, sameFootprint=False).rename('fcloss0023')
    forestCover00 = fc.select('treecover2000').gte(20).clip(AOI)
    forestCoverGain0012 = fc.select('gain').eq(1).clip(AOI)
    forestCover23 = forestCover00.subtract(deforestation0023).add(forestCoverGain0012).gte(1).rename('fc23').unmask(value=no_data_val, sameFootprint=False)
    deforestation_year = fc.select('lossyear').clip(AOI).unmask(value=no_data_val, sameFootprint=False)

    # Export to Google Drive - organized by city folder
    task0 = ee.batch.Export.image.toDrive(**{
        'image': forestCover23,
        'description': f'{city_name_l}_forest_cover23',
        'region': AOI,
        'scale': 30.92,
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_forest_cover23',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task0.start()

    task1 = ee.batch.Export.image.toDrive(**{
        'image': deforestation_year,
        'description': f'{city_name_l}_deforestation',
        'region': AOI,
        'scale': 30.92,
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_deforestation',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task1.start()

    print(f"✓ Tasks started: {city_name_l}_forest_cover23, {city_name_l}_deforestation")
    print(f"  Files will be saved to Google Drive: city-scan-outputs/{city_name_l}/")
    print("  Check https://code.earthengine.google.com/tasks for progress")

def gee_ndvi(city_name_l, aoi_file, first_year, last_year):
    """Export NDVI to Google Drive - MATCHES backend/gee_fun.py gee_ndxi"""
    print('Running gee_ndvi - exporting to Google Drive...')

    AOI = aoi_to_ee_geometry(aoi_file)

    # Cloud mask function for Sentinel-2 (from backend)
    def maskS2clouds(image):
        qa = image.select('QA60')
        cloudBitMask = 1 << 10
        cirrusBitMask = 1 << 11
        mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
        return image.updateMask(mask).divide(10000)

    # Get Sentinel-2 collection (matching backend)
    no_data_val = -9999
    s2 = ee.ImageCollection('COPERNICUS/S2_HARMONIZED') \
        .filterBounds(AOI) \
        .filterDate(f'{first_year}-06-01', f'{last_year}-09-01') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
        .map(maskS2clouds)

    s2_median = s2.median().clip(AOI).unmask(value=no_data_val, sameFootprint=False)

    # Calculate NDVI using Sentinel-2 bands (B8=NIR, B4=Red)
    ndvi_median = s2_median.normalizedDifference(['B8', 'B4']).rename('NDVI')

    # Export - MATCHING layers.yml pattern: ndvi_season.*.tif$
    task = ee.batch.Export.image.toDrive(**{
        'image': ndvi_median,
        'description': f'{city_name_l}_ndvi_season',
        'region': AOI,
        'scale': 10,  # Sentinel-2 resolution
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_ndvi_season',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task.start()

    print(f"✓ Task started: {city_name_l}_ndvi_season")
    print(f"  Files will be saved to Google Drive: city-scan-outputs/{city_name_l}/")
    print("  Check https://code.earthengine.google.com/tasks for progress")

def gee_landcover(city_name_l, aoi_file):
    """Export landcover to Google Drive"""
    print('Running gee_landcover - exporting to Google Drive...')

    AOI = aoi_to_ee_geometry(aoi_file)

    # Get ESA WorldCover 2021
    lc = ee.ImageCollection("ESA/WorldCover/v200").first()
    lc_aoi = lc.clip(AOI)

    # Export - MATCHING layers.yml pattern: lc.tif$
    task = ee.batch.Export.image.toDrive(**{
        'image': lc_aoi,
        'description': f'{city_name_l}_lc',
        'region': AOI,
        'scale': 10,
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_lc',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task.start()

    print(f"✓ Task started: {city_name_l}_lc")
    print(f"  Files will be saved to Google Drive: city-scan-outputs/{city_name_l}/")
    print("  Check https://code.earthengine.google.com/tasks for progress")

def gee_lst_summer(city_name_l, aoi_file, first_year, last_year):
    """Export summer LST to Google Drive - MATCHES backend/gee_fun.py"""
    print('Running gee_lst_summer - exporting to Google Drive...')

    AOI = aoi_to_ee_geometry(aoi_file)

    # Use Landsat 8 (matching backend exactly)
    landsat = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")

    # Cloud mask function (from backend)
    def maskL457sr(image):
        qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
        saturationMask = image.select('QA_RADSAT').eq(0)
        # Apply scaling factors to thermal band
        thermalBand = image.select('ST_B10').multiply(0.00341802).add(149.0)
        return image.addBands(thermalBand, None, True).updateMask(qaMask).updateMask(saturationMask)

    # Summer months (simplified - using Jun-Aug)
    date_filter = ee.Filter.calendarRange(6, 8, 'month')

    # Process: filter, mask, calculate mean LST in Celsius
    no_data_val = -9999
    lst_mean = landsat \
        .filterBounds(AOI) \
        .filterDate(f'{first_year}-01-01', f'{last_year+1}-01-01') \
        .filter(date_filter) \
        .map(maskL457sr) \
        .select('ST_B10') \
        .mean() \
        .add(-273.15) \
        .clip(AOI) \
        .unmask(value=no_data_val, sameFootprint=False)

    # Export
    task = ee.batch.Export.image.toDrive(**{
        'image': lst_mean,
        'description': f'{city_name_l}_summer',
        'region': AOI,
        'scale': 100,  # Landsat resolution
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_summer',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task.start()

    print(f"✓ Task started: {city_name_l}_summer")
    print(f"  Files will be saved to Google Drive: city-scan-outputs/{city_name_l}/")
    print("  Check https://code.earthengine.google.com/tasks for progress")

def gee_lst_winter(city_name_l, aoi_file, first_year, last_year):
    """Export winter LST to Google Drive - MATCHES backend/gee_fun.py"""
    print('Running gee_lst_winter - exporting to Google Drive...')

    AOI = aoi_to_ee_geometry(aoi_file)

    # Use Landsat 8 (matching backend exactly)
    landsat = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")

    # Cloud mask function (from backend)
    def maskL457sr(image):
        qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
        saturationMask = image.select('QA_RADSAT').eq(0)
        # Apply scaling factors to thermal band
        thermalBand = image.select('ST_B10').multiply(0.00341802).add(149.0)
        return image.addBands(thermalBand, None, True).updateMask(qaMask).updateMask(saturationMask)

    # Winter months (simplified - using Dec-Feb)
    date_filter = ee.Filter.calendarRange(12, 2, 'month')

    # Process: filter, mask, calculate mean LST in Celsius
    no_data_val = -9999
    lst_mean = landsat \
        .filterBounds(AOI) \
        .filterDate(f'{first_year}-01-01', f'{last_year+1}-01-01') \
        .filter(date_filter) \
        .map(maskL457sr) \
        .select('ST_B10') \
        .mean() \
        .add(-273.15) \
        .clip(AOI) \
        .unmask(value=no_data_val, sameFootprint=False)

    # Export
    task = ee.batch.Export.image.toDrive(**{
        'image': lst_mean,
        'description': f'{city_name_l}_winter',
        'region': AOI,
        'scale': 100,  # Landsat resolution
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_winter',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task.start()

    print(f"✓ Task started: {city_name_l}_winter")
    print(f"  Files will be saved to Google Drive: city-scan-outputs/{city_name_l}/")
    print("  Check https://code.earthengine.google.com/tasks for progress")

def gee_ndmi(city_name_l, aoi_file, first_year, last_year):
    """Export NDMI to Google Drive - MATCHES backend/gee_fun.py gee_ndxi"""
    print('Running gee_ndmi - exporting to Google Drive...')

    AOI = aoi_to_ee_geometry(aoi_file)

    # Cloud mask function for Sentinel-2 (from backend)
    def maskS2clouds(image):
        qa = image.select('QA60')
        cloudBitMask = 1 << 10
        cirrusBitMask = 1 << 11
        mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
        return image.updateMask(mask).divide(10000)

    # Get Sentinel-2 collection (matching backend)
    no_data_val = -9999
    s2 = ee.ImageCollection('COPERNICUS/S2_HARMONIZED') \
        .filterBounds(AOI) \
        .filterDate(f'{first_year}-06-01', f'{last_year}-09-01') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
        .map(maskS2clouds)

    s2_median = s2.median().clip(AOI).unmask(value=no_data_val, sameFootprint=False)

    # Calculate NDMI using Sentinel-2 bands (B8=NIR, B11=SWIR)
    ndmi_median = s2_median.normalizedDifference(['B8', 'B11']).rename('NDMI')

    # Export - MATCHING layers.yml pattern: ndmi_season.*.tif$
    task = ee.batch.Export.image.toDrive(**{
        'image': ndmi_median,
        'description': f'{city_name_l}_ndmi_season',
        'region': AOI,
        'scale': 30,
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_ndmi_season',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task.start()

    print(f"✓ Task started: {city_name_l}_ndmi_season")
    print(f"  Files will be saved to Google Drive: city-scan-outputs/{city_name_l}/")
    print("  Check https://code.earthengine.google.com/tasks for progress")

def gee_nightlight(city_name_l, aoi_file):
    """Export nightlight data to Google Drive (2 outputs: avg_rad_sum and linfit)"""
    print('Running gee_nightlight - exporting to Google Drive...')

    AOI = aoi_to_ee_geometry(aoi_file)

    # Get VIIRS nightlight collection (last 10 years)
    viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG')
    max_date = viirs.reduceColumns(ee.Reducer.max(), ["system:time_start"]).get('max')
    NTL_time = ee.DateRange(ee.Date(max_date.getInfo()).advance(-10, 'year'), ee.Date(max_date.getInfo()))

    # Function to add time band
    def addTime(image):
        return image.addBands(image.metadata('system:time_start').divide(1000 * 60 * 60 * 24 * 365))

    viirs_with_time = viirs.filterDate(NTL_time).map(addTime)

    # Calculate linear fit (for economic_change: linfit.tif$)
    linear_fit = viirs_with_time.select(['system:time_start', 'avg_rad']).reduce(ee.Reducer.linearFit()).clip(AOI)

    # Calculate sum of light (for economic_activity: avg_rad_sum.*.tif$)
    sum_of_light = viirs_with_time.select(['system:time_start', 'avg_rad']).reduce(ee.Reducer.sum()).clip(AOI)

    # Export 1: linfit - MATCHING layers.yml pattern: linfit.tif$
    task1 = ee.batch.Export.image.toDrive(**{
        'image': linear_fit.select('scale'),
        'description': f'{city_name_l}_linfit',
        'region': AOI,
        'scale': 463.83,
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_linfit',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task1.start()

    # Export 2: avg_rad_sum - MATCHING layers.yml pattern: avg_rad_sum.*.tif$
    task2 = ee.batch.Export.image.toDrive(**{
        'image': sum_of_light.select('avg_rad_sum'),
        'description': f'{city_name_l}_avg_rad_sum',
        'region': AOI,
        'scale': 463.83,
        'folder': f'city-scan-outputs/{city_name_l}',
        'fileNamePrefix': f'{city_name_l}_avg_rad_sum',
        'maxPixels': 1e10,
        'fileFormat': 'GeoTIFF'
    })
    task2.start()

    print(f"✓ Tasks started: {city_name_l}_linfit, {city_name_l}_avg_rad_sum")
    print(f"  Files will be saved to Google Drive: city-scan-outputs/{city_name_l}/")
    print("  Check https://code.earthengine.google.com/tasks for progress")
