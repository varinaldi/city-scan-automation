#!/usr/bin/env python3
"""Quick script to regenerate flood_pop.csv for a specific city"""

import sys
import os

# Import the function from generate_missing_tabular
sys.path.insert(0, os.path.dirname(__file__))
from generate_missing_tabular import generate_flood_stats

if __name__ == '__main__':
    city_dir = os.getcwd()
    city_name = os.path.basename(city_dir)

    # Extract city name
    parts = city_name.split('-')
    if len(parts) >= 4:
        city_name_l = parts[3]
    else:
        print("❌ Error: Run this script from a city directory")
        sys.exit(1)

    process_output_dir = os.path.join(city_dir, '02-process-output')

    print(f"\n📁 City: {city_name_l}")
    print(f"📂 Regenerating flood stats...")

    generate_flood_stats(city_name_l, process_output_dir)

    print("\n✅ Done!")
