from pathlib import Path
import sys
import csv

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


print("=" * 80)
print("STEP 13A — PyEOGPR CLOUD-THRESHOLD RETRIEVAL SENSITIVITY")
print("=" * 80)


# ======================================================
# 1. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")


# ======================================================
# 2. TEST WINDOW
# ======================================================

TEST_START = "2025-11-30"
TEST_END = "2025-12-15"

THRESHOLD_A = 40
THRESHOLD_B = 80


print(
    "\nTest window:",
    TEST_START,
    "to",
    TEST_END,
)

print(
    "Thresholds:",
    THRESHOLD_A,
    "vs",
    THRESHOLD_B,
)


# ======================================================
# 3. CREATE 40% PyEOGPR JOB
# ======================================================

job40 = EarthEngine(
    projectID=GEE_PROJECT_ID,
    sensor="SENTINEL2_L1C",
    biovar="laiCw",
    bounding_box=STUDY_BBOX,
    temporal_extent=[
        TEST_START,
        TEST_END,
    ],
    spatial_resolution=SPATIAL_RESOLUTION,
    cloudmask=True,
    scene_cloud_threshold=THRESHOLD_A,
)


# ======================================================
# 4. CREATE 80% PyEOGPR JOB
# ======================================================

job80 = EarthEngine(
    projectID=GEE_PROJECT_ID,
    sensor="SENTINEL2_L1C",
    biovar="laiCw",
    bounding_box=STUDY_BBOX,
    temporal_extent=[
        TEST_START,
        TEST_END,
    ],
    spatial_resolution=SPATIAL_RESOLUTION,
    cloudmask=True,
    scene_cloud_threshold=THRESHOLD_B,
)


print("✅ Both PyEOGPR jobs created.")


# ======================================================
# 5. VERIFY SCENE COUNTS
# ======================================================

def count_scenes(
    job,
    threshold,
):

    return (
        job.imcol
        .filterBounds(job.bbox)
        .filterMetadata(
            "CLOUDY_PIXEL_PERCENTAGE",
            "less_than",
            threshold,
        )
        .size()
        .getInfo()
    )


count40 = count_scenes(
    job40,
    THRESHOLD_A,
)

count80 = count_scenes(
    job80,
    THRESHOLD_B,
)


print("\nScene counts:")

print(
    f"<{THRESHOLD_A}%:",
    count40,
)

print(
    f"<{THRESHOLD_B}%:",
    count80,
)


if count40 == 0:

    raise RuntimeError(
        "40% threshold has no scenes."
    )


if count80 == 0:

    raise RuntimeError(
        "80% threshold has no scenes."
    )


# ======================================================
# 6. RUN BOTH GPR RETRIEVALS
# ======================================================

start = ee.Date(TEST_START)
end = ee.Date(TEST_END)


print(
    f"\nRunning laiCw retrieval "
    f"with <{THRESHOLD_A}% threshold..."
)

retrieval40 = (
    job40
    .calculate_GREEN(
        start,
        end,
        "laiCw",
    )
)

print("✅ 40% retrieval created.")


print(
    f"\nRunning laiCw retrieval "
    f"with <{THRESHOLD_B}% threshold..."
)

retrieval80 = (
    job80
    .calculate_GREEN(
        start,
        end,
        "laiCw",
    )
)

print("✅ 80% retrieval created.")


# ======================================================
# 7. EXTRACT BANDS
# ======================================================

lai40 = (
    retrieval40
    .select("laiCw")
    .rename("laiCw_40")
)


lai80 = (
    retrieval80
    .select("laiCw")
    .rename("laiCw_80")
)


unc40 = (
    retrieval40
    .select("laiCw_UNCERTAINTY")
    .rename("uncertainty_40")
)


unc80 = (
    retrieval80
    .select("laiCw_UNCERTAINTY")
    .rename("uncertainty_80")
)


# ======================================================
# 8. VALID-COVERAGE FUNCTION
# ======================================================

def valid_area_percent(
    image,
    geometry,
):

    valid_area = (
        ee.Image.pixelArea()
        .updateMask(
            image.mask()
        )
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=60,
            maxPixels=1e8,
            tileScale=4,
        )
        .get("area")
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


coverage40 = valid_area_percent(
    lai40,
    job40.bbox,
)

coverage80 = valid_area_percent(
    lai80,
    job80.bbox,
)


print("\nValid retrieval coverage:")

print(
    f"<{THRESHOLD_A}%: "
    f"{coverage40:.2f}%"
)

print(
    f"<{THRESHOLD_B}%: "
    f"{coverage80:.2f}%"
)


# ======================================================
# 9. COMPARISON BANDS
# ======================================================

delta = (
    lai80
    .subtract(lai40)
    .rename("delta_80_minus_40")
)


absolute_difference = (
    delta
    .abs()
    .rename("absolute_difference")
)


# Only compute relative difference where
# the 40% retrieval is positive.

relative_difference = (
    absolute_difference
    .divide(lai40)
    .multiply(100)
    .updateMask(
        lai40.gt(0)
    )
    .rename("relative_difference_pct")
)


uncertainty_difference = (
    unc80
    .subtract(unc40)
    .rename("uncertainty_delta_80_minus_40")
)


# ======================================================
# 10. COMBINE FOR OVERLAP SAMPLE
# ======================================================

comparison = (
    lai40
    .addBands(lai80)
    .addBands(unc40)
    .addBands(unc80)
    .addBands(delta)
    .addBands(absolute_difference)
    .addBands(relative_difference)
    .addBands(uncertainty_difference)
)


# ======================================================
# 10. LIGHTWEIGHT RANDOM-POINT COMPARISON SAMPLE
# ======================================================

# Evaluating two complete GPR retrievals simultaneously
# is computationally expensive in Earth Engine.
#
# Instead of scanning the entire AOI with Image.sample(),
# generate a reproducible set of spatial points and
# evaluate the comparison image only at those locations.

QA_POINT_COUNT = 750
QA_SCALE = 60
QA_TILE_SCALE = 16
QA_SEED = 42


print("\nGenerating lightweight comparison sample...")

random_points = (
    ee.FeatureCollection.randomPoints(
        region=job40.bbox,
        points=QA_POINT_COUNT,
        seed=QA_SEED,
        maxError=1,
    )
)


required_properties = [
    "laiCw_40",
    "laiCw_80",
    "uncertainty_40",
    "uncertainty_80",
    "delta_80_minus_40",
    "absolute_difference",
    "relative_difference_pct",
    "uncertainty_delta_80_minus_40",
]


sample = (
    comparison
    .sampleRegions(
        collection=random_points,
        scale=QA_SCALE,
        geometries=False,
        tileScale=QA_TILE_SCALE,
    )
    .filter(
        ee.Filter.notNull(
            required_properties
        )
    )
)


sample_count = (
    sample
    .size()
    .getInfo()
)


print(
    "Requested random points:",
    QA_POINT_COUNT,
)

print(
    "Valid overlapping sample points:",
    sample_count,
)

print(
    "QA scale:",
    QA_SCALE,
    "m",
)

print(
    "tileScale:",
    QA_TILE_SCALE,
)


if sample_count == 0:

    raise RuntimeError(
        "No overlapping valid pixels between "
        "the 40% and 80% retrievals."
    )
# ======================================================
# 11. PERCENTILE HELPER
# ======================================================

def get_percentiles(
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
# 12. RETRIEVAL DISTRIBUTIONS
# ======================================================

stats40 = get_percentiles(
    sample,
    "laiCw_40",
)


stats80 = get_percentiles(
    sample,
    "laiCw_80",
)


print("\n" + "=" * 80)
print("laiCw DISTRIBUTIONS [g/m²]")
print("=" * 80)


print("\n<40% threshold")

for key, value in stats40.items():

    print(
        f"{key}: {value}"
    )


print("\n<80% threshold")

for key, value in stats80.items():

    print(
        f"{key}: {value}"
    )


# ======================================================
# 13. DIFFERENCE DISTRIBUTIONS
# ======================================================

delta_stats = get_percentiles(
    sample,
    "delta_80_minus_40",
)


abs_diff_stats = get_percentiles(
    sample,
    "absolute_difference",
)


rel_diff_stats = get_percentiles(
    sample,
    "relative_difference_pct",
)


unc_delta_stats = get_percentiles(
    sample,
    "uncertainty_delta_80_minus_40",
)


print("\n" + "=" * 80)
print("RETRIEVAL DIFFERENCE — 80% minus 40%")
print("=" * 80)


print("\nSigned laiCw difference [g/m²]")

for key, value in delta_stats.items():

    print(
        f"{key}: {value}"
    )


print("\nAbsolute laiCw difference [g/m²]")

for key, value in abs_diff_stats.items():

    print(
        f"{key}: {value}"
    )


print("\nAbsolute relative difference [%]")

for key, value in rel_diff_stats.items():

    print(
        f"{key}: {value}"
    )


print("\nAbsolute-uncertainty change [g/m²]")

for key, value in unc_delta_stats.items():

    print(
        f"{key}: {value}"
    )


# ======================================================
# 14. SPATIAL CORRELATION
# ======================================================

correlation = (
    sample
    .reduceColumns(
        reducer=ee.Reducer.pearsonsCorrelation(),
        selectors=[
            "laiCw_40",
            "laiCw_80",
        ],
    )
    .getInfo()
)


print("\n" + "=" * 80)
print("SPATIAL CORRELATION")
print("=" * 80)


for key, value in correlation.items():

    print(
        f"{key}: {value}"
    )


# ======================================================
# 15. MEDIAN VALUES FOR CSV
# ======================================================

summary = {

    "test_start":
        TEST_START,

    "test_end":
        TEST_END,

    "scene_count_40":
        count40,

    "scene_count_80":
        count80,

    "coverage_40_pct":
        coverage40,

    "coverage_80_pct":
        coverage80,

    "lai40_p50":
        stats40.get("p50"),

    "lai80_p50":
        stats80.get("p50"),

    "signed_difference_p50":
        delta_stats.get("p50"),

    "absolute_difference_p50":
        abs_diff_stats.get("p50"),

    "relative_difference_p50_pct":
        rel_diff_stats.get("p50"),

    "relative_difference_p95_pct":
        rel_diff_stats.get("p95"),

    "uncertainty_change_p50":
        unc_delta_stats.get("p50"),

    "correlation":
        correlation.get("correlation"),

}


# ======================================================
# 16. SAVE CSV
# ======================================================

output_dir = (
    PROJECT_ROOT
    / "outputs"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True,
)


csv_path = (
    output_dir
    / "cloud_threshold_retrieval_sensitivity.csv"
)


with open(
    csv_path,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary.keys()
        ),
    )

    writer.writeheader()

    writer.writerow(
        summary
    )


print(
    "\nCSV saved to:",
    csv_path,
)


# ======================================================
# 17. FINAL STATUS
# ======================================================

print("\n" + "=" * 80)
print("✅ STEP 13A SENSITIVITY TEST COMPLETE")
print("=" * 80)

print(
    "No production cloud threshold has yet been frozen."
)

print(
    "No seasonal assets or GeoTIFFs were exported."
)