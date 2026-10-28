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


print("=" * 74)
print("STEP 9 — CONTEMPORANEOUS VEGETATION ACTIVITY + UNCERTAINTY")
print("=" * 74)


# ======================================================
# 1. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")


# ======================================================
# 2. RECREATE PyEOGPR RETRIEVAL
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


print("\nRunning PyEOGPR retrieval...")

retrieval = job.calculate_GREEN(
    start,
    end,
    "laiCw",
)

print("✅ PyEOGPR retrieval created.")


# ======================================================
# 3. FULL-SEASON AGRICULTURAL MASK
#    Same logic used in Step 8
# ======================================================

SEASON_START = "2025-11-15"
SEASON_END = "2026-04-15"


dw = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterBounds(job.bbox)
    .filterDate(
        SEASON_START,
        SEASON_END,
    )
)


def dw_crop(image):
    return (
        image
        .select("label")
        .eq(4)
        .rename("crop")
    )


def dw_built(image):
    return (
        image
        .select("label")
        .eq(6)
        .rename("built")
    )


def dw_water(image):
    return (
        image
        .select("label")
        .eq(0)
        .rename("water")
    )


crop_frequency = (
    dw
    .map(dw_crop)
    .mean()
    .rename("crop_frequency")
)


built_frequency = (
    dw
    .map(dw_built)
    .mean()
    .rename("built_frequency")
)


water_frequency = (
    dw
    .map(dw_water)
    .mean()
    .rename("water_frequency")
)


# ======================================================
# 4. SENTINEL-2 SR CLOUD MASK
# ======================================================

def mask_s2_sr(image):

    qa = image.select("QA60")

    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11

    clear = (
        qa
        .bitwiseAnd(cloud_bit)
        .eq(0)
        .And(
            qa
            .bitwiseAnd(cirrus_bit)
            .eq(0)
        )
    )

    return image.updateMask(clear)


def add_ndvi(image):

    ndvi = (
        image
        .normalizedDifference(
            ["B8", "B4"]
        )
        .rename("NDVI")
    )

    return image.addBands(ndvi)


# ======================================================
# 5. FULL-SEASON NDVI
#    Used only for agricultural-domain definition
# ======================================================

season_s2 = (
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
    .map(add_ndvi)
)


seasonal_max_ndvi = (
    season_s2
    .select("NDVI")
    .max()
    .rename("seasonal_max_ndvi")
)


# ======================================================
# 6. AGRICULTURAL MASK
# ======================================================

CROP_FREQ_THRESHOLD = 0.25
SEASONAL_NDVI_THRESHOLD = 0.40
BUILT_FREQ_MAX = 0.20
WATER_FREQ_MAX = 0.20


agricultural_mask = (
    crop_frequency
    .gte(CROP_FREQ_THRESHOLD)

    .And(
        seasonal_max_ndvi
        .gte(SEASONAL_NDVI_THRESHOLD)
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
# 7. CONTEMPORANEOUS SENTINEL-2 L2A
#    Same dates as the PyEOGPR retrieval
# ======================================================

current_s2 = (
    ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )
    .filterBounds(job.bbox)
    .filterDate(
        start,
        end,
    )
    .filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            40,
        )
    )
    .map(mask_s2_sr)
    .map(add_ndvi)
)


current_scene_count = (
    current_s2
    .size()
    .getInfo()
)


print(
    "\nSentinel-2 L2A scenes for contemporaneous NDVI:",
    current_scene_count,
)


if current_scene_count == 0:
    raise RuntimeError(
        "No contemporaneous Sentinel-2 L2A scenes."
    )


# Mean of per-image clear-pixel NDVI values.
current_ndvi = (
    current_s2
    .select("NDVI")
    .mean()
    .rename("current_ndvi")
)


# ======================================================
# 8. PREPARE GPR OUTPUT
# ======================================================

prediction = (
    retrieval
    .select("laiCw")
    .updateMask(agricultural_mask)
)


uncertainty = (
    retrieval
    .select("laiCw_UNCERTAINTY")
    .updateMask(agricultural_mask)
)


# Avoid meaningless division at zero/negative prediction.
positive_prediction = (
    prediction.gt(0)
)


prediction = (
    prediction
    .updateMask(positive_prediction)
)


uncertainty = (
    uncertainty
    .updateMask(positive_prediction)
)


relative_uncertainty = (
    uncertainty
    .divide(prediction)
    .multiply(100)
    .rename("relative_uncertainty_pct")
)


# Apply agricultural domain to contemporaneous NDVI too.
current_ndvi = (
    current_ndvi
    .updateMask(agricultural_mask)
)


# ======================================================
# 9. COMBINE QA VARIABLES
# ======================================================

qa_image = (
    prediction
    .addBands(uncertainty)
    .addBands(relative_uncertainty)
    .addBands(current_ndvi)
    .addBands(crop_frequency)
    .addBands(seasonal_max_ndvi)
)


# ======================================================
# 10. REPRODUCIBLE SAMPLE
# ======================================================

QA_SAMPLE_SIZE = 3000
QA_SCALE = 60
QA_TILE_SCALE = 4
QA_SEED = 42


sample = (
    qa_image
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
    sample
    .size()
    .getInfo()
)


print("\n" + "=" * 74)
print("QA SAMPLE")
print("=" * 74)

print("Sample size:", sample_count)
print("Scale:", QA_SCALE, "m")
print("Random seed:", QA_SEED)


if sample_count == 0:
    raise RuntimeError(
        "No valid contemporaneous QA pixels."
    )


# ======================================================
# 11. HELPER FUNCTIONS
# ======================================================

def percentiles(collection, property_name):

    return (
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


def median_value(collection, property_name):

    result = (
        collection
        .reduceColumns(
            reducer=ee.Reducer.percentile(
                [50]
            ),
            selectors=[
                property_name
            ],
        )
        .getInfo()
    )

    return result.get("p50")


def pearson_correlation(
    collection,
    x_property,
    y_property,
):

    result = (
        collection
        .reduceColumns(
            reducer=ee.Reducer.pearsonsCorrelation(),
            selectors=[
                x_property,
                y_property,
            ],
        )
        .getInfo()
    )

    return result


# ======================================================
# 12. CONTEMPORANEOUS NDVI DISTRIBUTION
# ======================================================

ndvi_stats = percentiles(
    sample,
    "current_ndvi",
)


print("\n" + "-" * 74)
print("CONTEMPORANEOUS NDVI DISTRIBUTION")
print("-" * 74)


for key, value in ndvi_stats.items():
    print(f"{key}: {value}")


# ======================================================
# 13. GPR DISTRIBUTIONS
# ======================================================

lai_stats = percentiles(
    sample,
    "laiCw",
)

abs_unc_stats = percentiles(
    sample,
    "laiCw_UNCERTAINTY",
)

rel_unc_stats = percentiles(
    sample,
    "relative_uncertainty_pct",
)


print("\n" + "-" * 74)
print("laiCw [g/m²]")
print("-" * 74)

for key, value in lai_stats.items():
    print(f"{key}: {value}")


print("\n" + "-" * 74)
print("ABSOLUTE GPR UNCERTAINTY [g/m²]")
print("-" * 74)

for key, value in abs_unc_stats.items():
    print(f"{key}: {value}")


print("\n" + "-" * 74)
print("RELATIVE GPR UNCERTAINTY [%]")
print("-" * 74)

for key, value in rel_unc_stats.items():
    print(f"{key}: {value}")


# ======================================================
# 14. CORRELATION DIAGNOSTICS
# ======================================================

print("\n" + "=" * 74)
print("CORRELATION DIAGNOSTICS")
print("=" * 74)


relationships = [
    (
        "laiCw vs absolute uncertainty",
        "laiCw",
        "laiCw_UNCERTAINTY",
    ),
    (
        "laiCw vs relative uncertainty",
        "laiCw",
        "relative_uncertainty_pct",
    ),
    (
        "laiCw vs contemporaneous NDVI",
        "laiCw",
        "current_ndvi",
    ),
    (
        "NDVI vs relative uncertainty",
        "current_ndvi",
        "relative_uncertainty_pct",
    ),
    (
        "NDVI vs absolute uncertainty",
        "current_ndvi",
        "laiCw_UNCERTAINTY",
    ),
]


for label, x, y in relationships:

    result = pearson_correlation(
        sample,
        x,
        y,
    )

    print(f"\n{label}")

    for key, value in result.items():
        print(
            f"  {key}: {value}"
        )


# ======================================================
# 15. VEGETATION-ACTIVITY THRESHOLD ANALYSIS
# ======================================================

print("\n" + "=" * 74)
print("CONTEMPORANEOUS NDVI THRESHOLD ANALYSIS")
print("=" * 74)


NDVI_THRESHOLDS = [
    0.20,
    0.30,
    0.40,
]


for ndvi_threshold in NDVI_THRESHOLDS:

    active = (
        sample
        .filter(
            ee.Filter.gte(
                "current_ndvi",
                ndvi_threshold,
            )
        )
    )

    n_active = (
        active
        .size()
        .getInfo()
    )


    pct_active = (
        100
        * n_active
        / sample_count
    )


    print(
        "\n"
        + "-" * 74
    )

    print(
        f"CURRENT NDVI >= {ndvi_threshold}"
    )

    print(
        "-" * 74
    )

    print(
        f"Pixels retained: "
        f"{n_active} "
        f"({pct_active:.2f}%)"
    )


    if n_active == 0:

        print(
            "No pixels available."
        )

        continue


    median_lai = median_value(
        active,
        "laiCw",
    )

    median_abs_unc = median_value(
        active,
        "laiCw_UNCERTAINTY",
    )

    median_rel_unc = median_value(
        active,
        "relative_uncertainty_pct",
    )


    print(
        f"Median laiCw: "
        f"{median_lai:.2f} g/m²"
    )

    print(
        f"Median absolute uncertainty: "
        f"{median_abs_unc:.2f} g/m²"
    )

    print(
        f"Median relative uncertainty: "
        f"{median_rel_unc:.2f}%"
    )


    for uncertainty_threshold in [
        20,
        30,
        40,
    ]:

        retained = (
            active
            .filter(
                ee.Filter.lt(
                    "relative_uncertainty_pct",
                    uncertainty_threshold,
                )
            )
            .size()
            .getInfo()
        )


        retained_pct = (
            100
            * retained
            / n_active
        )


        print(
            f"  RU < {uncertainty_threshold}%: "
            f"{retained_pct:.2f}%"
        )


# ======================================================
# 16. LOW-VEGETATION FRACTIONS
# ======================================================

print("\n" + "=" * 74)
print("LOW-VEGETATION FRACTIONS")
print("=" * 74)


for ndvi_threshold in [
    0.20,
    0.30,
    0.40,
]:

    low_count = (
        sample
        .filter(
            ee.Filter.lt(
                "current_ndvi",
                ndvi_threshold,
            )
        )
        .size()
        .getInfo()
    )


    low_pct = (
        100
        * low_count
        / sample_count
    )


    print(
        f"Current NDVI < {ndvi_threshold}: "
        f"{low_pct:.2f}%"
    )


# ======================================================
# 17. FINAL STATUS
# ======================================================

print("\n" + "=" * 74)
print("✅ STEP 9 DIAGNOSTIC COMPLETE")
print("=" * 74)

print(
    "No final NDVI threshold has been selected."
)

print(
    "No final uncertainty threshold has been selected."
)

print(
    "No Earth Engine asset or GeoTIFF has been exported."
)