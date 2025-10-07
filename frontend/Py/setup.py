from pathlib import Path
import importlib
import subprocess
import sys
import yaml

# cfg = yaml.safe_load(Path("frontend/source/pyconfig.yml").read_text())
# py = cfg.get('python') or sys.executable
# reqs = cfg.get('requirements', [])


import subprocess, sys, importlib

def ensure(pkg):
    try:
        importlib.import_module(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

for pkg in ["pyyaml", "pandas", "numpy", "rasterio", "geopandas", "shapely"]:
    ensure(pkg)

import yaml  # safe to import now

# for r in reqs:
#     ensure(r)