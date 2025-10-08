from pathlib import Path
import importlib
import subprocess
import sys


import subprocess, sys, importlib

# Check which packages are missing
required_packages = [ "yaml", "pandas", "numpy", "rasterio", "geopandas", "shapely"]
missing_packages = []

print("Checking required packages...")
for pkg in required_packages:
    try:
        importlib.import_module(pkg)
        print(f"  ✓ {pkg}")
    except ImportError:
        print(f"  ✗ {pkg} (missing)")
        missing_packages.append(pkg)

# If packages are missing, ask user before installing
if missing_packages:
    print(f"\nMissing packages: {', '.join(missing_packages)}")
    response = input("Would you like to install them? (y/n): ").strip().lower()

    if response == 'y' or response == 'yes':
        print("\nInstalling missing packages...")
        for pkg in missing_packages:
            print(f"  Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        print("\nAll packages installed successfully!")
    else:
        print("\nInstallation aborted. Required packages are missing.")
        sys.exit(1)
else:
    print("\nAll required packages are already installed!")


