from pathlib import Path
import sys
import numpy as np

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
    STUDY_BBOX,
    SPATIAL_RESOLUTION,
)


print("=" * 82)
print("STEP 13B — PARTIALLY OBSERVED MARCH WINDOW QA")
print("=" * 82)


# ======================================================
# 1. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")


# ======================================================
# 2. TEST WINDOW
# ======================================================

WINDOW_START = "2026-03-15"
WINDOW_END = "2026-03-30"

SCENE_CLOUD_THRESHOLD = 80


print(
    "\nWindow:",
    WINDOW_START,
    "to",
    WINDOW_END,
)

print(
    "Scene cloud threshold:",
    f"<{SCENE_CLOUD_THRESHOLD}%",
)


# ======================================================
# 3. CREATE PyEOGPR JOB
# ======================================================

job = EarthEngine(
    projectID=GEE_PROJECT_ID,
    sensor="SENTINEL2_L1C",
    biovar="laiCw",
    bounding_box=STUDY_BBOX,
    temporal_extent=[
        WINDOW_START,
        WINDOW_END,
    ],
    spatial_resolution=SPATIAL_RESOLUTION,
    cloudmask=True,
    scene_cloud_threshold=SCENE_CLOUD_THRESHOLD,
)


# ======================================================
# 4. CHECK L1C SCENES
# ======================================================

l1c = (
    job.imcol
    .filterBounds(job.bbox)
    .filterDate(
        WINDOW_START,
        WINDOW_END,
    )
    .filterMetadata(
        "CLOUDY_PIXEL_PERCENTAGE",
        "less_than",
        SCENE_CLOUD_THRESHOLD,
    )
)


l1c_count = (
    l1c
    .size()
    .getInfo()
)


print(
    "L1C scenes:",
    l1c_count,
)


if l1c_count == 0:
    raise RuntimeError(
        "No L1C scenes available."
    )


# ======================================================
# 5. RUN PyEOGPR RETRIEVAL
# ======================================================

print("\nRunning March laiCw retrieval...")


retrieval = (
    job
    .calculate_GREEN(
        ee.Date(WINDOW_START),
        ee.Date(WINDOW_END),
        "laiCw",
    )
)


print("✅ March retrieval created.")

print(
    "Bands:",
    retrieval
    .bandNames()
    .getInfo(),
)


lai = (
    retrieval
    .select("laiCw")
)


uncertainty = (
    retrieval
    .select("laiCw_UNCERTAINTY")
)


# ======================================================
# 6. CLOUD MASK FUNCTION FOR L2A
# ======================================================

def mask_qa60(image):

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
# 7. CONTEMPORANEOUS L2A NDVI
# ======================================================

l2a = (
    ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )
    .filterBounds(job.bbox)
    .filterDate(
        WINDOW_START,
        WINDOW_END,
    )
    .filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            SCENE_CLOUD_THRESHOLD,
        )
    )
)


l2a_count = (
    l2a
    .size()
    .getInfo()
)


print(
    "L2A scenes:",
    l2a_count,
)


if l2a_count == 0:
    raise RuntimeError(
        "No L2A observations available."
    )


current_ndvi = (
    l2a
    .map(mask_qa60)
    .map(add_ndvi)
    .select("NDVI")
    .mean()
    .rename("current_ndvi")
)


# ======================================================
# 8. RECREATE FROZEN AGRICULTURAL DOMAIN
# ======================================================

SEASON_START = "2025-11-15"
SEASON_END = "2026-04-15"


dw = (
    ee.ImageCollection(
        "GOOGLE/DYNAMICWORLD/V1"
    )
    .filterBounds(job.bbox)
    .filterDate(
        SEASON_START,
        SEASON_END,
    )
)


crop_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(4)
        .rename("crop")
    )
    .mean()
    .rename("crop_frequency")
)


built_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(6)
        .rename("built")
    )
    .mean()
    .rename("built_frequency")
)


water_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(0)
        .rename("water")
    )
    .mean()
    .rename("water_frequency")
)


# Keep the same agricultural-mask construction
# used in Steps 8 and 9.
#
# The seasonal vegetation mask remains based on the
# conservative <40% L2A scene threshold so that changing
# the PyEOGPR production threshold does not redefine the
# agricultural study domain.

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
    .map(mask_qa60)
    .map(add_ndvi)
)


seasonal_max_ndvi = (
    season_s2
    .select("NDVI")
    .max()
    .rename("seasonal_max_ndvi")
)


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
# 9. AREA HELPERS
# ======================================================

def area_of_mask(
    mask_image,
    geometry,
):

    result = (
        ee.Image.pixelArea()
        .updateMask(mask_image)
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=60,
            maxPixels=1e8,
            tileScale=8,
        )
        .get("area")
    )

    if result is None:
        return 0.0

    return ee.Number(result)


def percent_of_total_area(
    valid_mask,
    geometry,
):

    valid_area = (
        area_of_mask(
            valid_mask,
            geometry,
        )
    )

    total_area = (
        geometry
        .area(maxError=1)
    )

    return (
        ee.Number(valid_area)
        .divide(total_area)
        .multiply(100)
        .getInfo()
    )


def percent_of_domain(
    valid_mask,
    domain_mask,
    geometry,
):

    domain_area = (
        area_of_mask(
            domain_mask,
            geometry,
        )
    )

    valid_domain_area = (
        area_of_mask(
            domain_mask
            .And(valid_mask),
            geometry,
        )
    )

    return (
        ee.Number(valid_domain_area)
        .divide(domain_area)
        .multiply(100)
        .getInfo()
    )


# ======================================================
# 10. VALIDITY MASKS
# ======================================================

lai_valid = (
    lai
    .mask()
    .gt(0)
)


ndvi_valid = (
    current_ndvi
    .mask()
    .gt(0)
)


common_valid = (
    lai_valid
    .And(ndvi_valid)
)


# ======================================================
# 11. AOI COVERAGE
# ======================================================

lai_aoi_coverage = (
    percent_of_total_area(
        lai_valid,
        job.bbox,
    )
)


ndvi_aoi_coverage = (
    percent_of_total_area(
        ndvi_valid,
        job.bbox,
    )
)


common_aoi_coverage = (
    percent_of_total_area(
        common_valid,
        job.bbox,
    )
)


print("\n" + "=" * 82)
print("WHOLE-AOI VALID COVERAGE")
print("=" * 82)

print(
    f"laiCw retrieval: "
    f"{lai_aoi_coverage:.2f}%"
)

print(
    f"NDVI: "
    f"{ndvi_aoi_coverage:.2f}%"
)

print(
    f"Common laiCw + NDVI: "
    f"{common_aoi_coverage:.2f}%"
)


# ======================================================
# 12. AGRICULTURAL-DOMAIN COVERAGE
# ======================================================

lai_ag_coverage = (
    percent_of_domain(
        lai_valid,
        agricultural_mask,
        job.bbox,
    )
)


ndvi_ag_coverage = (
    percent_of_domain(
        ndvi_valid,
        agricultural_mask,
        job.bbox,
    )
)


common_ag_coverage = (
    percent_of_domain(
        common_valid,
        agricultural_mask,
        job.bbox,
    )
)


print("\n" + "=" * 82)
print("AGRICULTURAL-DOMAIN COVERAGE")
print("=" * 82)

print(
    f"Valid laiCw agricultural area: "
    f"{lai_ag_coverage:.2f}%"
)

print(
    f"Valid NDVI agricultural area: "
    f"{ndvi_ag_coverage:.2f}%"
)

print(
    f"Common valid agricultural area: "
    f"{common_ag_coverage:.2f}%"
)


# ======================================================
# 13. QUADRANT COVERAGE
# ======================================================

west, south, east, north = STUDY_BBOX

mid_x = (
    west + east
) / 2

mid_y = (
    south + north
) / 2


quadrants = {

    "SW": ee.Geometry.Rectangle(
        [
            west,
            south,
            mid_x,
            mid_y,
        ]
    ),

    "SE": ee.Geometry.Rectangle(
        [
            mid_x,
            south,
            east,
            mid_y,
        ]
    ),

    "NW": ee.Geometry.Rectangle(
        [
            west,
            mid_y,
            mid_x,
            north,
        ]
    ),

    "NE": ee.Geometry.Rectangle(
        [
            mid_x,
            mid_y,
            east,
            north,
        ]
    ),
}


print("\n" + "=" * 82)
print("AGRICULTURAL COVERAGE BY AOI QUADRANT")
print("=" * 82)


for name, geometry in quadrants.items():

    coverage = (
        percent_of_domain(
            lai_valid,
            agricultural_mask,
            geometry,
        )
    )

    print(
        f"{name}: "
        f"{coverage:.2f}%"
    )


# ======================================================
# 14. RELATIVE UNCERTAINTY
# ======================================================

positive_lai = (
    lai.gt(0)
)


relative_uncertainty = (
    uncertainty
    .divide(lai)
    .multiply(100)
    .updateMask(positive_lai)
    .rename(
        "relative_uncertainty_pct"
    )
)


# ======================================================
# 15. BUILD QA IMAGE
# ======================================================

qa_image = (
    lai
    .rename("laiCw")

    .addBands(
        uncertainty
        .rename("laiCw_UNCERTAINTY")
    )

    .addBands(
        relative_uncertainty
    )

    .addBands(
        current_ndvi
    )

    .updateMask(
        agricultural_mask
    )

    .updateMask(
        common_valid
    )
)


# ======================================================
# 16. LIGHTWEIGHT RANDOM-POINT SAMPLE
# ======================================================

QA_POINT_COUNT = 750
QA_SCALE = 60
QA_TILE_SCALE = 16
QA_SEED = 42


random_points = (
    ee.FeatureCollection.randomPoints(
        region=job.bbox,
        points=QA_POINT_COUNT,
        seed=QA_SEED,
        maxError=1,
    )
)


sample = (
    qa_image
    .sampleRegions(
        collection=random_points,
        scale=QA_SCALE,
        geometries=False,
        tileScale=QA_TILE_SCALE,
    )
    .filter(
        ee.Filter.notNull(
            [
                "laiCw",
                "laiCw_UNCERTAINTY",
                "relative_uncertainty_pct",
                "current_ndvi",
            ]
        )
    )
)


sample_count = (
    sample
    .size()
    .getInfo()
)

print("\n" + "=" * 82)
print("VALID AGRICULTURAL QA SAMPLE")
print("=" * 82)

print(
    "Requested points:",
    QA_POINT_COUNT,
)

print(
    "Valid common points:",
    sample_count,
)


if sample_count == 0:

    raise RuntimeError(
        "No valid agricultural QA pixels."
    )
# ======================================================
# 16B. EXACT LOCAL RELATIVE-UNCERTAINTY CHECK
# ======================================================

print("\n" + "=" * 82)
print("EXACT LOCAL RELATIVE-UNCERTAINTY CHECK")
print("=" * 82)


# Recompute RU independently from the sampled
# laiCw and uncertainty properties.
def add_ru_check(feature):

    lai_value = ee.Number(
        feature.get("laiCw")
    )

    uncertainty_value = ee.Number(
        feature.get("laiCw_UNCERTAINTY")
    )

    saved_ru = ee.Number(
        feature.get(
            "relative_uncertainty_pct"
        )
    )

    recomputed_ru = (
        uncertainty_value
        .divide(lai_value)
        .multiply(100)
    )

    absolute_error = (
        recomputed_ru
        .subtract(saved_ru)
        .abs()
    )

    return feature.set({
        "ru_recomputed":
            recomputed_ru,

        "ru_absolute_error":
            absolute_error,
    })


sample_check = sample.map(
    add_ru_check
)


# ------------------------------------------------------
# Retrieve only the small QA arrays locally.
# This sample contains only a few hundred points.
# ------------------------------------------------------

ru_saved = np.asarray(
    sample_check
    .aggregate_array(
        "relative_uncertainty_pct"
    )
    .getInfo(),
    dtype=float,
)


ru_recomputed = np.asarray(
    sample_check
    .aggregate_array(
        "ru_recomputed"
    )
    .getInfo(),
    dtype=float,
)


lai_values = np.asarray(
    sample_check
    .aggregate_array(
        "laiCw"
    )
    .getInfo(),
    dtype=float,
)


unc_values = np.asarray(
    sample_check
    .aggregate_array(
        "laiCw_UNCERTAINTY"
    )
    .getInfo(),
    dtype=float,
)


ndvi_values = np.asarray(
    sample_check
    .aggregate_array(
        "current_ndvi"
    )
    .getInfo(),
    dtype=float,
)


# ======================================================
# Check whether saved RU equals independently
# recomputed uncertainty / laiCw * 100.
# ======================================================

max_ru_error = float(
    np.max(
        np.abs(
            ru_saved
            - ru_recomputed
        )
    )
)


print(
    "Maximum difference between saved "
    "and recomputed RU:",
    max_ru_error,
)


# ======================================================
# Exact percentiles calculated locally
# ======================================================

PERCENTILES = [
    5,
    25,
    50,
    75,
    95,
]


def print_exact_percentiles(
    label,
    values,
):

    values = np.asarray(
        values,
        dtype=float,
    )

    result = np.percentile(
        values,
        PERCENTILES,
    )

    print(f"\n{label}")

    for percentile, value in zip(
        PERCENTILES,
        result,
    ):

        print(
            f"p{percentile}: "
            f"{value}"
        )


print_exact_percentiles(
    "laiCw [g/m²]",
    lai_values,
)


print_exact_percentiles(
    "Absolute uncertainty [g/m²]",
    unc_values,
)


print_exact_percentiles(
    "Relative uncertainty — saved [%]",
    ru_saved,
)


print_exact_percentiles(
    "Relative uncertainty — recomputed [%]",
    ru_recomputed,
)


print_exact_percentiles(
    "NDVI",
    ndvi_values,
)


# ======================================================
# Exact threshold counts
# ======================================================

print(
    "\nExact RU threshold retention:"
)


for threshold in [
    20,
    30,
    40,
]:

    retained = (
        ru_recomputed
        < threshold
    ).sum()

    percent = (
        100
        * retained
        / len(ru_recomputed)
    )

    print(
        f"RU < {threshold}%: "
        f"{percent:.2f}%"
    )


print(
    "\nRU minimum:",
    float(
        np.min(
            ru_recomputed
        )
    ),
)


print(
    "RU maximum:",
    float(
        np.max(
            ru_recomputed
        )
    ),
)

# ======================================================
# 17. PERCENTILE HELPER
# ======================================================

def percentiles(
    collection,
    property_name,
):

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


# ======================================================
# 18. DISTRIBUTIONS
# ======================================================

lai_stats = percentiles(
    sample,
    "laiCw",
)


unc_stats = percentiles(
    sample,
    "laiCw_UNCERTAINTY",
)


ru_stats = percentiles(
    sample,
    "relative_uncertainty_pct",
)


ndvi_stats = percentiles(
    sample,
    "current_ndvi",
)


print("\n" + "=" * 82)
print("MARCH VALID-AREA DISTRIBUTIONS")
print("=" * 82)


print("\nlaiCw [g/m²]")

for key, value in lai_stats.items():
    print(
        f"{key}: {value}"
    )


print("\nAbsolute uncertainty [g/m²]")

for key, value in unc_stats.items():
    print(
        f"{key}: {value}"
    )


print("\nRelative uncertainty [%]")

for key, value in ru_stats.items():
    print(
        f"{key}: {value}"
    )


print("\nContemporaneous NDVI")

for key, value in ndvi_stats.items():
    print(
        f"{key}: {value}"
    )


# ======================================================
# 19. REFERENCE-RANGE DIAGNOSTIC
# ======================================================

REFERENCE_MIN = 32.1
REFERENCE_MAX = 887.9


below = (
    sample
    .filter(
        ee.Filter.lt(
            "laiCw",
            REFERENCE_MIN,
        )
    )
    .size()
    .getInfo()
)


within = (
    sample
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


above = (
    sample
    .filter(
        ee.Filter.gt(
            "laiCw",
            REFERENCE_MAX,
        )
    )
    .size()
    .getInfo()
)


print("\n" + "=" * 82)
print("REFERENCE-RANGE DIAGNOSTIC")
print("=" * 82)


print(
    f"Below {REFERENCE_MIN}: "
    f"{100 * below / sample_count:.2f}%"
)

print(
    f"Within {REFERENCE_MIN}–{REFERENCE_MAX}: "
    f"{100 * within / sample_count:.2f}%"
)

print(
    f"Above {REFERENCE_MAX}: "
    f"{100 * above / sample_count:.2f}%"
)


# ======================================================
# 20. UNCERTAINTY SENSITIVITY
# ======================================================

print("\n" + "=" * 82)
print("RELATIVE-UNCERTAINTY SENSITIVITY")
print("=" * 82)


for threshold in [
    20,
    30,
    40,
]:

    n = (
        sample
        .filter(
            ee.Filter.lt(
                "relative_uncertainty_pct",
                threshold,
            )
        )
        .size()
        .getInfo()
    )

    pct = (
        100
        * n
        / sample_count
    )

    print(
        f"RU < {threshold}%: "
        f"{pct:.2f}%"
    )


# ======================================================
# 21. FINAL STATUS
# ======================================================

print("\n" + "=" * 82)
print("✅ STEP 13B MARCH QA COMPLETE")
print("=" * 82)

print(
    "No missing pixels were spatially filled."
)

print(
    "No interpolation was performed."
)

print(
    "No production assets or GeoTIFFs were exported."
)

print(
    "The March window remains classified as LIMITED "
    "until this QA result is reviewed."
)