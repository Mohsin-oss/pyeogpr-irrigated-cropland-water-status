from pathlib import Path
import sys
import json
import time

import ee
import rasterio


# ======================================================
# PROJECT ROOT
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


from config.project_config import GEE_PROJECT_ID


# ======================================================
# PATHS
# ======================================================

REFERENCE_RASTER = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "final"
    / "pyeogpr_W06_20260129_20260213_final.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DRIVE_FOLDER = "PyEOGPR_mask"

FILE_BASENAME = (
    "agricultural_mask_drivers_"
    "20251115_20260415"
)

NODATA_VALUE = -9999.0


print("=" * 88)
print("STEP 16A — EXPORT AGRICULTURAL-MASK DRIVER LAYERS")
print("=" * 88)


# ======================================================
# 1. CHECK REFERENCE PRODUCTION GRID
# ======================================================

if not REFERENCE_RASTER.exists():

    raise FileNotFoundError(
        f"Reference raster not found:\n"
        f"{REFERENCE_RASTER}"
    )


with rasterio.open(
    REFERENCE_RASTER
) as src:

    reference_crs = (
        src.crs.to_string()
    )

    reference_transform = (
        src.transform
    )

    reference_bounds = (
        src.bounds
    )

    reference_width = (
        src.width
    )

    reference_height = (
        src.height
    )

    reference_resolution = (
        src.res
    )


print("\nReference production grid:")

print(
    "CRS:",
    reference_crs,
)

print(
    "Resolution:",
    reference_resolution,
)

print(
    "Dimensions:",
    reference_width,
    "x",
    reference_height,
)

print(
    "Bounds:",
    reference_bounds,
)


if reference_crs != "EPSG:32643":

    raise RuntimeError(
        f"Unexpected reference CRS: "
        f"{reference_crs}"
    )


if (
    abs(reference_resolution[0]) != 20
    or abs(reference_resolution[1]) != 20
):

    raise RuntimeError(
        "Reference raster is not 20 m."
    )


# ======================================================
# ======================================================
# 2. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(
    project=GEE_PROJECT_ID
)

print(
    "\n✅ Earth Engine initialized."
)


# ======================================================
# 3. EARTH ENGINE TARGET GRID
# ======================================================

CRS_TRANSFORM = [
    reference_transform.a,
    reference_transform.b,
    reference_transform.c,
    reference_transform.d,
    reference_transform.e,
    reference_transform.f,
]


print(
    "CRS transform:",
    CRS_TRANSFORM,
)


aoi = ee.Geometry.Rectangle(
    [
        reference_bounds.left,
        reference_bounds.bottom,
        reference_bounds.right,
        reference_bounds.top,
    ],
    proj=reference_crs,
    geodesic=False,
)
# ======================================================
# 4. FROZEN MASK PERIOD
# ======================================================

SEASON_START = "2025-11-15"
SEASON_END = "2026-04-15"

# Deliberately retain the earlier <40% threshold
# for the seasonal vegetation-domain definition.
#
# This prevents changing the agricultural domain simply
# because the PyEOGPR production scene threshold was
# later relaxed to <80%.

MASK_SCENE_CLOUD_THRESHOLD = 40


# ======================================================
# 5. QA60 MASK
# ======================================================

def mask_qa60(image):

    qa = image.select(
        "QA60"
    )

    cloud_bit = (
        1 << 10
    )

    cirrus_bit = (
        1 << 11
    )

    clear = (
        qa
        .bitwiseAnd(
            cloud_bit
        )
        .eq(0)

        .And(

            qa
            .bitwiseAnd(
                cirrus_bit
            )
            .eq(0)

        )
    )

    return (
        image
        .updateMask(
            clear
        )
    )


# ======================================================
# 6. DYNAMIC WORLD
# ======================================================

dw = (
    ee.ImageCollection(
        "GOOGLE/DYNAMICWORLD/V1"
    )
    .filterBounds(
        aoi
    )
    .filterDate(
        SEASON_START,
        SEASON_END,
    )
)


dw_count = (
    dw
    .size()
    .getInfo()
)


print(
    "\nDynamic World scenes:",
    dw_count,
)


if dw_count == 0:

    raise RuntimeError(
        "No Dynamic World observations."
    )


# Dynamic World label:
#
# 0 = water
# 4 = crops
# 6 = built


crop_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(4)
        .rename("crop_frequency")
    )
    .mean()
    .rename(
        "crop_frequency"
    )
)


built_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(6)
        .rename("built_frequency")
    )
    .mean()
    .rename(
        "built_frequency"
    )
)


water_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(0)
        .rename("water_frequency")
    )
    .mean()
    .rename(
        "water_frequency"
    )
)


# ======================================================
# 7. SEASONAL MAXIMUM NDVI
# ======================================================

s2 = (
    ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )
    .filterBounds(
        aoi
    )
    .filterDate(
        SEASON_START,
        SEASON_END,
    )
    .filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            MASK_SCENE_CLOUD_THRESHOLD,
        )
    )
)


s2_count = (
    s2
    .size()
    .getInfo()
)


print(
    "Sentinel-2 L2A scenes "
    f"<{MASK_SCENE_CLOUD_THRESHOLD}%:",
    s2_count,
)


if s2_count == 0:

    raise RuntimeError(
        "No Sentinel-2 L2A scenes "
        "available for mask construction."
    )


def add_ndvi(image):

    image = (
        mask_qa60(
            image
        )
    )

    ndvi = (
        image
        .normalizedDifference(
            [
                "B8",
                "B4",
            ]
        )
        .rename(
            "seasonal_max_ndvi"
        )
    )

    return ndvi


seasonal_max_ndvi = (
    s2
    .map(
        add_ndvi
    )
    .max()
    .rename(
        "seasonal_max_ndvi"
    )
)


# ======================================================
# 8. ALIGN CONTINUOUS DRIVER LAYERS TO PRODUCTION GRID
# ======================================================

# These are continuous quantities rather than categorical
# labels, therefore bilinear resampling is used when
# mapping the native 10 m driver layers to the 20 m
# production grid.

crop_frequency = (
    crop_frequency
    .resample(
        "bilinear"
    )
)


built_frequency = (
    built_frequency
    .resample(
        "bilinear"
    )
)


water_frequency = (
    water_frequency
    .resample(
        "bilinear"
    )
)


seasonal_max_ndvi = (
    seasonal_max_ndvi
    .resample(
        "bilinear"
    )
)


# ======================================================
# 9. BUILD FOUR-BAND DRIVER PRODUCT
# ======================================================

drivers = (
    crop_frequency

    .addBands(
        built_frequency
    )

    .addBands(
        water_frequency
    )

    .addBands(
        seasonal_max_ndvi
    )

    .toFloat()
)


EXPECTED_BANDS = [

    "crop_frequency",
    "built_frequency",
    "water_frequency",
    "seasonal_max_ndvi",
]


actual_bands = (
    drivers
    .bandNames()
    .getInfo()
)


print(
    "\nDriver bands:",
    actual_bands,
)


if actual_bands != EXPECTED_BANDS:

    raise RuntimeError(
        f"Unexpected driver bands: "
        f"{actual_bands}"
    )


# ======================================================
# 10. EXPORT
# ======================================================

export_image = (
    drivers
    .unmask(
        NODATA_VALUE
    )
)


task = (
    ee.batch.Export.image.toDrive(

        image=export_image,

        description=(
            "Agricultural_Mask_Drivers_"
            "20251115_20260415"
        ),

        folder=DRIVE_FOLDER,

        fileNamePrefix=(
            FILE_BASENAME
        ),

        region=aoi,

        crs=reference_crs,

        crsTransform=CRS_TRANSFORM,

        maxPixels=1e8,

        fileFormat="GeoTIFF",

        formatOptions={

            "cloudOptimized":
                True,

            "noData":
                NODATA_VALUE,
        },
    )
)


print(
    "\nStarting mask-driver export..."
)

task.start()


print(
    "Task ID:",
    task.id,
)

print(
    "Drive folder:",
    DRIVE_FOLDER,
)

print(
    "Expected file:",
    FILE_BASENAME + ".tif",
)


# ======================================================
# 11. MONITOR
# ======================================================

POLL_SECONDS = 15


while True:

    status = (
        task.status()
    )

    state = (
        status
        .get(
            "state",
            "UNKNOWN",
        )
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


if state != "COMPLETED":

    print(
        status
    )

    raise RuntimeError(
        f"Mask-driver export ended "
        f"with state {state}"
    )


# ======================================================
# 12. MANIFEST
# ======================================================

manifest = {

    "season_start":
        SEASON_START,

    "season_end_exclusive":
        SEASON_END,

    "reference_raster":
        str(
            REFERENCE_RASTER
        ),

    "target_crs":
        reference_crs,

    "target_resolution_m":
        20,

    "target_dimensions": [
        reference_width,
        reference_height,
    ],

    "target_transform":
        CRS_TRANSFORM,

    "bands":
        EXPECTED_BANDS,

    "dynamic_world_scene_count":
        dw_count,

    "sentinel2_scene_count":
        s2_count,

    "sentinel2_scene_cloud_threshold_pct":
        MASK_SCENE_CLOUD_THRESHOLD,

    "sentinel2_pixel_cloud_mask":
        "QA60 bits 10 and 11",

    "seasonal_ndvi_statistic":
        "maximum",

    "resampling_to_20m":
        "bilinear",

    "nodata":
        NODATA_VALUE,

    "thresholds_applied":
        False,

    "earth_engine_task_id":
        task.id,

    "filename":
        FILE_BASENAME + ".tif",
}


manifest_path = (
    OUTPUT_DIR
    / "agricultural_mask_drivers_manifest.json"
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
    "\nManifest:"
)

print(
    manifest_path
)


print("\n" + "=" * 88)
print("✅ STEP 16A COMPLETE")
print("=" * 88)

print(
    "\nNo agricultural threshold "
    "has been frozen yet."
)

print(
    "No PyEOGPR or index raster "
    "has been modified."
)