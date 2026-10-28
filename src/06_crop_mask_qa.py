from pathlib import Path
import sys

# ======================================================
# PROJECT ROOT
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ======================================================
# IMPORTS
# ======================================================

import ee

from pyeogpr import EarthEngine

from config.project_config import GEE_PROJECT_ID
from config.study_config import (
    SMOKE_BBOX,
    SMOKE_START,
    SMOKE_END,
    SMOKE_COMPOSITE_DAYS,
    SPATIAL_RESOLUTION,
)


print("=" * 72)
print("STEP 8 — AGRICULTURAL MASK + CROPLAND PyEOGPR QA")
print("=" * 72)


# ======================================================
# 1. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")


# ======================================================
# 2. RECREATE PyEOGPR SMOKE-TEST RETRIEVAL
# ======================================================

job = EarthEngine(
    projectID=GEE_PROJECT_ID,
    sensor="SENTINEL2_L1C",
    biovar="laiCw",
    bounding_box=SMOKE_BBOX,
    temporal_extent=[
        SMOKE_START,
        SMOKE_END,
    ],
    spatial_resolution=SPATIAL_RESOLUTION,
    cloudmask=True,
)

print("✅ PyEOGPR object created.")


job.construct_datacube(
    composite=SMOKE_COMPOSITE_DAYS
)


dates = job.getInputDates(0)

start = dates["fecha_inicio"]
end = dates["fecha_fin"]


print(
    "Retrieval window:",
    start.format("YYYY-MM-dd").getInfo(),
    "to",
    end.format("YYYY-MM-dd").getInfo(),
)


# ======================================================
# 3. CHECK SOURCE SENTINEL-2 L1C SCENES
# ======================================================

source_collection = (
    job.imcol
    .filterDate(start, end)
    .filterBounds(job.bbox)
    .filterMetadata(
        "CLOUDY_PIXEL_PERCENTAGE",
        "less_than",
        40,
    )
)

source_count = source_collection.size().getInfo()

print(
    "Sentinel-2 L1C scenes used by retrieval window:",
    source_count,
)

if source_count == 0:
    raise RuntimeError(
        "No Sentinel-2 L1C scenes available for retrieval."
    )


# ======================================================
# 4. RUN PyEOGPR laiCw RETRIEVAL
# ======================================================

print("\nRunning PyEOGPR laiCw retrieval...")

retrieval = job.calculate_GREEN(
    start,
    end,
    "laiCw",
)

print("✅ PyEOGPR retrieval created.")


bands = retrieval.bandNames().getInfo()

print("Retrieval bands:", bands)

expected = {
    "laiCw",
    "laiCw_UNCERTAINTY",
}

if set(bands) != expected:
    raise RuntimeError(
        f"Unexpected retrieval bands: {bands}"
    )


# ======================================================
# 5. DEFINE FULL RABI SEASON
# ======================================================

SEASON_START = "2025-11-15"
SEASON_END = "2026-04-15"

print("\nSeason used for agricultural classification:")
print(SEASON_START, "to", SEASON_END)


# ======================================================
# 6. DYNAMIC WORLD COLLECTION
# ======================================================

dw = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterBounds(job.bbox)
    .filterDate(
        SEASON_START,
        SEASON_END,
    )
)

dw_count = dw.size().getInfo()

print("\nDynamic World scenes:", dw_count)

if dw_count == 0:
    raise RuntimeError(
        "No Dynamic World observations available."
    )


# Dynamic World label classes:
#
# 0 = water
# 1 = trees
# 2 = grass
# 3 = flooded vegetation
# 4 = crops
# 5 = shrub / scrub
# 6 = built
# 7 = bare
# 8 = snow / ice


# ======================================================
# 7. SEASONAL CROP OCCURRENCE FREQUENCY
# ======================================================

def dynamic_world_crop(image):

    return (
        image
        .select("label")
        .eq(4)
        .rename("crop")
    )


crop_frequency = (
    dw
    .map(dynamic_world_crop)
    .mean()
    .rename("crop_frequency")
)


# ======================================================
# 8. BUILT-UP FREQUENCY
# ======================================================

def dynamic_world_built(image):

    return (
        image
        .select("label")
        .eq(6)
        .rename("built")
    )


built_frequency = (
    dw
    .map(dynamic_world_built)
    .mean()
    .rename("built_frequency")
)


# ======================================================
# 9. WATER FREQUENCY
# ======================================================

def dynamic_world_water(image):

    return (
        image
        .select("label")
        .eq(0)
        .rename("water")
    )


water_frequency = (
    dw
    .map(dynamic_world_water)
    .mean()
    .rename("water_frequency")
)


# ======================================================
# 10. SENTINEL-2 L2A COLLECTION FOR NDVI
# ======================================================

def mask_s2_sr(image):

    qa = image.select("QA60")

    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11

    clear_mask = (
        qa
        .bitwiseAnd(cloud_bit)
        .eq(0)
        .And(
            qa
            .bitwiseAnd(cirrus_bit)
            .eq(0)
        )
    )

    return image.updateMask(clear_mask)


s2_sr = (
    ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )
    .filterBounds(job.bbox)
    .filterDate(
        SEASON_START,
        SEASON_END,
    )
    .filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            40,
        )
    )
    .map(mask_s2_sr)
)


s2_sr_count = s2_sr.size().getInfo()

print(
    "Sentinel-2 L2A scenes for seasonal NDVI:",
    s2_sr_count,
)

if s2_sr_count == 0:
    raise RuntimeError(
        "No Sentinel-2 L2A scenes available for NDVI."
    )


# ======================================================
# 11. CALCULATE NDVI
# ======================================================

def add_ndvi(image):

    ndvi = (
        image
        .normalizedDifference(
            ["B8", "B4"]
        )
        .rename("NDVI")
    )

    return image.addBands(ndvi)


seasonal_max_ndvi = (
    s2_sr
    .map(add_ndvi)
    .select("NDVI")
    .max()
    .rename("seasonal_max_ndvi")
)


# ======================================================
# 12. INITIAL AGRICULTURAL-MASK THRESHOLDS
# ======================================================

# IMPORTANT:
# These are experimental analysis thresholds.
# They are NOT treated as universal crop definitions.
#
# They will later be subjected to sensitivity analysis.

CROP_FREQ_THRESHOLD = 0.25
NDVI_THRESHOLD = 0.40

BUILT_FREQ_MAX = 0.20
WATER_FREQ_MAX = 0.20


print("\nAgricultural-mask thresholds:")

print(
    "Crop occurrence frequency >=",
    CROP_FREQ_THRESHOLD,
)

print(
    "Seasonal max NDVI >=",
    NDVI_THRESHOLD,
)

print(
    "Built occurrence frequency <",
    BUILT_FREQ_MAX,
)

print(
    "Water occurrence frequency <",
    WATER_FREQ_MAX,
)


# ======================================================
# 13. BUILD AGRICULTURAL ANALYSIS MASK
# ======================================================

agricultural_mask = (
    crop_frequency
    .gte(CROP_FREQ_THRESHOLD)

    .And(
        seasonal_max_ndvi
        .gte(NDVI_THRESHOLD)
    )

    .And(
        built_frequency
        .lt(BUILT_FREQ_MAX)
    )

    .And(
        water_frequency
        .lt(WATER_FREQ_MAX)
    )

    .rename("agricultural_mask")
)


# ======================================================
# 14. CALCULATE AGRICULTURAL COVERAGE
# ======================================================

agricultural_area = (
    ee.Image.pixelArea()
    .updateMask(
        agricultural_mask
    )
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=job.bbox,
        scale=20,
        maxPixels=1e8,
        tileScale=4,
    )
    .get("area")
)


total_area = job.bbox.area(
    maxError=1
)


agricultural_fraction = (
    ee.Number(agricultural_area)
    .divide(total_area)
    .multiply(100)
    .getInfo()
)


print("\n" + "=" * 72)
print("AGRICULTURAL MASK COVERAGE")
print("=" * 72)

print(
    f"Agricultural analysis area: "
    f"{agricultural_fraction:.2f}%"
)


# ======================================================
# 15. APPLY AGRICULTURAL MASK TO PyEOGPR RETRIEVAL
# ======================================================

crop_retrieval = (
    retrieval
    .updateMask(
        agricultural_mask
    )
)


crop_prediction = (
    crop_retrieval
    .select("laiCw")
)


crop_uncertainty = (
    crop_retrieval
    .select("laiCw_UNCERTAINTY")
)


# ======================================================
# 16. PREVENT DIVISION BY ZERO
# ======================================================

positive_prediction = (
    crop_prediction.gt(0)
)


crop_prediction = (
    crop_prediction
    .updateMask(
        positive_prediction
    )
)


crop_uncertainty = (
    crop_uncertainty
    .updateMask(
        positive_prediction
    )
)


# ======================================================
# 17. RELATIVE GPR UNCERTAINTY
# ======================================================

crop_relative_uncertainty = (
    crop_uncertainty
    .divide(crop_prediction)
    .multiply(100)
    .rename(
        "relative_uncertainty_pct"
    )
)


crop_qa = (
    crop_prediction
    .addBands(
        crop_uncertainty
    )
    .addBands(
        crop_relative_uncertainty
    )
)


# ======================================================
# 18. SAMPLE CROPLAND PIXELS
# ======================================================

QA_SAMPLE_SIZE = 3000
QA_SCALE = 60
QA_TILE_SCALE = 4
QA_SEED = 42


crop_sample = (
    crop_qa
    .sample(
        region=job.bbox,
        scale=QA_SCALE,
        numPixels=QA_SAMPLE_SIZE,
        seed=QA_SEED,
        geometries=False,
        tileScale=QA_TILE_SCALE,
    )
)


sample_count = (
    crop_sample
    .size()
    .getInfo()
)


print("\n" + "=" * 72)
print("AGRICULTURAL QA SAMPLE")
print("=" * 72)

print("Sample size:", sample_count)
print("QA scale:", QA_SCALE, "m")
print("Random seed:", QA_SEED)


if sample_count == 0:

    raise RuntimeError(
        "Agricultural mask produced no valid QA samples."
    )


# ======================================================
# 19. HELPER — PERCENTILE STATISTICS
# ======================================================

def get_percentiles(
    collection,
    property_name,
):

    result = (
        collection
        .reduceColumns(
            reducer=ee.Reducer.percentile(
                [
                    5,
                    25,
                    50,
                    75,
                    95,
                ]
            ),
            selectors=[
                property_name
            ],
        )
        .getInfo()
    )

    return result


# ======================================================
# 20. laiCw DISTRIBUTION
# ======================================================

lai_stats = get_percentiles(
    crop_sample,
    "laiCw",
)


print("\n" + "-" * 72)
print("CROPLAND laiCw DISTRIBUTION [g/m²]")
print("-" * 72)


for key, value in lai_stats.items():

    print(
        f"{key}: {value}"
    )


# ======================================================
# 21. ABSOLUTE UNCERTAINTY DISTRIBUTION
# ======================================================

absolute_uncertainty_stats = (
    get_percentiles(
        crop_sample,
        "laiCw_UNCERTAINTY",
    )
)


print("\n" + "-" * 72)
print("CROPLAND ABSOLUTE GPR UNCERTAINTY [g/m²]")
print("-" * 72)


for key, value in absolute_uncertainty_stats.items():

    print(
        f"{key}: {value}"
    )


# ======================================================
# 22. RELATIVE UNCERTAINTY DISTRIBUTION
# ======================================================

relative_uncertainty_stats = (
    get_percentiles(
        crop_sample,
        "relative_uncertainty_pct",
    )
)


print("\n" + "-" * 72)
print("CROPLAND RELATIVE UNCERTAINTY [%]")
print("-" * 72)


for key, value in relative_uncertainty_stats.items():

    print(
        f"{key}: {value}"
    )


# ======================================================
# 23. CHECK RELATIVE-UNCERTAINTY MIN / MAX
# ======================================================

ru_minmax = (
    crop_sample
    .reduceColumns(
        reducer=ee.Reducer.minMax(),
        selectors=[
            "relative_uncertainty_pct"
        ],
    )
    .getInfo()
)


print("\nRelative uncertainty min/max:")

for key, value in ru_minmax.items():

    print(
        f"{key}: {value}"
    )


# ======================================================
# 24. UNCERTAINTY THRESHOLD RETENTION
# ======================================================

print("\n" + "-" * 72)
print("CROPLAND UNCERTAINTY THRESHOLD RETENTION")
print("-" * 72)


for threshold in [
    20,
    30,
    40,
]:

    retained = (
        crop_sample
        .filter(
            ee.Filter.lt(
                "relative_uncertainty_pct",
                threshold,
            )
        )
        .size()
        .getInfo()
    )


    retained_fraction = (
        retained
        / sample_count
        * 100
    )


    print(
        f"< {threshold}% uncertainty: "
        f"{retained_fraction:.2f}%"
    )


# ======================================================
# 25. FIELD-REFERENCE ENVELOPE
# ======================================================

# Approximate observed field-data range used only as
# a diagnostic reference envelope.
#
# This is NOT a hard physical validity mask.

REFERENCE_MIN = 32.1
REFERENCE_MAX = 887.9


below_reference = (
    crop_sample
    .filter(
        ee.Filter.lt(
            "laiCw",
            REFERENCE_MIN,
        )
    )
    .size()
    .getInfo()
)


within_reference = (
    crop_sample
    .filter(
        ee.Filter.gte(
            "laiCw",
            REFERENCE_MIN,
        )
    )
    .filter(
        ee.Filter.lte(
            "laiCw",
            REFERENCE_MAX,
        )
    )
    .size()
    .getInfo()
)


above_reference = (
    crop_sample
    .filter(
        ee.Filter.gt(
            "laiCw",
            REFERENCE_MAX,
        )
    )
    .size()
    .getInfo()
)


print("\n" + "-" * 72)
print("CROPLAND FIELD-REFERENCE RANGE COMPARISON")
print("-" * 72)


print(
    f"Below {REFERENCE_MIN} g/m²: "
    f"{100 * below_reference / sample_count:.2f}%"
)


print(
    f"Within {REFERENCE_MIN}–"
    f"{REFERENCE_MAX} g/m²: "
    f"{100 * within_reference / sample_count:.2f}%"
)


print(
    f"Above {REFERENCE_MAX} g/m²: "
    f"{100 * above_reference / sample_count:.2f}%"
)


# ======================================================
# 26. FINAL STATUS
# ======================================================

print("\n" + "=" * 72)
print("✅ STEP 8 AGRICULTURAL QA COMPLETE")
print("=" * 72)

print(
    f"Agricultural analysis area: "
    f"{agricultural_fraction:.2f}%"
)

print(
    f"Agricultural QA sample size: "
    f"{sample_count}"
)

print(
    "\nNo final uncertainty mask has been selected."
)

print(
    "No Earth Engine asset or GeoTIFF has been exported."
)

print(
    "The <20%, <30%, and <40% thresholds remain "
    "sensitivity-analysis candidates."
)