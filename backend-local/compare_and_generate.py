"""
Compare city data to reference and generate missing files

This script:
1. Compares spatial and tabular files to a reference city
2. Generates a summary YAML of missing/available data
3. Creates missing tabular files (when source data exists)
4. Skips files when source datasets are missing

Usage:
    cd mnt/2025-10-senegal-dakar/
    python ../../backend-local/compare_and_generate.py --reference sofifi
"""

import os
import sys
import yaml
import argparse
import pandas as pd
import geopandas as gpd
import rasterio
import numpy as np
from pathlib import Path
from datetime import datetime

class CityDataComparator:
    def __init__(self, city_dir, reference_city_name):
        self.city_dir = city_dir
        self.city_name = os.path.basename(city_dir)

        # Extract city_name_l (e.g., "dakar" from "2025-10-senegal-dakar")
        parts = self.city_name.split('-')
        if len(parts) >= 4:
            self.city_name_l = parts[3]
        else:
            raise ValueError("City directory name must be in format: YYYY-MM-country-city")

        # Set directories
        self.process_output_dir = os.path.join(city_dir, '02-process-output')
        self.spatial_dir = os.path.join(self.process_output_dir, 'spatial')
        self.tabular_dir = os.path.join(self.process_output_dir, 'tabular')

        # Find reference city
        mnt_dir = os.path.dirname(city_dir)
        ref_dirs = [d for d in os.listdir(mnt_dir)
                   if reference_city_name in d and os.path.isdir(os.path.join(mnt_dir, d))]

        if not ref_dirs:
            raise ValueError(f"Reference city '{reference_city_name}' not found in {mnt_dir}")

        ref_city_dir = os.path.join(mnt_dir, ref_dirs[0])
        self.ref_spatial_dir = os.path.join(ref_city_dir, '02-process-output', 'spatial')
        self.ref_tabular_dir = os.path.join(ref_city_dir, '02-process-output', 'tabular')
        self.reference_city_name_l = reference_city_name

        print(f"📍 Current City: {self.city_name_l}")
        print(f"📌 Reference City: {self.reference_city_name_l}")

    def normalize_filename(self, filename, city_name_l):
        """Remove city prefix from filename for comparison"""
        # Remove city name prefix
        if filename.startswith(f"{city_name_l}_"):
            return filename[len(city_name_l)+1:]
        return filename

    def get_file_list(self, directory, city_name_l):
        """Get normalized file list from directory"""
        if not os.path.exists(directory):
            return set()

        files = os.listdir(directory)
        # Filter out system files
        files = [f for f in files if not f.startswith('.')]
        # Normalize filenames
        normalized = {self.normalize_filename(f, city_name_l) for f in files}
        return normalized

    def compare_directories(self):
        """Compare spatial and tabular directories"""
        print("\n" + "="*70)
        print("📊 COMPARING DATA TO REFERENCE")
        print("="*70)

        # Get file lists
        ref_spatial = self.get_file_list(self.ref_spatial_dir, self.reference_city_name_l)
        ref_tabular = self.get_file_list(self.ref_tabular_dir, self.reference_city_name_l)

        curr_spatial = self.get_file_list(self.spatial_dir, self.city_name_l)
        curr_tabular = self.get_file_list(self.tabular_dir, self.city_name_l)

        # Find differences
        missing_spatial = sorted(ref_spatial - curr_spatial)
        missing_tabular = sorted(ref_tabular - curr_tabular)
        extra_spatial = sorted(curr_spatial - ref_spatial)
        extra_tabular = sorted(curr_tabular - ref_tabular)
        common_spatial = sorted(ref_spatial & curr_spatial)
        common_tabular = sorted(ref_tabular & curr_tabular)

        # Create summary
        summary = {
            'comparison_date': datetime.now().isoformat(),
            'current_city': self.city_name_l,
            'reference_city': self.reference_city_name_l,
            'spatial': {
                'available': list(common_spatial),
                'missing': list(missing_spatial),
                'extra': list(extra_spatial),
                'stats': {
                    'total_in_reference': len(ref_spatial),
                    'total_in_current': len(curr_spatial),
                    'common': len(common_spatial),
                    'missing': len(missing_spatial),
                    'extra': len(extra_spatial)
                }
            },
            'tabular': {
                'available': list(common_tabular),
                'missing': list(missing_tabular),
                'extra': list(extra_tabular),
                'stats': {
                    'total_in_reference': len(ref_tabular),
                    'total_in_current': len(curr_tabular),
                    'common': len(common_tabular),
                    'missing': len(missing_tabular),
                    'extra': len(extra_tabular)
                }
            }
        }

        # Print summary
        print(f"\n📂 SPATIAL FILES:")
        print(f"   ✅ Available: {len(common_spatial)}/{len(ref_spatial)}")
        print(f"   ❌ Missing: {len(missing_spatial)}")
        print(f"   ➕ Extra: {len(extra_spatial)}")

        print(f"\n📄 TABULAR FILES:")
        print(f"   ✅ Available: {len(common_tabular)}/{len(ref_tabular)}")
        print(f"   ❌ Missing: {len(missing_tabular)}")
        print(f"   ➕ Extra: {len(extra_tabular)}")

        if missing_spatial:
            print(f"\n❌ Missing Spatial Files:")
            for f in missing_spatial:
                print(f"   - {f}")

        if missing_tabular:
            print(f"\n❌ Missing Tabular Files:")
            for f in missing_tabular:
                print(f"   - {f}")

        # Save summary
        summary_file = os.path.join(self.city_dir, 'data_comparison_summary.yml')
        with open(summary_file, 'w') as f:
            yaml.dump(summary, f, default_flow_style=False, sort_keys=False)

        print(f"\n💾 Summary saved to: data_comparison_summary.yml")

        return summary

    def generate_missing_tabular(self, summary):
        """Generate missing tabular files (when source data exists)"""
        print("\n" + "="*70)
        print("🔧 GENERATING MISSING TABULAR FILES")
        print("="*70)

        missing_tabular = summary['tabular']['missing']

        if not missing_tabular:
            print("\n✨ No missing tabular files!")
            return

        generated = []
        skipped = []

        for filename in missing_tabular:
            # Determine what needs to be generated
            if 'demographics_summary.yml' in filename:
                result = self.generate_demographics_summary()
            elif filename == 'lc.csv':
                result = self.generate_landcover_csv()
            elif filename == 'lc_stats.yml':
                result = self.generate_landcover_stats()
            elif filename == 'flood_wsf.csv':
                result = self.generate_flood_wsf_stats()
            elif filename == 'flood_pop.csv':
                result = self.generate_flood_pop_stats()
            elif filename == 'flood_road.csv':
                result = self.generate_flood_road_stats()
            elif filename == 'flood_osm.csv':
                result = self.generate_flood_osm_stats()
            elif 'hottest_months.txt' in filename or 'coldest_months.txt' in filename:
                # These are generated by GEE functions, skip
                skipped.append({'file': filename, 'reason': 'Generated by GEE functions'})
                result = False
            else:
                skipped.append({'file': filename, 'reason': 'Unknown file type'})
                result = False

            if result:
                generated.append(filename)
            elif result is False and filename not in [s['file'] for s in skipped]:
                skipped.append({'file': filename, 'reason': 'Source data missing'})

        # Update summary with generation results
        summary['generation_results'] = {
            'generated': generated,
            'skipped': skipped,
            'stats': {
                'attempted': len(missing_tabular),
                'generated': len(generated),
                'skipped': len(skipped)
            }
        }

        # Save updated summary
        summary_file = os.path.join(self.city_dir, 'data_comparison_summary.yml')
        with open(summary_file, 'w') as f:
            yaml.dump(summary, f, default_flow_style=False, sort_keys=False)

        print(f"\n📊 Generation Results:")
        print(f"   ✅ Generated: {len(generated)}")
        print(f"   ⏭️  Skipped: {len(skipped)}")

        if skipped:
            print(f"\n⏭️  Skipped Files:")
            for item in skipped:
                print(f"   - {item['file']}: {item['reason']}")

    # Generation methods
    def generate_demographics_summary(self):
        """Generate demographics_summary.yml from demographics.csv"""
        print(f"\n📊 Generating {self.city_name_l}_demographics_summary.yml...")

        demographics_csv = os.path.join(self.tabular_dir, f'{self.city_name_l}_demographics.csv')

        if not os.path.exists(demographics_csv):
            print(f"   ⏭️  Source missing: {self.city_name_l}_demographics.csv")
            return False

        try:
            df = pd.read_csv(demographics_csv)

            # Normalize column names (handle both formats)
            df.columns = df.columns.str.lower()

            # Rename to standard format
            column_mapping = {
                'age_group': 'Age_Bracket',
                'sex': 'Sex',
                'population': 'Count'
            }
            df = df.rename(columns=column_mapping)

            # Map age groups to standard brackets
            # 0-1 and 1-4 combine to 0-4
            age_mapping = {
                '0-1': '0-4',
                '1-4': '0-4',
                '5-9': '5-9',
                '10-14': '10-14',
                '15-19': '15-19',
                '20-24': '20-24',
                '25-29': '25-29',
                '30-34': '30-34',
                '35-39': '35-39',
                '40-44': '40-44',
                '45-49': '45-49',
                '50-54': '50-54',
                '55-59': '55-59',
                '60-64': '60-64',
                '65-69': '65-69',
                '70-74': '70-74',
                '75-79': '75-79',
                '80+': '80+'
            }

            df['Age_Bracket'] = df['Age_Bracket'].map(age_mapping)

            # Calculate summary statistics
            pop_dist = df.groupby(['Age_Bracket', 'Sex'])['Count'].sum().reset_index()
            total_pop = pop_dist['Count'].sum()
            pop_dist['Percentage'] = (pop_dist['Count'] / total_pop * 100)

            male_total = pop_dist[pop_dist['Sex'] == 'm']['Count'].sum()
            female_total = pop_dist[pop_dist['Sex'] == 'f']['Count'].sum()

            pop_dist['Sexed_Percent'] = pop_dist.apply(
                lambda row: (row['Count'] / male_total * 100) if row['Sex'] == 'm'
                            else (row['Count'] / female_total * 100),
                axis=1
            )

            under5 = pop_dist[pop_dist['Age_Bracket'] == '0-4']['Percentage'].sum()
            youth = pop_dist[pop_dist['Age_Bracket'].isin(['15-19', '20-24'])]['Percentage'].sum()
            working_age_brackets = ['15-19','20-24','25-29','30-34','35-39','40-44','45-49','50-54','55-59','60-64']
            working_age = pop_dist[pop_dist['Age_Bracket'].isin(working_age_brackets)]['Percentage'].sum()
            elderly = pop_dist[pop_dist['Age_Bracket'].isin(['60-64', '65-69', '70-74', '75-79', '80+'])]['Percentage'].sum()

            male_count = pop_dist[pop_dist['Sex'] == 'm']['Count'].sum()
            female_count = pop_dist[pop_dist['Sex'] == 'f']['Count'].sum()
            sex_ratio = male_count / female_count * 100 if female_count > 0 else 0

            reproductive_age = pop_dist[
                (pop_dist['Sex'] == 'f') &
                (pop_dist['Age_Bracket'].isin(['15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49']))
            ]['Sexed_Percent'].sum()

            summary_data = {
                'under5': f"{under5:.2f}%",
                'youth (15-24)': f"{youth:.2f}%",
                'working_age (15-64)': f"{working_age:.2f}%",
                'elderly (60+)': f"{elderly:.2f}%",
                'reproductive_age, percent of women (15-49)': f"{reproductive_age:.2f}%",
                'sex_ratio': f"{round(sex_ratio, 2)} males to 100 females"
            }

            output_file = os.path.join(self.tabular_dir, f'{self.city_name_l}_demographics_summary.yml')
            with open(output_file, 'w') as f:
                yaml.dump(summary_data, f, default_flow_style=False)

            print(f"   ✅ Generated {self.city_name_l}_demographics_summary.yml")
            return True

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    def generate_landcover_csv(self):
        """Generate lc.csv from land cover raster"""
        print(f"\n🌍 Generating {self.city_name_l}_lc.csv...")

        lc_files = [f for f in os.listdir(self.spatial_dir) if f.endswith('_lc.tif')]
        if not lc_files:
            print(f"   ⏭️  Source missing: land cover raster")
            return False

        try:
            lc_file = os.path.join(self.spatial_dir, lc_files[0])

            class_values = {
                10: 'Tree cover', 20: 'Shrubland', 30: 'Grassland',
                40: 'Cropland', 50: 'Built-up', 60: 'Bare / sparse vegetation',
                70: 'Snow and ice', 80: 'Permanent water bodies',
                90: 'Herbaceous wetland', 95: 'Mangroves', 100: 'Moss and lichen'
            }

            with rasterio.open(lc_file) as src:
                data = src.read(1)
                unique, counts = np.unique(data[data > 0], return_counts=True)

            counts_dict = {}
            for class_val in class_values:
                idx = np.where(unique == class_val)[0]
                count = int(counts[idx[0]]) if len(idx) > 0 else 0
                if count > 0:
                    counts_dict[class_values[class_val]] = count

            lc_csv = os.path.join(self.tabular_dir, f'{self.city_name_l}_lc.csv')
            with open(lc_csv, 'w') as f:
                f.write('Land Cover Type,Pixel Count\n')
                for class_name, count in counts_dict.items():
                    f.write(f'{class_name},{count}\n')

            print(f"   ✅ Generated {self.city_name_l}_lc.csv")
            return True

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    def generate_landcover_stats(self):
        """Generate lc_stats.yml from lc.csv"""
        print(f"\n🌍 Generating {self.city_name_l}_lc_stats.yml...")

        lc_csv = os.path.join(self.tabular_dir, f'{self.city_name_l}_lc.csv')

        if not os.path.exists(lc_csv):
            print(f"   ⏭️  Source missing: {self.city_name_l}_lc.csv (run lc.csv generation first)")
            return False

        try:
            df = pd.read_csv(lc_csv)
            total_pixels = df['Pixel Count'].sum()
            df['Percentage'] = (df['Pixel Count'] / total_pixels * 100)
            df = df.sort_values('Percentage', ascending=False)

            top3 = df.head(3)
            ordinals = ['first', 'second', 'third']
            lc_text_dict = {}

            for i, (idx, row) in enumerate(top3.iterrows()):
                ordinal = ordinals[i]
                text = f"The {ordinal} highest landcover value is {row['Land Cover Type']} with {row['Percentage']:.2f}% of the total land area"
                if i == 0:
                    text = text.replace('first ', '')
                lc_text_dict[ordinal] = text

            lc_stats_yml = os.path.join(self.tabular_dir, f'{self.city_name_l}_lc_stats.yml')
            with open(lc_stats_yml, 'w') as f:
                yaml.dump(lc_text_dict, f, default_flow_style=False)

            print(f"   ✅ Generated {self.city_name_l}_lc_stats.yml")
            return True

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    def generate_flood_wsf_stats(self):
        """Generate flood_wsf.csv"""
        print(f"\n🌊 Generating {self.city_name_l}_flood_wsf.csv...")

        wsf_file = os.path.join(self.spatial_dir, f'{self.city_name_l}_wsf_evolution_utm.tif')
        if not os.path.exists(wsf_file):
            print(f"   ⏭️  Source missing: WSF evolution data")
            return False

        flood_types = ['fluvial', 'pluvial', 'coastal', 'combined_flooding']
        available_floods = [ft for ft in flood_types
                          if any(ft in f and f.endswith('_2020.tif')
                                for f in os.listdir(self.spatial_dir))]

        if not available_floods:
            print(f"   ⏭️  Source missing: Flood rasters")
            return False

        try:
            rows = []

            for ft in available_floods:
                flood_files = [f for f in os.listdir(self.spatial_dir)
                              if ft in f and f.endswith('_2020.tif') and 'utm' not in f]
                if not flood_files:
                    continue

                flood_file = os.path.join(self.spatial_dir, flood_files[0])

                with rasterio.open(wsf_file) as wsf:
                    wsf_array = wsf.read(1)
                    pixel_area = abs(wsf.res[0] * wsf.res[1]) / 1e6

                    import rasterio.warp as warp
                    with rasterio.open(flood_file) as flood_src:
                        flood_array = np.zeros(wsf_array.shape)
                        warp.reproject(
                            source=flood_src.read(1),
                            destination=flood_array,
                            src_transform=flood_src.transform,
                            src_crs=flood_src.crs,
                            dst_transform=wsf.transform,
                            dst_crs=wsf.crs,
                            resampling=warp.Resampling.nearest
                        )

                    for year in range(1985, 2016):
                        exposed = np.sum((wsf_array <= year) & (wsf_array > 0) & (flood_array > 0))
                        exposed_sqkm = exposed * pixel_area
                        rows.append([year, f'{ft}_2020', exposed_sqkm])

            if rows:
                df = pd.DataFrame(rows, columns=['year', 'type', 'exposed_built_up_sqkm'])
                df_pivot = df.pivot(index='year', columns='type', values='exposed_built_up_sqkm')
                output_file = os.path.join(self.tabular_dir, f'{self.city_name_l}_flood_wsf.csv')
                df_pivot.to_csv(output_file)
                print(f"   ✅ Generated {self.city_name_l}_flood_wsf.csv")
                return True

            return False

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    def generate_flood_pop_stats(self):
        """Generate flood_pop.csv"""
        print(f"\n🌊 Generating {self.city_name_l}_flood_pop.csv...")

        pop_file = os.path.join(self.spatial_dir, f'{self.city_name_l}_population.tif')
        if not os.path.exists(pop_file):
            print(f"   ⏭️  Source missing: Population data")
            return False

        flood_types = ['fluvial', 'pluvial', 'coastal', 'combined_flooding']
        available_floods = [ft for ft in flood_types
                          if any(ft in f and f.endswith('_2020.tif')
                                for f in os.listdir(self.spatial_dir))]

        if not available_floods:
            print(f"   ⏭️  Source missing: Flood rasters")
            return False

        try:
            rows = []

            for ft in available_floods:
                flood_files = [f for f in os.listdir(self.spatial_dir)
                              if ft in f and f.endswith('_2020.tif') and 'utm' not in f]
                if not flood_files:
                    continue

                flood_file = os.path.join(self.spatial_dir, flood_files[0])

                with rasterio.open(pop_file) as pop:
                    pop_array = pop.read(1)
                    pop_array = np.where(pop_array < 0, np.nan, pop_array)

                    pop60 = np.nanpercentile(pop_array, 60)
                    dense_pop = (pop_array >= pop60).astype(float)

                    import rasterio.warp as warp
                    with rasterio.open(flood_file) as flood_src:
                        flood_array = np.zeros(pop_array.shape)
                        warp.reproject(
                            source=flood_src.read(1),
                            destination=flood_array,
                            src_transform=flood_src.transform,
                            src_crs=flood_src.crs,
                            dst_transform=pop.transform,
                            dst_crs=pop.crs,
                            resampling=warp.Resampling.nearest
                        )

                    total_dense = np.sum(dense_pop)
                    exposed_dense = np.sum((dense_pop == 1) & (flood_array > 0))
                    pct = (exposed_dense / total_dense * 100) if total_dense > 0 else 0

                    rows.append([f'{ft}_2020', pct])

            if rows:
                df = pd.DataFrame(rows, columns=['type', 'exposed_dense_pop_pct'])
                output_file = os.path.join(self.tabular_dir, f'{self.city_name_l}_flood_pop.csv')
                df.to_csv(output_file, index=False)
                print(f"   ✅ Generated {self.city_name_l}_flood_pop.csv")
                return True

            return False

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    def generate_flood_road_stats(self):
        """Generate flood_road.csv"""
        print(f"\n🌊 Generating {self.city_name_l}_flood_road.csv...")

        road_file = os.path.join(self.spatial_dir, f'{self.city_name_l}_major_roads.gpkg')
        if not os.path.exists(road_file):
            print(f"   ⏭️  Source missing: Road network data")
            return False

        flood_types = ['fluvial', 'pluvial', 'coastal', 'combined_flooding']
        available_floods = [ft for ft in flood_types
                          if any(ft in f and f.endswith('_2020_utm.tif')
                                for f in os.listdir(self.spatial_dir))]

        if not available_floods:
            print(f"   ⏭️  Source missing: Flood rasters (UTM)")
            return False

        try:
            roads = gpd.read_file(road_file, layer='major_roads')

            if roads.empty:
                print(f"   ⏭️  No roads in dataset")
                return False

            utm_crs = roads.crs
            rows = []

            for ft in available_floods:
                flood_files = [f for f in os.listdir(self.spatial_dir)
                              if ft in f and f.endswith('_2020_utm.tif')]
                if not flood_files:
                    continue

                flood_file = os.path.join(self.spatial_dir, flood_files[0])

                with rasterio.open(flood_file) as flood_src:
                    flood_data = flood_src.read(1)
                    flood_transform = flood_src.transform

                    from rasterio.features import shapes
                    from shapely.geometry import shape as shp_shape

                    flood_mask = flood_data > 0
                    flood_polys = [shp_shape(p) for p, val in shapes(flood_mask.astype('uint8'), transform=flood_transform) if val == 1]

                    flood_zones = gpd.GeoDataFrame(geometry=flood_polys, crs=utm_crs)
                    clipped = gpd.overlay(roads, flood_zones, how='intersection')

                    total_length = roads.length.sum()
                    flooded_length = clipped.length.sum()
                    pct = (flooded_length / total_length * 100) if total_length > 0 else 0

                    rows.append([f'{ft}_2020', total_length, flooded_length, pct])

            if rows:
                df = pd.DataFrame(rows, columns=['type', 'total_major_road_meter', 'meter_in_flood_zones', 'percentage_in_flood_zones'])
                output_file = os.path.join(self.tabular_dir, f'{self.city_name_l}_flood_road.csv')
                df.to_csv(output_file, index=False)
                print(f"   ✅ Generated {self.city_name_l}_flood_road.csv")
                return True

            return False

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    def generate_flood_osm_stats(self):
        """Generate flood_osm.csv"""
        print(f"\n🌊 Generating {self.city_name_l}_flood_osm.csv...")

        osm_types = ['health', 'schools', 'fire', 'police']
        available_osm = [t for t in osm_types
                        if any(f'osm_{t}' in f and f.endswith('.gpkg')
                              for f in os.listdir(self.spatial_dir))]

        if not available_osm:
            print(f"   ⏭️  Source missing: OSM POI data")
            return False

        flood_types = ['fluvial', 'pluvial', 'coastal', 'combined_flooding']
        available_floods = [ft for ft in flood_types
                          if any(ft in f and f.endswith('_2020.tif')
                                for f in os.listdir(self.spatial_dir))]

        if not available_floods:
            print(f"   ⏭️  Source missing: Flood rasters")
            return False

        try:
            rows = []

            for poi_type in available_osm:
                osm_files = [f for f in os.listdir(self.spatial_dir)
                            if f'osm_{poi_type}' in f and f.endswith('.gpkg')]

                osm_file = os.path.join(self.spatial_dir, osm_files[0])
                osm = gpd.read_file(osm_file)

                if osm.empty:
                    continue

                for ft in available_floods:
                    flood_files = [f for f in os.listdir(self.spatial_dir)
                                  if ft in f and f.endswith('_2020.tif') and 'utm' not in f]
                    if not flood_files:
                        continue

                    flood_file = os.path.join(self.spatial_dir, flood_files[0])

                    with rasterio.open(flood_file) as flood_src:
                        flood_data = flood_src.read(1)

                        # Reproject OSM to flood CRS
                        osm_reproj = osm.to_crs(flood_src.crs)

                        in_flood = 0
                        for idx, row in osm_reproj.iterrows():
                            # Sample flood raster at point
                            try:
                                for val in flood_src.sample([(row.geometry.x, row.geometry.y)]):
                                    if val[0] > 0:
                                        in_flood += 1
                            except:
                                pass

                        total = len(osm)
                        pct = (in_flood / total * 100) if total > 0 else 0
                        rows.append([poi_type, f'{ft}_2020', total, in_flood, pct])

            if rows:
                df = pd.DataFrame(rows, columns=['poi', 'type', 'total_pois', 'pois_in_flood_zone', 'percentage_in_flood_zone'])
                output_file = os.path.join(self.tabular_dir, f'{self.city_name_l}_flood_osm.csv')
                df.to_csv(output_file, index=False)
                print(f"   ✅ Generated {self.city_name_l}_flood_osm.csv")
                return True

            return False

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Compare city data to reference and generate missing files'
    )
    parser.add_argument(
        '--reference', '-r',
        default='sofifi',
        help='Reference city name (default: sofifi)'
    )
    parser.add_argument(
        '--generate', '-g',
        action='store_true',
        help='Generate missing tabular files (default: only compare)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🔍 CITY DATA COMPARATOR")
    print("=" * 70)

    try:
        city_dir = os.getcwd()
        comparator = CityDataComparator(city_dir, args.reference)

        # Compare directories
        summary = comparator.compare_directories()

        # Generate missing files if requested
        if args.generate:
            comparator.generate_missing_tabular(summary)
        else:
            print("\n💡 Tip: Add --generate to create missing tabular files")

        print("\n" + "=" * 70)
        print("✅ DONE!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
