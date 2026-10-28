from pathlib import Path
import sys

# ------------------------------------------------------
# Make project root importable
# ------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ------------------------------------------------------
# Imports
# ------------------------------------------------------

import ee

from config.project_config import GEE_PROJECT_ID


print("=" * 60)
print("GOOGLE EARTH ENGINE CONNECTIVITY TEST")
print("=" * 60)

print("Earth Engine API version:", ee.__version__)
print("Cloud project:", GEE_PROJECT_ID)


# ------------------------------------------------------
# Authentication
# ------------------------------------------------------

print("\nAuthenticating Google Earth Engine...")

ee.Authenticate(auth_mode="localhost")


# ------------------------------------------------------
# Initialization
# ------------------------------------------------------

print("\nInitializing Earth Engine...")

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized successfully.")


# ------------------------------------------------------
# Very simple server-side calculation
# ------------------------------------------------------

test_value = ee.Number(10).multiply(5).getInfo()

print("\nSimple Earth Engine calculation:")
print("10 × 5 =", test_value)

assert test_value == 50


# ------------------------------------------------------
# Frozen project AOI
# South Jaranwala / Buchiana
# ------------------------------------------------------

AOI = ee.Geometry.Rectangle(
    [
        73.408,  # west
        31.205,  # south
        73.513,  # east
        31.295,  # north
    ]
)


# ------------------------------------------------------
# Check AOI area
# ------------------------------------------------------

area_km2 = AOI.area().divide(1e6).getInfo()

print("\nFrozen study-area size:")
print(f"{area_km2:.2f} km²")


# ------------------------------------------------------
# Check Sentinel-2 L1C availability
# Same product required by our PyEOGPR laiCw model
# ------------------------------------------------------

START_DATE = "2026-02-01"
END_DATE = "2026-02-12"

s2 = (
    ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
    .filterBounds(AOI)
    .filterDate(START_DATE, END_DATE)
)

scene_count = s2.size().getInfo()

print("\nSentinel-2 L1C test:")
print("Dataset: COPERNICUS/S2_HARMONIZED")
print("Period:", START_DATE, "to", END_DATE)
print("Scenes intersecting full AOI:", scene_count)


if scene_count <= 0:
    raise RuntimeError(
        "No Sentinel-2 scenes were found over the project AOI."
    )


print("\n" + "=" * 60)
print("✅ STEP 3 PASSED")
print("GEE authentication: OK")
print("GEE initialization: OK")
print("Server computation: OK")
print("Study-area geometry: OK")
print("Sentinel-2 L1C access: OK")
print("=" * 60)