from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import ee

from config.project_config import GEE_PROJECT_ID


# ------------------------------------------------------
# Initialize GEE
# ------------------------------------------------------

ee.Initialize(project=GEE_PROJECT_ID)


# ------------------------------------------------------
# Same smoke-test AOI
# ------------------------------------------------------

bbox = ee.Geometry.Rectangle([
    73.435,
    31.228,
    73.485,
    31.273,
])


START_DATE = "2026-02-01"
END_DATE = "2026-02-12"


# Bands used by the Sentinel-2 L1C GPR family
# We will inspect common spectral bands only here.
bands = [
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B8A",
    "B11",
    "B12",
]


collection = (
    ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
    .filterDate(START_DATE, END_DATE)
    .filterBounds(bbox)
    .filterMetadata(
        "CLOUDY_PIXEL_PERCENTAGE",
        "less_than",
        40,
    )
    .select(bands)
)


print("Scenes after metadata filtering:", collection.size().getInfo())


# ------------------------------------------------------
# Construct both alternatives
# ------------------------------------------------------

mean_composite = collection.mean().divide(10000)

max_composite = collection.max().divide(10000)


# Absolute spectral difference
difference = (
    max_composite
    .subtract(mean_composite)
    .abs()
)


# ------------------------------------------------------
# AOI-wide mean difference for each band
# ------------------------------------------------------

stats = difference.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=bbox,
    scale=20,
    maxPixels=1e8,
).getInfo()


print("\nMean absolute difference")
print("(MAX composite - MEAN composite)\n")

for band, value in stats.items():
    print(
        f"{band:>4}: "
        f"{value:.6f}"
        if value is not None
        else f"{band:>4}: None"
    )


print("\n✅ Composite audit completed.")
