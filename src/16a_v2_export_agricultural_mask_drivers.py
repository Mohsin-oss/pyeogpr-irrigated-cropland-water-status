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
from config.study_config import STUDY_BBOX


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
    "20251115_20260415_v2"
)

NODATA_VALUE = -9999.0


print("=" * 90)
print("STEP 16A-v2 — CORRECTED AGRICULTURAL-MASK DRIVER EXPORT")
print("=" * 90)


# ======================================================
# 1. READ REFERENCE PRODUCTION GRID
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


CRS_TRANSFORM = [

    reference_transform.a,
    reference_transform.b,
    reference_transform.c,

    reference_transform.d,
    reference_transform.e,
    reference_transform.f,
]


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

print(
    "CRS transform:",
    CRS_TRANSFORM,
)


if reference_crs != "EPSG:32643":

    raise RuntimeError(
        f"Unexpected CRS: "
        f"{reference_crs}"
    )


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
# 3. GEOMETRIES
# ======================================================

# Source-data filtering uses the original geographic
# study bbox.

source_aoi = ee.Geometry.Rectangle(
    STUDY_BBOX,
    proj="EPSG:4326",
    geodesic=False,
)


# Export geometry corresponds exactly to the existing
# 20 m UTM production raster.

export_region = ee.Geometry.Rectangle(
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
# 4. SEASON SETTINGS
# ======================================================

SEASON_START = "2025-11-15"
SEASON_END = "2026-04-15"

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

    return image.updateMask(
        clear
    )


# ======================================================
# 6. DYNAMIC WORLD COLLECTION
# ======================================================

dw = (
    ee.ImageCollection(
        "GOOGLE/DYNAMICWORLD/V1"
    )
    .filterBounds(
        source_aoi
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


# ======================================================
# 7. GET A MEANINGFUL NATIVE DW PROJECTION
# ======================================================

dw_reference = (
    ee.Image(
        dw.first()
    )
    .select(
        "label"
    )
)


dw_projection = (
    dw_reference
    .projection()
)


print(
    "Dynamic World native projection:",
    dw_projection.getInfo(),
)

print(
    "Dynamic World nominal scale:",
    dw_projection
    .nominalScale()
    .getInfo(),
)


# ======================================================
# 8. TEMPORAL CLASS-FREQUENCY COMPOSITES
# ======================================================

def make_class_frequency(
    class_id,
    band_name,
):

    composite = (

        dw
        .map(

            lambda image:

            image
            .select(
                "label"
            )
            .eq(
                class_id
            )
            .rename(
                band_name
            )

        )
        .mean()
        .rename(
            band_name
        )

        # IMPORTANT:
        # ImageCollection reductions may otherwise have
        # the default WGS84 / 1-degree projection.
        .setDefaultProjection(
            dw_projection
        )
    )

    return composite


crop_frequency_10m = (
    make_class_frequency(
        4,
        "crop_frequency",
    )
)


built_frequency_10m = (
    make_class_frequency(
        6,
        "built_frequency",
    )
)


water_frequency_10m = (
    make_class_frequency(
        0,
        "water_frequency",
    )
)


# ======================================================
# 9. SENTINEL-2 COLLECTION
# ======================================================

s2 = (
    ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )
    .filterBounds(
        source_aoi
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
    "\nSentinel-2 L2A scenes "
    f"<{MASK_SCENE_CLOUD_THRESHOLD}%:",
    s2_count,
)


if s2_count == 0:

    raise RuntimeError(
        "No Sentinel-2 observations."
    )


# ======================================================
# 10. GET NATIVE 10 m S2 PROJECTION
# ======================================================

s2_reference = (
    ee.Image(
        s2.first()
    )
    .select(
        "B8"
    )
)


s2_projection = (
    s2_reference
    .projection()
)


print(
    "Sentinel-2 B8 projection:",
    s2_projection.getInfo(),
)

print(
    "Sentinel-2 B8 nominal scale:",
    s2_projection
    .nominalScale()
    .getInfo(),
)


# ======================================================
# 11. SEASONAL MAXIMUM NDVI
# ======================================================

def calculate_ndvi(image):

    clear = (
        mask_qa60(
            image
        )
    )

    return (

        clear
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


seasonal_max_ndvi_10m = (

    s2
    .map(
        calculate_ndvi
    )
    .max()
    .rename(
        "seasonal_max_ndvi"
    )

    # Restore meaningful native scale to the
    # ImageCollection composite.
    .setDefaultProjection(
        s2_projection
    )
)


# ======================================================
# 12. AGGREGATE 10 m → 20 m
# ======================================================

# The production analysis grid is 20 m.
#
# The driver layers are continuous:
#
# - crop/built/water frequency = proportion/frequency
# - seasonal maximum NDVI = continuous vegetation metric
#
# Therefore, aggregate native ~10 m values using MEAN
# when Earth Engine maps them to the target 20 m grid.
#
# Do NOT use resample("bilinear") on these composites.


def aggregate_to_target(
    image,
):

    return (
        image
        .reduceResolution(
            reducer=ee.Reducer.mean(),
            maxPixels=1024,
        )
    )


crop_frequency = (
    aggregate_to_target(
        crop_frequency_10m
    )
)


built_frequency = (
    aggregate_to_target(
        built_frequency_10m
    )
)


water_frequency = (
    aggregate_to_target(
        water_frequency_10m
    )
)


seasonal_max_ndvi = (
    aggregate_to_target(
        seasonal_max_ndvi_10m
    )
)


# ======================================================
# 13. BUILD DRIVER STACK
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
        f"Unexpected bands: "
        f"{actual_bands}"
    )


# ======================================================
# 14. PRE-EXPORT SPATIAL-VARIATION CHECK
# ======================================================

# This diagnostic is intentionally included because the
# failed v1 product was spatially constant.

print("\n" + "=" * 90)
print("PRE-EXPORT DRIVER RANGE CHECK")
print("=" * 90)


range_stats = (

    drivers
    .reduceRegion(

        reducer=(
            ee.Reducer.minMax()
        ),

        geometry=source_aoi,

        crs=reference_crs,

        scale=20,

        maxPixels=1e7,

        tileScale=4,
    )
    .getInfo()
)


for band_name in EXPECTED_BANDS:

    minimum = range_stats.get(
        band_name + "_min"
    )

    maximum = range_stats.get(
        band_name + "_max"
    )

    print(
        f"{band_name}: "
        f"min={minimum}, "
        f"max={maximum}"
    )


# ======================================================
# 15. FAIL IF ALL FOUR DRIVERS ARE CONSTANT
# ======================================================

constant_bands = []


for band_name in EXPECTED_BANDS:

    minimum = range_stats.get(
        band_name + "_min"
    )

    maximum = range_stats.get(
        band_name + "_max"
    )


    if (
        minimum is not None
        and maximum is not None
        and abs(
            maximum
            - minimum
        ) < 1e-10
    ):

        constant_bands.append(
            band_name
        )


if len(
    constant_bands
) == len(
    EXPECTED_BANDS
):

    raise RuntimeError(
        "All four driver layers are "
        "still spatially constant. "
        "Export aborted."
    )


if constant_bands:

    print(
        "\n⚠️ Constant bands detected:",
        constant_bands,
    )

else:

    print(
        "\n✅ All four driver layers "
        "show spatial variation."
    )


# ======================================================
# 16. EXPORT
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
            "Agricultural_Mask_Drivers_v2_"
            "20251115_20260415"
        ),

        folder=DRIVE_FOLDER,

        fileNamePrefix=(
            FILE_BASENAME
        ),

        region=export_region,

        crs=reference_crs,

        crsTransform=(
            CRS_TRANSFORM
        ),

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
    "\nStarting corrected export..."
)


task.start()


print(
    "Task ID:",
    task.id,
)

print(
    "Expected file:",
    FILE_BASENAME + ".tif",
)


# ======================================================
# 17. MONITOR
# ======================================================

POLL_SECONDS = 15


while True:

    status = (
        task.status()
    )

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


if state != "COMPLETED":

    print(status)

    raise RuntimeError(
        f"Export ended with "
        f"state {state}"
    )


# ======================================================
# 18. MANIFEST
# ======================================================

manifest = {

    "version":
        "v2_projection_corrected",

    "reason_for_v2":
        (
            "v1 incorrectly applied resample() "
            "to ImageCollection composites with "
            "default WGS84 1-degree projection, "
            "producing spatially constant drivers."
        ),

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

    "temporal_composites":
        {
            "class_frequency":
                "mean of binary class indicators",

            "seasonal_ndvi":
                "maximum NDVI",
        },

    "native_projection_restoration":
        (
            "setDefaultProjection() using "
            "source 10 m image projection"
        ),

    "spatial_aggregation_10m_to_20m":
        "reduceResolution(mean)",

    "bilinear_resampling":
        False,

    "pre_export_ranges":
        range_stats,

    "thresholds_applied":
        False,

    "nodata":
        NODATA_VALUE,

    "earth_engine_task_id":
        task.id,

    "filename":
        FILE_BASENAME + ".tif",
}


manifest_path = (
    OUTPUT_DIR
    / (
        "agricultural_mask_drivers_"
        "v2_manifest.json"
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


print("\n" + "=" * 90)
print("✅ STEP 16A-v2 COMPLETE")
print("=" * 90)


print(
    "\nManifest:",
    manifest_path,
)

print(
    "\nNo agricultural threshold "
    "has been frozen."
)