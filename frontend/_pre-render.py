import os
import yaml
import numpy as np
import pandas as pd

os.getcwd()



# Load City Directory 
city_dir = open('city-dir.txt').readlines()[0].strip()

user_input_dir = os.path.join(city_dir, '01-user-input/')
process_output_dir = os.path.join(city_dir, '02-process-output/')
spatial_dir = os.path.join(process_output_dir, 'spatial/')
tabular_dir = os.path.join(process_output_dir, 'tabular/')

city_name = city_dir.split('-')[-1].lower() 
country_name = city_dir.split('-')[-2].lower()


# Load files for missing files
if not os.path.exists('source/files.yml'):
    raise FileNotFoundError("The 'source/files.yml' file does not exist. Please create it with the necessary file paths.")

else:
    with open('source/files.yml', 'r') as file:
        files = yaml.safe_load(file)



with open('source/pyconfig.yml', 'r') as file:
        config = yaml.safe_load(file)



# Check if we are missing any raw files
import Py.utils

Py.utils.check_raw(city_dir, tabular_dir, spatial_dir,config, files)


# Run cleaning functions
import Py.clean

tabular = [f for f in os.listdir(tabular_dir) if f.endswith('.csv')]

raster = [f for f in os.listdir( spatial_dir) if f.endswith('.tif')]

for key in config['tabular'].keys():
    print()
    print(key)
    filename = Py.utils.get_file_by_topic(key, tabular, tabular_dir)
    func = getattr(Py.clean, config['tabular'][key])
    func(filename)
    print()

Py.utils.create_pug()
print()


for key in config['raster'].keys():

    if 'forest' not in key:
        print()
        print(key)
        filename = Py.utils.get_file_by_topic(key, raster, spatial_dir)
        func = getattr(Py.clean, config['raster'][key])
        func(filename)
        print()

forest_tif_path = Py.utils.get_file_by_topic('forest_cover23.', raster, spatial_dir)

deforestation_tif_path = Py.utils.get_file_by_topic('deforestation.', raster, spatial_dir)

Py.clean.clean_deforestation_area(
    forest_tif_file=forest_tif_path,
    deforestation_tif_file=deforestation_tif_path,
    base_year=2000,
    auto_align=True
)