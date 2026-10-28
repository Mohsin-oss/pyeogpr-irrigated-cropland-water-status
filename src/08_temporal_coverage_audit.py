from pathlib import Path
import sys
import csv
from datetime import datetime, timedelta

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
    STUDY_START,
    STUDY_END,
)


print("=" * 78)
print("STEP 10 — FULL-SEASON SENTINEL-2 TEMPORAL COVERAGE AUDIT")
print("=" * 78)


# ======================================================
# 1. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")


# ======================================================
# 2. FROZEN FULL STUDY AOI
# ======================================================

aoi = ee.Geometry.Rectangle(
    STUDY_BBOX
)

area_km2 = (
    aoi
    .area(maxError=1)
    .divide(1e6)
    .getInfo()
)

print(
    f"Study AOI area: {area_km2:.2f} km²"
)


# ======================================================
# 3. TEMPORAL SETTINGS
# ======================================================

COMPOSITE_DAYS = 10

start_date = datetime.strptime(
    STUDY_START,
    "%Y-%m-%d",
)

end_date = datetime.strptime(
    STUDY_END,
    "%Y-%m-%d",
)


total_days = (
    end_date - start_date
).days


full_windows = (
    total_days // COMPOSITE_DAYS
)

remainder_days = (
    total_days % COMPOSITE_DAYS
)


print("\nTemporal configuration:")
print(
    "Study period:",
    STUDY_START,
    "to",
    STUDY_END,
)
print(
    "Total days:",
    total_days,
)
print(
    "Composite interval:",
    COMPOSITE_DAYS,
    "days",
)
print(
    "Complete 10-day windows:",
    full_windows,
)
print(
    "Remaining days after complete windows:",
    remainder_days,
)


# ======================================================
# 4. CLOUD MASK
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


# ======================================================
# 5. CLEAR-AREA FUNCTION
# ======================================================

def clear_coverage_percent(
    collection,
    geometry,
):

    """
    Percentage of AOI having at least one valid
    clear B4 observation during the time window.

    Computed at 60 m for QA efficiency only.
    """

    count = collection.size().getInfo()

    if count == 0:
        return 0.0

    masked_collection = (
        collection
        .map(mask_qa60)
        .select("B4")
    )

    valid_any = (
        masked_collection
        .count()
        .gt(0)
    )

    valid_area = (
        ee.Image.pixelArea()
        .updateMask(valid_any)
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=60,
            maxPixels=1e8,
            tileScale=4,
        )
        .get("area")
    )

    total_area = geometry.area(
        maxError=1
    )

    fraction = (
        ee.Number(valid_area)
        .divide(total_area)
        .multiply(100)
        .getInfo()
    )

    return fraction


# ======================================================
# 6. OUTPUT STORAGE
# ======================================================

results = []


print("\n" + "=" * 78)
print("10-DAY WINDOW AUDIT")
print("=" * 78)


# ======================================================
# 7. LOOP THROUGH COMPLETE WINDOWS
# ======================================================

for i in range(full_windows):

    window_start = (
        start_date
        + timedelta(
            days=i * COMPOSITE_DAYS
        )
    )

    window_end = (
        window_start
        + timedelta(
            days=COMPOSITE_DAYS
        )
    )


    start_text = window_start.strftime(
        "%Y-%m-%d"
    )

    end_text = window_end.strftime(
        "%Y-%m-%d"
    )


    # --------------------------------------------------
    # Sentinel-2 L1C
    # PyEOGPR source product
    # --------------------------------------------------

    l1c = (
        ee.ImageCollection(
            "COPERNICUS/S2_HARMONIZED"
        )
        .filterBounds(aoi)
        .filterDate(
            start_text,
            end_text,
        )
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                40,
            )
        )
    )


    l1c_count = (
        l1c
        .size()
        .getInfo()
    )


    l1c_clear = (
        clear_coverage_percent(
            l1c,
            aoi,
        )
    )


    # --------------------------------------------------
    # Sentinel-2 L2A
    # NDVI / NDMI context product
    # --------------------------------------------------

    l2a = (
        ee.ImageCollection(
            "COPERNICUS/S2_SR_HARMONIZED"
        )
        .filterBounds(aoi)
        .filterDate(
            start_text,
            end_text,
        )
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                40,
            )
        )
    )


    l2a_count = (
        l2a
        .size()
        .getInfo()
    )


    l2a_clear = (
        clear_coverage_percent(
            l2a,
            aoi,
        )
    )


    # --------------------------------------------------
    # Status flag
    # --------------------------------------------------

    if (
        l1c_count == 0
        or l1c_clear < 50
    ):

        status = "POOR"

    elif (
        l1c_count == 1
        or l1c_clear < 90
    ):

        status = "LIMITED"

    else:

        status = "GOOD"


    row = {
        "window": i + 1,
        "start": start_text,
        "end_exclusive": end_text,
        "l1c_scene_count": l1c_count,
        "l1c_clear_coverage_pct": round(
            l1c_clear,
            2,
        ),
        "l2a_scene_count": l2a_count,
        "l2a_clear_coverage_pct": round(
            l2a_clear,
            2,
        ),
        "status": status,
    }


    results.append(row)


    print(
        f"\nWindow {i + 1:02d}: "
        f"{start_text} → {end_text}"
    )

    print(
        f"  L1C scenes: {l1c_count}"
    )

    print(
        f"  L1C clear coverage: "
        f"{l1c_clear:.2f}%"
    )

    print(
        f"  L2A scenes: {l2a_count}"
    )

    print(
        f"  L2A clear coverage: "
        f"{l2a_clear:.2f}%"
    )

    print(
        f"  Status: {status}"
    )


# ======================================================
# 8. REMAINDER PERIOD
# ======================================================

if remainder_days > 0:

    remainder_start = (
        start_date
        + timedelta(
            days=(
                full_windows
                * COMPOSITE_DAYS
            )
        )
    )

    print("\n" + "-" * 78)

    print(
        "NOTE: The study period contains a "
        f"{remainder_days}-day remainder:"
    )

    print(
        remainder_start.strftime(
            "%Y-%m-%d"
        ),
        "to",
        STUDY_END,
    )

    print(
        "This remainder is not included in the "
        "15 complete 10-day PyEOGPR windows."
    )


# ======================================================
# 9. SAVE CSV
# ======================================================

output_directory = (
    PROJECT_ROOT
    / "outputs"
)

output_directory.mkdir(
    parents=True,
    exist_ok=True,
)


csv_path = (
    output_directory
    / "temporal_coverage_audit.csv"
)


with open(
    csv_path,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "window",
            "start",
            "end_exclusive",
            "l1c_scene_count",
            "l1c_clear_coverage_pct",
            "l2a_scene_count",
            "l2a_clear_coverage_pct",
            "status",
        ],
    )

    writer.writeheader()

    writer.writerows(
        results
    )


print("\n" + "=" * 78)
print("SEASON SUMMARY")
print("=" * 78)


# ======================================================
# 10. SUMMARY
# ======================================================

good = sum(
    row["status"] == "GOOD"
    for row in results
)

limited = sum(
    row["status"] == "LIMITED"
    for row in results
)

poor = sum(
    row["status"] == "POOR"
    for row in results
)


print(
    "GOOD windows:",
    good,
)

print(
    "LIMITED windows:",
    limited,
)

print(
    "POOR windows:",
    poor,
)

print(
    "Total audited windows:",
    len(results),
)

print(
    "\nCSV saved to:",
    csv_path,
)


print("\n" + "=" * 78)
print("✅ STEP 10 TEMPORAL COVERAGE AUDIT COMPLETE")
print("=" * 78)

print(
    "No PyEOGPR seasonal retrievals were generated."
)

print(
    "No Earth Engine assets or GeoTIFFs were exported."
)