import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import Point


#  Function to get population data from Oxford dataset
def get_oxford_pop(city_dir, files, years =[2000, 2021], save = True):
    """
    Get Oxford population data for the specified city and country.

    parameters:
    -----------
    city_dir: str
        The city directory string in the format 'mnt/YYYY-MM-country-city'.
    files: dict
        A dictionary containing file paths, including 'oxford_file'.
    years: list
        A list containing the start and end years for population data extraction. 
    save: bool
        If True, save the output to a CSV file; otherwise, return the DataFrame.  
    """

    # Extract country and city from the directory name
    country = city_dir.split('-')[-2].capitalize()
    city = city_dir.split('-')[-1].capitalize()
    
    # Read Oxford Population Data
    oxford_file = pd.read_csv(files['oxford_file'],)

    # Query by country and city name
    pg = oxford_file.query('Indicator == "Total population" & Country == @country & Location == @city')

    # Reshape the DataFrame from wide to long format
    pg = pg.melt(
        id_vars=['Location', 'Country'],
        value_vars=[str(year) for year in range(years[0], years[1]+1)],  
        var_name='Year',
        value_name='Population'
    )

    # Following Caroline's raw data formatting
    pg['Year'] = pg['Year'].astype(int) 
    pg['Population'] = pg['Population'].astype(int) *1000
    pg['Group'] = pg['Location']
    raw_df_pg = pg.copy()[['Group', 'Location', 'Country', 'Year', 'Population' ]]
    raw_df_pg['Source'] = 'Oxford'
    raw_df_pg['Method'] = 'Oxford'

    if save:
        filename = city_dir + '/02-process-output/tabular/' + city.lower() +'_' + 'population-growth.csv'
        raw_df_pg.to_csv(filename, index=False)
        print("Raw population growth data saved to:", filename)
    else:
        return raw_df_pg


# Function to get monthly solar data from global raster using AOI
def get_monthly_pv(city_dir, files, save = True):

    """
    Get PV monthly data from the global raster using AOI .

    parameters:
    -----------
    city_dir: str
        The city directory string in the format 'mnt/YYYY-MM-country-city'.
    files: dict
        A dictionary containing file paths, including 'pv_out_file'.
    save: bool
        If True, save the output to a CSV file; otherwise, return the DataFram  
    """

    city = city_dir.split('-')[-1].lower()

    aoi = gpd.read_file(os.path.join(city_dir, '01-user-input/AOI', city +'.shp') )

    with rasterio.open(files['pv_out_file']) as src:
        # Reproject AOI to match raster CRS if needed
        if aoi.crs != src.crs:
            aoi = aoi.to_crs(src.crs)

        out_image, _ = mask(src, aoi.geometry, crop=True, nodata=np.nan)

        stats = []
        for i in range(out_image.shape[0]):  # Loop through bands
            band_data = out_image[i]
            valid_data = band_data[~np.isnan(band_data)]
            stats.append({
                'month': i + 1,
                'min': np.min(valid_data) if valid_data.size > 0 else np.nan,
                'max': np.max(valid_data) if valid_data.size > 0 else np.nan,
                'mean': np.mean(valid_data) if valid_data.size > 0 else np.nan,
            })

        pv_df = pd.DataFrame(stats)

    if save:
        filename = city_dir + '/02-process-output/tabular/' + city +'_' + 'monthly-pv.csv'
        pv_df.to_csv(filename, index=False)
        print("Raw PV Monthly  data saved to:", filename)
    else:
        return pv_df

        
        
# Function to get raw earthquake events 500km from AOI
def get_earthquake_events(city_dir, files, save = True):

    """
    Get PV monthly data from the global raster using AOI .

    parameters:
    -----------
    city_dir: str
        The city directory string in the format 'mnt/YYYY-MM-country-city'.
    files: dict
        A dictionary containing file paths, including 'earthquake_files'.
    save: bool
        If True, save the output to a CSV file; otherwise, return the DataFram  
    """

    city = city_dir.split('-')[-1].lower()
    aoi = gpd.read_file(os.path.join(city_dir, '01-user-input/AOI', city +'.shp') )

    df = pd.read_csv(files['earthquake_file'])

    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')

    # Use World Azimuthal Equidistant projection centered on AOI
    aoi_centroid = aoi.to_crs('EPSG:4326').geometry.iloc[0].centroid
    aeqd_proj = f'+proj=aeqd +lat_0={aoi_centroid.y} +lon_0={aoi_centroid.x} +x_0=0 +y_0=0 +datum=WGS84 +units=m'

    gdf_proj = gdf.to_crs(aeqd_proj).copy()
    aoi_proj = aoi.to_crs(aeqd_proj).copy()


    # Create 500km buffer and select points within it
    buffer_500km = aoi_proj.buffer(500000)
    nearby_points = gdf_proj[gdf_proj.within(buffer_500km.iloc[0])]

    # Calculate distances from AOI to each point
    nearby_points.loc[:, 'distance_m'] = nearby_points.geometry.apply(
        lambda x: aoi_proj.geometry.distance(x).min()
    )

    # Convert distance to kilometers and reproject back to EPSG:4326
    nearby_points.loc[:, 'distance_km'] = nearby_points.distance(aoi_proj.geometry.iloc[0]) / 1000
    # nearby_points = nearby_points.to_crs('EPSG:4326')


    nearby_points = nearby_points[['year', 'month', 'day', 'eqMagnitude', 'distance_km', 'locationName', 'damageAmountOrder','deaths']]

    # data clearning to get the same format as Caroline's table
    nearby_points['BEGAN'] = pd.to_datetime(
        nearby_points[['year', 'month', 'day']], 
        errors='coerce'
    ).dt.strftime('%Y-%m-%d')


    nearby_points['line1'] = pd.to_datetime(
        nearby_points[['year', 'month']].assign(day=1), 
        errors='coerce'
    ).dt.strftime('%B %Y').str.upper()

    nearby_points['line2'] = nearby_points.apply(
        lambda row: f"M{row['eqMagnitude']}; {int(row['distance_km'])} km away" 
        if pd.notna(row['eqMagnitude']) 
        else f"MNA; {int(row['distance_km'])} km away",
        axis=1
    )

    damage_map = {
        1.0: 'Limited damage',
        2.0: 'Moderate damage',
        3.0: 'Severe damage',
        4.0: 'Extreme damage'
    }
    nearby_points['line3'] = nearby_points['damageAmountOrder'].map(damage_map).fillna('NA damage')


    nearby_points['line4'] = nearby_points.apply(
        lambda row: f"{int(row['deaths'])} fatalities" 
        if pd.notna(row['deaths']) and row['deaths'] > 1
        else f"{int(row['deaths'])} fatality" 
        if pd.notna(row['deaths']) and row['deaths'] == 1
        else '',
        axis=1
    )

    # Create combined text column like in the first table
    nearby_points['text'] = (
        nearby_points['line1'] + '; ' + 
        nearby_points['line2'] + '; ' + 
        nearby_points['line3'] + 
        nearby_points['line4'].apply(lambda x: '; ' + x if x else '')
    )


    nearby_points = nearby_points[['BEGAN', 'text', 'line1', 'line2', 'line3', 'line4', 'distance_km' ,'eqMagnitude', 'locationName']].rename(columns={'distance_km': 'distance','locationName': 'location'})


    if save:
        filename = city_dir + '/02-process-output/tabular/' + city +'_' + 'earthquake-events.csv'
        nearby_points.to_csv(filename, index=False)
        print("Raw earthquake events data saved to:", filename)
    else:
        return nearby_points


# Function to creare pug data once pg and uba are available
def check_raw(city_dir, tabular_dir, spatial_dir, config, files):
    """
    Check if all Raw datasets are present; if not, create the missing tabular ones. Need to figure out if raster ones can be created too.

    parameters:
    -----------
    city_dir: str
        The city directory string in the format 'mnt/YYYY-MM-country-city'.
    tabular_dir: str
        The directory path where tabular datasets are stored.
    spatial_dir: str
        The directory path where spatial datasets are stored.
    config: dict
        A dictionary containing configuration settings, including lists of required 'tabular' and 'raster'
    files: dict
        A dictionary containing file paths, including 'earthquake_files'.  
    """

    city = city_dir.split('-')[-1].lower()
    tabular = [f for f in os.listdir(tabular_dir) if f.endswith('.csv')]
    raster = [f for f in os.listdir( spatial_dir) if f.endswith('.tif')]

    def get_diff(existing, check, config = config, city= city):
        a = {f.replace(city + '_', '').replace('.csv' if check == 'tabular' else '.tif', '') for f in existing}
        c = set(config[check])
        
        return list(c - a)

    missing_tabular = get_diff(tabular, 'tabular')

    missing_raster = get_diff(raster, 'raster') 
    
    if len(missing_tabular)>0:
        print(f"The following tabular datasets are missing: {missing_tabular}")
        print()

        for i in missing_tabular:
            # func = getattr(Py.utils, config['create_raw'][i])
            func = globals()[config['create_raw'][i]]
            func(city_dir, files)

        tabular = [f for f in os.listdir(tabular_dir) if f.endswith('.csv')]

    if len(missing_tabular) == 0:
        print("All tabular datasets are present.")

    if len(missing_raster) == 0:
        print("All raster datasets are present.")


 # regex function to get file by topic
def get_file_by_topic(topic, folder, dir):

    f = [f for f in folder if topic in f.lower()][0]
    filedir = os.path.join(dir, f)

    return filedir

# Function to creare pug data once pg and uba are available
from Py.clean import clean_pug
def create_pug( chart_data_dir ):
    print("Checking prerequisite files...")

    # check if required input files exist
    pg_file = os.path.join(chart_data_dir, 'pg.csv')
    uba_file = os.path.join(chart_data_dir, 'data/processed/uba.csv')

    if os.path.exists(pg_file):
        print(f"Population growth file found: {pg_file}")
    else:
        print(f"Population growth file missing: {pg_file}")
        print("Run clean_pg function first to generate this file")

    if os.path.exists(uba_file):
        print(f"Urban built area file found: {uba_file}")
    else:
        print(f"Urban built area file missing: {uba_file}")
        print("Run clean_uba function first to generate this file")
        
    if os.path.exists(pg_file) and os.path.exists(uba_file):
        print("Both prerequisite files are available. Proceeding to merge and clean population urban growth data...")
        clean_pug()  # uses default paths: pg.csv and uba.csv

    if os.path.exists('data/processed/pug.csv'):
        print("Population urban growth data merged and cleaned successfully!")
    
        