from pathlib import Path
import sys

# ------------------------------------------------------
# Project root
# ------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ------------------------------------------------------
# Imports
# ------------------------------------------------------

import ee

from config.project_config import GEE_PROJECT_ID
from pyeogpr import EarthEngine


print("=" * 60)
print("PyEOGPR × GOOGLE EARTH ENGINE SMOKE TEST")
print("=" * 60)


# ------------------------------------------------------
# 1. Initialize Earth Engine
# ------------------------------------------------------

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")
print("GEE project:", GEE_PROJECT_ID)


# ------------------------------------------------------
# 2. Small test AOI INSIDE our frozen study area
# ------------------------------------------------------

SMOKE_BBOX = [
    73.435,   # west
    31.228,   # south
    73.485,   # east
    31.273,   # north
]


# ------------------------------------------------------
# 3. Smoke-test dates
# ------------------------------------------------------

START_DATE = "2026-02-01"
END_DATE = "2026-02-12"


# ------------------------------------------------------
# 4. Create PyEOGPR EarthEngine object
# ------------------------------------------------------

print("\nCreating PyEOGPR EarthEngine object...")

ee_job = EarthEngine(
    projectID=GEE_PROJECT_ID,
    sensor="SENTINEL2_L1C",
    biovar="laiCw",
    bounding_box=SMOKE_BBOX,
    temporal_extent=[
        START_DATE,
        END_DATE,
    ],
    spatial_resolution=20,
    cloudmask=True,
)


print("✅ PyEOGPR EarthEngine object created.")


# ------------------------------------------------------
# 5. Inspect configuration
# ------------------------------------------------------

print("\n--- PyEOGPR configuration ---")

print("Sensor:", ee_job.sensor)
print("Biophysical variable:", ee_job.biovar)
print("Temporal extent:", ee_job.temporal_extent)
print("Spatial resolution:", ee_job.spatial_resolution)
print("Cloud mask setting:", ee_job.cloudmask)


# ------------------------------------------------------
# 6. Verify model module loaded
# ------------------------------------------------------

if ee_job.model_imported is None:
    raise RuntimeError("PyEOGPR pretrained GPR model was not loaded.")

print("\n✅ Pretrained laiCw GPR model loaded.")

print(
    "Model module:",
    ee_job.model_imported.__name__
)


# ------------------------------------------------------
# 7. Verify Sentinel-2 over test AOI
# ------------------------------------------------------

local_count = (
    ee_job.imcol
    .filterBounds(ee_job.bbox)
    .size()
    .getInfo()
)

print(
    "\nSentinel-2 scenes intersecting smoke-test AOI:",
    local_count
)

if local_count <= 0:
    raise RuntimeError(
        "No Sentinel-2 L1C images intersect the smoke-test AOI."
    )


# ------------------------------------------------------
# 8. Construct requested temporal composite setting
# ------------------------------------------------------

ee_job.construct_datacube(
    composite=10
)

print(
    "Temporal composite length:",
    ee_job.timeWindows,
    "days"
)


print("\n" + "=" * 60)
print("✅ STEP 4 PASSED")
print("PyEOGPR import: OK")
print("GEE backend: OK")
print("laiCw model load: OK")
print("Sentinel-2 L1C access: OK")
print("Composite configuration: OK")
print("=" * 60)