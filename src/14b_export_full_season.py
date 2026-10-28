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

from pyeogpr import EarthEngine

from config.project_config import GEE_PROJECT_ID
from config.study_config import (
    STUDY_BBOX,
    SPATIAL_RESOLUTION,
)


print("=" * 88)
print("STEP 14B — FULL-SEASON PyEOGPR PRODUCTION EXPORT")
print("=" * 88)


# ======================================================
# 1. FROZEN PRODUCTION DESIGN
# ======================================================

SCENE_CLOUD_THRESHOLD = 80
COMPOSITE_DAYS = 15

EXPORT_CRS = "EPSG:32643"
NODATA_VALUE = -9999.0

DRIVE_FOLDER = "PyEOGPR_production"

TRAITS = [
    "Cw",
    "laiCw",
    "LAI",
]

EXPECTED_BANDS = [
    "Cw",
    "Cw_UNCERTAINTY",
    "laiCw",
    "laiCw_UNCERTAINTY",
    "LAI",
    "LAI_UNCERTAINTY",
]


# ======================================================
# 2. COMPLETE SEASON WINDOW DEFINITIONS
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
        "reason":
            "No adequate clear Sentinel-2 observations.",
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
        "reason":
            "Approximately 54.9% agricultural-domain "
            "coverage; missing pixels retained as missing.",
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
# 4. MANIFEST DIRECTORY
# ======================================================

manifest_dir = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "manifests"
)

manifest_dir.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# 5. STORAGE
# ======================================================

tasks = []

season_manifest = {

    "created":
        datetime.now().isoformat(),

    "production_design": {

        "sensor":
            "COPERNICUS/S2_HARMONIZED",

        "composite_days":
            COMPOSITE_DAYS,

        "scene_cloud_threshold_pct":
            SCENE_CLOUD_THRESHOLD,

        "pixel_cloud_mask":
            "QA60 opaque cloud + cirrus",

        "temporal_composite":
            "mean",

        "spatial_resolution_m":
            SPATIAL_RESOLUTION,

        "export_crs":
            EXPORT_CRS,

        "nodata":
            NODATA_VALUE,

        "agricultural_mask_applied":
            False,

        "relative_uncertainty_mask_applied":
            False,

        "spatial_gap_filling":
            False,

        "temporal_gap_filling":
            False,

        "raw_export_requires_local_sanitization":
            True,
    },

    "bands": {
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

    "windows": [],
}


# ======================================================
# 6. LOOP THROUGH ALL WINDOWS
# ======================================================

for window in WINDOWS:

    window_id = window["id"]
    start = window["start"]
    end = window["end"]
    status = window["status"]


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
    # Missing window
    # --------------------------------------------------

    if not window["export"]:

        print(
            "⚠️ No export created."
        )

        season_manifest[
            "windows"
        ].append({

            **window,

            "earth_engine_task_id":
                None,

            "raw_filename":
                None,

            "scene_count":
                0,
        })

        continue


    # --------------------------------------------------
    # Source scene count
    # --------------------------------------------------

    source_collection = (
        ee.ImageCollection(
            "COPERNICUS/S2_HARMONIZED"
        )
        .filterBounds(aoi)
        .filterDate(
            start,
            end,
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


    print(
        "Source L1C scenes:",
        scene_count,
    )


    if scene_count == 0:

        raise RuntimeError(
            f"{window_id} unexpectedly has "
            "zero source scenes."
        )


    # --------------------------------------------------
    # Retrieve each PyEOGPR trait
    # --------------------------------------------------

    retrievals = {}


    for trait in TRAITS:

        print(
            f"  Preparing {trait}..."
        )


        job = EarthEngine(
            projectID=GEE_PROJECT_ID,
            sensor="SENTINEL2_L1C",
            biovar=trait,
            bounding_box=STUDY_BBOX,
            temporal_extent=[
                start,
                end,
            ],
            spatial_resolution=SPATIAL_RESOLUTION,
            cloudmask=True,
            scene_cloud_threshold=SCENE_CLOUD_THRESHOLD,
        )


        retrieval = (
            job
            .calculate_GREEN(
                ee.Date(start),
                ee.Date(end),
                trait,
            )
        )


        expected = [
            trait,
            trait
            + "_UNCERTAINTY",
        ]


        actual = (
            retrieval
            .bandNames()
            .getInfo()
        )


        if actual != expected:

            raise RuntimeError(
                f"{window_id} {trait}: "
                f"unexpected bands {actual}"
            )


        retrievals[trait] = (
            retrieval
            .select(expected)
        )


        print(
            f"  ✅ {trait}"
        )


    # --------------------------------------------------
    # Six-band product
    # --------------------------------------------------

    product = ee.Image.cat(
        [
            retrievals["Cw"],
            retrievals["laiCw"],
            retrievals["LAI"],
        ]
    )


    product_bands = (
        product
        .bandNames()
        .getInfo()
    )


    if product_bands != EXPECTED_BANDS:

        raise RuntimeError(
            f"{window_id}: unexpected "
            f"six-band order {product_bands}"
        )


    # --------------------------------------------------
    # RAW production export
    #
    # IMPORTANT:
    # Earth Engine/PyEOGPR NaN values can survive
    # this export.
    #
    # They will be converted locally to -9999 by
    # the validated sanitization stage.
    # --------------------------------------------------

    export_image = (
        product
        .toFloat()
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
        f"pyeogpr_"
        f"{window_id}_"
        f"{start_compact}_"
        f"{end_compact}_raw"
    )


    description = (
        f"PyEOGPR_"
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
        "Export task started:",
        task.id,
    )


    tasks.append({

        "window_id":
            window_id,

        "start":
            start,

        "end":
            end,

        "status":
            status,

        "scene_count":
            scene_count,

        "task":
            task,

        "task_id":
            task.id,

        "basename":
            basename,
    })


    window_record = {

        **window,

        "scene_count":
            scene_count,

        "earth_engine_task_id":
            task.id,

        "raw_filename":
            basename + ".tif",

        "final_filename":
            basename.replace(
                "_raw",
                "_final",
            )
            + ".tif",

        "local_sanitization_required":
            True,
    }


    season_manifest[
        "windows"
    ].append(
        window_record
    )


    # Individual pre-export manifest

    manifest_path = (
        manifest_dir
        / (
            basename
            + "_manifest.json"
        )
    )


    with open(
        manifest_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            window_record,
            f,
            indent=2,
        )


# ======================================================
# 7. SAVE SEASON MANIFEST
# ======================================================

season_manifest_path = (
    manifest_dir
    / "pyeogpr_season_manifest.json"
)


with open(
    season_manifest_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        season_manifest,
        f,
        indent=2,
    )


print("\n" + "=" * 88)
print("ALL EXPORT TASKS SUBMITTED")
print("=" * 88)


print(
    "Tasks submitted:",
    len(tasks),
)


print(
    "Season manifest:",
    season_manifest_path,
)


# ======================================================
# 8. MONITOR ALL TASKS
# ======================================================

POLL_SECONDS = 30


while True:

    terminal_count = 0

    print(
        "\nCurrent export states:"
    )


    for item in tasks:

        task = item["task"]

        status_info = (
            task.status()
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

            terminal_count += 1


    if terminal_count == len(
        tasks
    ):

        break


    time.sleep(
        POLL_SECONDS
    )


# ======================================================
# 9. FINAL TASK SUMMARY
# ======================================================

print("\n" + "=" * 88)
print("FULL-SEASON EXPORT SUMMARY")
print("=" * 88)


failed = []


for item in tasks:

    state = item[
        "final_state"
    ]


    print(
        f"{item['window_id']}: "
        f"{state}"
    )


    if state != "COMPLETED":

        failed.append(
            item["window_id"]
        )


if failed:

    print(
        "\n❌ Some exports failed:"
    )

    for window_id in failed:

        print(
            "-",
            window_id,
        )

else:

    print(
        "\n✅ All 9 production "
        "exports completed."
    )


print(
    "\nW03 remains explicitly "
    "MISSING / NA."
)

print(
    "W09 remains explicitly "
    "LIMITED."
)

print(
    "\nNext required operation:"
)

print(
    "Download raw GeoTIFFs and "
    "run local NaN/Inf sanitization."
)

print("\n" + "=" * 88)
print("STEP 14B EXPORT STAGE COMPLETE")
print("=" * 88)