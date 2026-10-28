from pathlib import Path
import sys
import json
import time

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


print("=" * 84)
print("STEP 14A — FIRST PRODUCTION-FORMAT PyEOGPR EXPORT")
print("=" * 84)


# ======================================================
# 1. FROZEN PRODUCTION SETTINGS
# ======================================================

WINDOW_ID = "W06"

WINDOW_START = "2026-01-29"
WINDOW_END = "2026-02-13"

COMPOSITE_DAYS = 15

SCENE_CLOUD_THRESHOLD = 80

TRAITS = [
    "Cw",
    "laiCw",
    "LAI",
]

NODATA_VALUE = -9999.0

# Lower Chenab / study AOI lies in UTM Zone 43N.
EXPORT_CRS = "EPSG:32643"

DRIVE_FOLDER = "PyEOGPR_production"

FILE_BASENAME = (
    f"pyeogpr_{WINDOW_ID}_"
    f"20260129_20260213_clean"
)

# ======================================================
# 2. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")

print("\nFrozen production settings:")

print("Window:", WINDOW_ID)
print("Dates:", WINDOW_START, "to", WINDOW_END)
print("Composite length:", COMPOSITE_DAYS, "days")
print("Scene cloud threshold:", f"<{SCENE_CLOUD_THRESHOLD}%")
print("Spatial resolution:", SPATIAL_RESOLUTION, "m")
print("Export CRS:", EXPORT_CRS)
print("NoData:", NODATA_VALUE)


# ======================================================
# 3. CREATE AOI
# ======================================================

aoi = ee.Geometry.Rectangle(
    STUDY_BBOX
)


# ======================================================
# 4. RUN ALL THREE PyEOGPR RETRIEVALS
# ======================================================

retrievals = {}

scene_counts = {}


for trait in TRAITS:

    print("\n" + "-" * 84)

    print(
        f"Preparing {trait}"
    )

    print("-" * 84)


    job = EarthEngine(
        projectID=GEE_PROJECT_ID,
        sensor="SENTINEL2_L1C",
        biovar=trait,
        bounding_box=STUDY_BBOX,
        temporal_extent=[
            WINDOW_START,
            WINDOW_END,
        ],
        spatial_resolution=SPATIAL_RESOLUTION,
        cloudmask=True,
        scene_cloud_threshold=SCENE_CLOUD_THRESHOLD,
    )


    source_collection = (
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


    scene_count = (
        source_collection
        .size()
        .getInfo()
    )


    scene_counts[trait] = (
        scene_count
    )


    print(
        "Source L1C scenes:",
        scene_count,
    )


    if scene_count == 0:

        raise RuntimeError(
            f"No Sentinel-2 scenes available "
            f"for {trait}."
        )


    retrieval = (
        job
        .calculate_GREEN(
            ee.Date(WINDOW_START),
            ee.Date(WINDOW_END),
            trait,
        )
    )


    expected_bands = [
        trait,
        trait + "_UNCERTAINTY",
    ]


    actual_bands = (
        retrieval
        .bandNames()
        .getInfo()
    )


    print(
        "Bands:",
        actual_bands,
    )


    if actual_bands != expected_bands:

        raise RuntimeError(
            f"Unexpected bands for "
            f"{trait}: {actual_bands}"
        )


    retrievals[trait] = (
        retrieval
        .select(
            expected_bands
        )
    )


    print(
        f"✅ {trait} ready."
    )


# ======================================================
# 5. COMBINE INTO SIX-BAND PRODUCT
# ======================================================

product = ee.Image.cat(
    [
        retrievals["Cw"],
        retrievals["laiCw"],
        retrievals["LAI"],
    ]
)


EXPECTED_BANDS = [
    "Cw",
    "Cw_UNCERTAINTY",
    "laiCw",
    "laiCw_UNCERTAINTY",
    "LAI",
    "LAI_UNCERTAINTY",
]


actual_product_bands = (
    product
    .bandNames()
    .getInfo()
)


print("\n" + "=" * 84)
print("SIX-BAND PRODUCT")
print("=" * 84)

print(
    "Bands:",
    actual_product_bands,
)


if actual_product_bands != EXPECTED_BANDS:

    raise RuntimeError(
        "Six-band product has unexpected "
        f"band order: {actual_product_bands}"
    )


# ======================================================
# ======================================================
# 6. MASK NON-FINITE VALUES + EXPLICIT NODATA
# ======================================================

# PyEOGPR/GPR calculations can produce NaN values at
# some pixels even though the Earth Engine pixel mask
# itself remains valid.
#
# ee.Image.unmask() only fills pixels where mask == 0.
# It does NOT replace NaN values that exist inside
# otherwise valid pixels.
#
# Therefore:
#
# 1. Identify numerically valid values.
# 2. Require all six bands to be numerically valid.
# 3. Convert any non-finite pixel to an EE masked pixel.
# 4. Convert those masked pixels to -9999 for GeoTIFF.
#
# product.eq(product) is False for NaN because:
# NaN != NaN.
#
# The magnitude check additionally excludes infinite /
# absurd floating-point values.

not_nan = (
    product
    .eq(product)
)


reasonable_magnitude = (
    product
    .abs()
    .lt(1e30)
)


bandwise_finite = (
    not_nan
    .And(
        reasonable_magnitude
    )
)


# Require validity in ALL six bands.
common_finite_mask = (
    bandwise_finite
    .reduce(
        ee.Reducer.min()
    )
)


clean_product = (
    product
    .updateMask(
        common_finite_mask
    )
)


export_image = (
    clean_product
    .toFloat()
    .unmask(
        NODATA_VALUE
    )
)

# ======================================================

# ======================================================
# 7. CREATE DRIVE EXPORT TASK
# ======================================================

description = (
    f"PyEOGPR_{WINDOW_ID}_"
    f"20260129_20260213"
)


task = (
    ee.batch.Export.image.toDrive(
        image=export_image,
        description=description,
        folder=DRIVE_FOLDER,
        fileNamePrefix=FILE_BASENAME,
        region=aoi,
        scale=SPATIAL_RESOLUTION,
        crs=EXPORT_CRS,
        maxPixels=1e8,
        fileFormat="GeoTIFF",
        formatOptions={
            "cloudOptimized": True,
            "noData": NODATA_VALUE,
        },
    )
)


# ======================================================
# 8. START EXPORT
# ======================================================

print("\nStarting Earth Engine export...")

task.start()


task_id = task.id

print(
    "Task ID:",
    task_id,
)

print(
    "Google Drive folder:",
    DRIVE_FOLDER,
)

print(
    "Expected filename:",
    FILE_BASENAME + ".tif",
)


# ======================================================
# 9. MONITOR TASK
# ======================================================

POLL_SECONDS = 15


while True:

    status = task.status()

    state = status.get(
        "state",
        "UNKNOWN",
    )


    print(
        "Export state:",
        state,
    )


    if state in [
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    ]:

        break


    time.sleep(
        POLL_SECONDS
    )


# ======================================================
# 10. CHECK FINAL TASK STATE
# ======================================================

if state != "COMPLETED":

    print(
        "\nExport did not complete."
    )

    print(
        "Earth Engine status:",
        status,
    )

    raise RuntimeError(
        f"Export ended with state: {state}"
    )


print(
    "\n✅ Earth Engine export completed."
)


# ======================================================
# 11. WRITE LOCAL EXPORT MANIFEST
# ======================================================

manifest_dir = (
    PROJECT_ROOT
    / "outputs"
    / "production"
)

manifest_dir.mkdir(
    parents=True,
    exist_ok=True,
)


manifest = {

    "window_id":
        WINDOW_ID,

    "window_start":
        WINDOW_START,

    "window_end_exclusive":
        WINDOW_END,

    "composite_days":
        COMPOSITE_DAYS,

    "window_status":
        "GOOD",

    "sentinel2_product":
        "COPERNICUS/S2_HARMONIZED",

    "scene_cloud_threshold_pct":
        SCENE_CLOUD_THRESHOLD,

    "pixel_cloud_mask":
        "QA60 bits 10 and 11",

    "temporal_composite":
        "mean",

    "spatial_resolution_m":
        SPATIAL_RESOLUTION,

    "export_crs":
        EXPORT_CRS,

    "nodata":
        NODATA_VALUE,

    "bands":
        EXPECTED_BANDS,

    "units": {
        "Cw":
            "cm",

        "Cw_UNCERTAINTY":
            "cm",

        "laiCw":
            "g/m2",

        "laiCw_UNCERTAINTY":
            "g/m2",

        "LAI":
            "m2/m2",

        "LAI_UNCERTAINTY":
            "m2/m2",
    },

    "scene_counts":
        scene_counts,

    "agricultural_mask_applied":
        False,

    "relative_uncertainty_applied":
        False,

    "spatial_gap_filling":
        False,

    "temporal_gap_filling":
        False,

    "earth_engine_task_id":
        task_id,

    "drive_folder":
        DRIVE_FOLDER,

    "filename":
        FILE_BASENAME + ".tif",
}


manifest_path = (
    manifest_dir
    / (
        FILE_BASENAME
        + "_manifest.json"
    )
)


with open(
    manifest_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        manifest,
        f,
        indent=2,
    )


print(
    "\nManifest saved:"
)

print(
    manifest_path
)


print("\n" + "=" * 84)
print("✅ STEP 14A EXPORT COMPLETE")
print("=" * 84)

print(
    "Download the GeoTIFF from the "
    "PyEOGPR_production folder in Google Drive."
)

print(
    "Place it in:"
)

print(
    PROJECT_ROOT
    / "outputs"
    / "production"
)

print(
    "\nDo not start full-season production yet."
)