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


print("=" * 82)
print("STEP 12 — SENTINEL-2 SCENE CLOUD-THRESHOLD AUDIT")
print("=" * 82)


# ======================================================
# 1. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")


# ======================================================
# 2. STUDY AREA
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

print(f"Study AOI area: {area_km2:.2f} km²")


# ======================================================
# 3. TEMPORAL DESIGN
# ======================================================

COMPOSITE_DAYS = 15

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
    "Composite interval:",
    COMPOSITE_DAYS,
    "days",
)

print(
    "Complete windows:",
    full_windows,
)

print(
    "Remainder days:",
    remainder_days,
)


# ======================================================
# 4. CLOUD THRESHOLDS TO TEST
# ======================================================

# None means:
# no scene-level CLOUDY_PIXEL_PERCENTAGE filter.
#
# QA60 pixel masking is still applied.

CLOUD_THRESHOLDS = [
    40,
    60,
    80,
    None,
]


# ======================================================
# 5. QA60 PIXEL MASK
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
# 6. APPLY OPTIONAL SCENE-CLOUD FILTER
# ======================================================

def apply_cloud_threshold(
    collection,
    threshold,
):

    if threshold is None:

        return collection

    return collection.filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            threshold,
        )
    )


# ======================================================
# 7. CLEAR AOI COVERAGE
# ======================================================

def clear_coverage_percent(
    collection,
    geometry,
):

    count = (
        collection
        .size()
        .getInfo()
    )

    if count == 0:

        return 0.0


    valid_any = (
        collection
        .map(mask_qa60)
        .select("B4")
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


    if valid_area is None:

        return 0.0


    total_area = geometry.area(
        maxError=1
    )


    return (
        ee.Number(valid_area)
        .divide(total_area)
        .multiply(100)
        .getInfo()
    )


# ======================================================
# 8. WINDOW CLASSIFICATION
# ======================================================

def classify(
    l1c_count,
    l1c_clear,
    l2a_count,
    l2a_clear,
):

    if (
        l1c_count == 0
        or l2a_count == 0
        or l1c_clear < 50
        or l2a_clear < 50
    ):

        return "POOR"


    if (
        l1c_count == 1
        or l2a_count == 1
        or l1c_clear < 90
        or l2a_clear < 90
    ):

        return "LIMITED"


    return "GOOD"


# ======================================================
# 9. STORAGE
# ======================================================

results = []


# ======================================================
# 10. LOOP OVER CLOUD THRESHOLDS
# ======================================================

for threshold in CLOUD_THRESHOLDS:

    if threshold is None:

        threshold_label = "NONE"

    else:

        threshold_label = str(threshold)


    print("\n" + "=" * 82)

    print(
        "SCENE CLOUD THRESHOLD:",
        threshold_label,
    )

    print("=" * 82)


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


        start_text = (
            window_start
            .strftime("%Y-%m-%d")
        )

        end_text = (
            window_end
            .strftime("%Y-%m-%d")
        )


        # --------------------------------------------------
        # Sentinel-2 L1C
        # --------------------------------------------------

        l1c_base = (
            ee.ImageCollection(
                "COPERNICUS/S2_HARMONIZED"
            )
            .filterBounds(aoi)
            .filterDate(
                start_text,
                end_text,
            )
        )


        l1c = apply_cloud_threshold(
            l1c_base,
            threshold,
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
        # --------------------------------------------------

        l2a_base = (
            ee.ImageCollection(
                "COPERNICUS/S2_SR_HARMONIZED"
            )
            .filterBounds(aoi)
            .filterDate(
                start_text,
                end_text,
            )
        )


        l2a = apply_cloud_threshold(
            l2a_base,
            threshold,
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


        status = classify(
            l1c_count,
            l1c_clear,
            l2a_count,
            l2a_clear,
        )


        row = {

            "cloud_threshold":
                threshold_label,

            "window":
                i + 1,

            "start":
                start_text,

            "end_exclusive":
                end_text,

            "l1c_scene_count":
                l1c_count,

            "l1c_clear_coverage_pct":
                round(
                    l1c_clear,
                    2,
                ),

            "l2a_scene_count":
                l2a_count,

            "l2a_clear_coverage_pct":
                round(
                    l2a_clear,
                    2,
                ),

            "status":
                status,
        }


        results.append(row)


        print(
            f"\nWindow {i + 1:02d}: "
            f"{start_text} → {end_text}"
        )

        print(
            f"  L1C: "
            f"{l1c_count} scenes, "
            f"{l1c_clear:.2f}% clear"
        )

        print(
            f"  L2A: "
            f"{l2a_count} scenes, "
            f"{l2a_clear:.2f}% clear"
        )

        print(
            "  Status:",
            status,
        )


# ======================================================
# 11. SUMMARY BY THRESHOLD
# ======================================================

print("\n" + "=" * 82)
print("THRESHOLD COMPARISON SUMMARY")
print("=" * 82)


for threshold in CLOUD_THRESHOLDS:

    if threshold is None:

        threshold_label = "NONE"

    else:

        threshold_label = str(threshold)


    subset = [
        row
        for row in results
        if row["cloud_threshold"]
        == threshold_label
    ]


    good = sum(
        row["status"] == "GOOD"
        for row in subset
    )


    limited = sum(
        row["status"] == "LIMITED"
        for row in subset
    )


    poor = sum(
        row["status"] == "POOR"
        for row in subset
    )


    print(
        f"\nThreshold: {threshold_label}"
    )

    print(
        "GOOD:",
        good,
    )

    print(
        "LIMITED:",
        limited,
    )

    print(
        "POOR:",
        poor,
    )


# ======================================================
# 12. IDENTIFY RESCUED WINDOWS
# ======================================================

print("\n" + "=" * 82)
print("WINDOWS RESCUED RELATIVE TO CURRENT <40% FILTER")
print("=" * 82)


baseline = {

    row["window"]:
        row

    for row in results

    if row["cloud_threshold"] == "40"
}


for threshold_label in [
    "60",
    "80",
    "NONE",
]:

    print(
        f"\nUsing threshold: {threshold_label}"
    )


    comparison = {

        row["window"]:
            row

        for row in results

        if (
            row["cloud_threshold"]
            == threshold_label
        )
    }


    rescued_any = False


    for window_number in baseline:

        before = (
            baseline[
                window_number
            ]["status"]
        )


        after = (
            comparison[
                window_number
            ]["status"]
        )


        if (
            before == "POOR"
            and after != "POOR"
        ):

            rescued_any = True

            row = comparison[
                window_number
            ]


            print(
                f"  Window {window_number:02d}: "
                f"POOR → {after}"
            )

            print(
                f"    "
                f"{row['start']} → "
                f"{row['end_exclusive']}"
            )

            print(
                f"    L1C: "
                f"{row['l1c_scene_count']} scenes, "
                f"{row['l1c_clear_coverage_pct']}%"
            )

            print(
                f"    L2A: "
                f"{row['l2a_scene_count']} scenes, "
                f"{row['l2a_clear_coverage_pct']}%"
            )


    if not rescued_any:

        print(
            "  No POOR windows rescued."
        )


# ======================================================
# 13. SAVE CSV
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
    / "cloud_threshold_audit.csv"
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
            "cloud_threshold",
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


print(
    "\nCSV saved to:",
    csv_path,
)


# ======================================================
# 14. FINAL STATUS
# ======================================================

print("\n" + "=" * 82)
print("✅ STEP 12 CLOUD-THRESHOLD AUDIT COMPLETE")
print("=" * 82)

print(
    "No PyEOGPR cloud threshold has been modified."
)

print(
    "No final temporal design has been frozen."
)

print(
    "No seasonal retrievals or exports were performed."
)