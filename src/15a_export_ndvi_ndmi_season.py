from pathlib import Path
import sys
import json
import time
from datetime import datetime

# ======================================================
# PROJECT ROOT
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ======================================================
# IMPORTS
# ======================================================

import ee

from config.project_config import GEE_PROJECT_ID
from config.study_config import (
    STUDY_BBOX,
    SPATIAL_RESOLUTION,
)


print("=" * 88)
print("STEP 15A — SEASONAL NDVI + NDMI PRODUCTION")
print("=" * 88)


# ======================================================
# 1. FROZEN SETTINGS
# ======================================================

SCENE_CLOUD_THRESHOLD = 80

EXPORT_CRS = "EPSG:32643"

NODATA_VALUE = -9999.0

DRIVE_FOLDER = "PyEOGPR_indices"

COLLECTION_ID = (
    "COPERNICUS/S2_SR_HARMONIZED"
)

EXPECTED_BANDS = [
    "NDVI",
    "NDMI",
]


# ======================================================
# 2. TEMPORAL WINDOWS
# ======================================================

WINDOWS = [

    {
        "id": "W01",
        "start": "2025-11-15",
        "end": "2025-11-30",
        "status": "GOOD",
        "export": True,
    },

    {
        "id": "W02",
        "start": "2025-11-30",
        "end": "2025-12-15",
        "status": "GOOD",
        "export": True,
    },

    {
        "id": "W03",
        "start": "2025-12-15",
        "end": "2025-12-30",
        "status": "MISSING",
        "export": False,
    },

    {
        "id": "W04",
        "start": "2025-12-30",
        "end": "2026-01-14",
        "status": "GOOD",
        "export": True,
    },

    {
        "id": "W05",
        "start": "2026-01-14",
        "end": "2026-01-29",
        "status": "GOOD",
        "export": True,
    },

    {
        "id": "W06",
        "start": "2026-01-29",
        "end": "2026-02-13",
        "status": "GOOD",
        "export": True,
    },

    {
        "id": "W07",
        "start": "2026-02-13",
        "end": "2026-02-28",
        "status": "GOOD",
        "export": True,
    },

    {
        "id": "W08",
        "start": "2026-02-28",
        "end": "2026-03-15",
        "status": "GOOD",
        "export": True,
    },

    {
        "id": "W09",
        "start": "2026-03-15",
        "end": "2026-03-30",
        "status": "LIMITED",
        "export": True,
    },

    {
        "id": "W10",
        "start": "2026-03-30",
        "end": "2026-04-14",
        "status": "GOOD",
        "export": True,
    },
]


# ======================================================
# 3. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(
    project=GEE_PROJECT_ID
)

print("✅ Earth Engine initialized.")


aoi = ee.Geometry.Rectangle(
    STUDY_BBOX
)


# ======================================================
# 4. QA60 MASK
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
# 5. MANIFEST DIRECTORY
# ======================================================

manifest_dir = (
    PROJECT_ROOT
    / "outputs"
    / "indices"
    / "manifests"
)

manifest_dir.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# 6. SEASON MANIFEST
# ======================================================

season_manifest = {

    "created":
        datetime.now().isoformat(),

    "dataset":
        COLLECTION_ID,

    "processing": {

        "scene_cloud_threshold_pct":
            SCENE_CLOUD_THRESHOLD,

        "pixel_cloud_mask":
            "QA60 bits 10 and 11",

        "temporal_composite":
            "mean surface reflectance",

        "index_timing":
            (
                "Indices calculated after "
                "mean reflectance compositing"
            ),

        "spatial_resolution_m":
            SPATIAL_RESOLUTION,

        "crs":
            EXPORT_CRS,

        "nodata":
            NODATA_VALUE,

        "agricultural_mask_applied":
            False,

        "spatial_interpolation":
            False,

        "temporal_interpolation":
            False,
    },

    "indices": {

        "NDVI":
            "(B8 - B4) / (B8 + B4)",

        "NDMI":
            "(B8 - B11) / (B8 + B11)",
    },

    "windows": [],
}


tasks = []


# ======================================================
# 7. PROCESS WINDOWS
# ======================================================

for window in WINDOWS:

    window_id = (
        window["id"]
    )

    start = (
        window["start"]
    )

    end = (
        window["end"]
    )

    status = (
        window["status"]
    )


    print("\n" + "=" * 88)

    print(
        f"{window_id}: "
        f"{start} → {end}"
    )

    print(
        "Status:",
        status,
    )

    print("=" * 88)


    # --------------------------------------------------
    # W03 remains explicitly missing
    # --------------------------------------------------

    if not window[
        "export"
    ]:

        print(
            "⚠️ No index export created."
        )

        season_manifest[
            "windows"
        ].append({

            **window,

            "scene_count":
                0,

            "task_id":
                None,

            "raw_filename":
                None,
        })

        continue


    # --------------------------------------------------
    # Collection
    # --------------------------------------------------

    collection = (
        ee.ImageCollection(
            COLLECTION_ID
        )
        .filterBounds(
            aoi
        )
        .filterDate(
            start,
            end,
        )
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                SCENE_CLOUD_THRESHOLD,
            )
        )
    )


    scene_count = (
        collection
        .size()
        .getInfo()
    )


    print(
        "L2A source scenes:",
        scene_count,
    )


    if scene_count == 0:

        raise RuntimeError(
            f"{window_id}: "
            "zero Sentinel-2 L2A scenes."
        )


    # --------------------------------------------------
    # Apply QA60 and retain required bands
    # --------------------------------------------------

    masked_collection = (
        collection
        .map(
            mask_qa60
        )
        .select(
            [
                "B4",
                "B8",
                "B11",
            ]
        )
    )


    # --------------------------------------------------
    # Mean surface-reflectance composite
    # --------------------------------------------------

    reflectance = (
        masked_collection
        .mean()
        .divide(
            10000.0
        )
        .clip(
            aoi
        )
    )


    # --------------------------------------------------
    # NDVI
    # --------------------------------------------------

    ndvi = (
        reflectance
        .normalizedDifference(
            [
                "B8",
                "B4",
            ]
        )
        .rename(
            "NDVI"
        )
    )


    # --------------------------------------------------
    # NDMI
    # --------------------------------------------------

    ndmi = (
        reflectance
        .normalizedDifference(
            [
                "B8",
                "B11",
            ]
        )
        .rename(
            "NDMI"
        )
    )


    product = (
        ndvi
        .addBands(
            ndmi
        )
        .toFloat()
    )


    product_bands = (
        product
        .bandNames()
        .getInfo()
    )


    print(
        "Output bands:",
        product_bands,
    )


    if product_bands != EXPECTED_BANDS:

        raise RuntimeError(
            f"{window_id}: "
            f"unexpected bands "
            f"{product_bands}"
        )


    # --------------------------------------------------
    # Export raw product
    # --------------------------------------------------

    export_image = (
        product
        .unmask(
            NODATA_VALUE
        )
    )


    start_compact = (
        start.replace(
            "-",
            "",
        )
    )

    end_compact = (
        end.replace(
            "-",
            "",
        )
    )


    basename = (
        f"indices_"
        f"{window_id}_"
        f"{start_compact}_"
        f"{end_compact}_raw"
    )


    description = (
        f"Indices_"
        f"{window_id}_"
        f"{start_compact}_"
        f"{end_compact}"
    )


    task = (
        ee.batch.Export.image.toDrive(
            image=export_image,
            description=description,
            folder=DRIVE_FOLDER,
            fileNamePrefix=basename,
            region=aoi,
            scale=SPATIAL_RESOLUTION,
            crs=EXPORT_CRS,
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


    task.start()


    print(
        "Export task:",
        task.id,
    )


    tasks.append({

        "window_id":
            window_id,

        "task":
            task,

        "task_id":
            task.id,

        "status":
            status,

        "scene_count":
            scene_count,

        "basename":
            basename,
    })


    season_manifest[
        "windows"
    ].append({

        **window,

        "scene_count":
            scene_count,

        "task_id":
            task.id,

        "raw_filename":
            basename + ".tif",
    })


# ======================================================
# 8. SAVE PRE-EXPORT MANIFEST
# ======================================================

manifest_path = (
    manifest_dir
    / "indices_season_manifest.json"
)


with open(
    manifest_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        season_manifest,
        f,
        indent=2,
    )


print("\n" + "=" * 88)
print("ALL INDEX EXPORT TASKS SUBMITTED")
print("=" * 88)

print(
    "Tasks:",
    len(tasks),
)

print(
    "Manifest:",
    manifest_path,
)


# ======================================================
# 9. MONITOR TASKS
# ======================================================

POLL_SECONDS = 30


while True:

    terminal = 0

    print(
        "\nCurrent states:"
    )


    for item in tasks:

        status_info = (
            item[
                "task"
            ]
            .status()
        )


        state = (
            status_info
            .get(
                "state",
                "UNKNOWN",
            )
        )


        item[
            "final_state"
        ] = state


        print(
            f"  "
            f"{item['window_id']}: "
            f"{state}"
        )


        if state in [
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        ]:

            terminal += 1


    if terminal == len(
        tasks
    ):

        break


    time.sleep(
        POLL_SECONDS
    )


# ======================================================
# 10. FINAL SUMMARY
# ======================================================

print("\n" + "=" * 88)
print("SEASONAL NDVI + NDMI EXPORT SUMMARY")
print("=" * 88)


failed = []


for item in tasks:

    state = (
        item[
            "final_state"
        ]
    )


    print(
        f"{item['window_id']}: "
        f"{state}"
    )


    if state != "COMPLETED":

        failed.append(
            item[
                "window_id"
            ]
        )


if failed:

    print(
        "\n❌ Failed index exports:"
    )

    for window_id in failed:

        print(
            "-",
            window_id,
        )

else:

    print(
        "\n✅ All 9 available "
        "NDVI/NDMI exports completed."
    )


print(
    "\nW03 remains MISSING / NA."
)

print(
    "W09 remains LIMITED."
)

print(
    "No agricultural mask applied."
)

print(
    "No interpolation performed."
)


print("\n" + "=" * 88)
print("STEP 15A COMPLETE")
print("=" * 88)