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


print("=" * 80)
print("STEP 11 — 10-DAY vs 15-DAY TEMPORAL COMPOSITE COMPARISON")
print("=" * 80)


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

print(
    f"Study AOI area: {area_km2:.2f} km²"
)


# ======================================================
# 3. STUDY PERIOD
# ======================================================

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


# ======================================================
# 4. QA60 MASK
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
# 5. CLEAR COVERAGE
# ======================================================

def clear_coverage_percent(
    collection,
    geometry,
):

    scene_count = (
        collection
        .size()
        .getInfo()
    )

    if scene_count == 0:

        return 0.0

    clear_count = (
        collection
        .map(mask_qa60)
        .select("B4")
        .count()
    )

    valid_any = (
        clear_count
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


# ======================================================
# 6. WINDOW STATUS
# ======================================================

def classify_window(
    l1c_count,
    l1c_clear,
    l2a_count,
    l2a_clear,
):

    # POOR:
    # one required data stream is missing
    # or spatial clear coverage is seriously incomplete.

    if (
        l1c_count == 0
        or l2a_count == 0
        or l1c_clear < 50
        or l2a_clear < 50
    ):

        return "POOR"

    # LIMITED:
    # usable, but based on only one scene
    # or less than 90% clear coverage.

    if (
        l1c_count == 1
        or l2a_count == 1
        or l1c_clear < 90
        or l2a_clear < 90
    ):

        return "LIMITED"

    return "GOOD"


# ======================================================
# 7. AUDIT FUNCTION
# ======================================================

def audit_composite_length(
    composite_days,
):

    full_windows = (
        total_days
        // composite_days
    )

    remainder_days = (
        total_days
        % composite_days
    )


    print("\n" + "=" * 80)

    print(
        f"{composite_days}-DAY COMPOSITE AUDIT"
    )

    print("=" * 80)

    print(
        "Complete windows:",
        full_windows,
    )

    print(
        "Remainder days:",
        remainder_days,
    )


    results = []


    for i in range(full_windows):

        window_start = (
            start_date
            + timedelta(
                days=i
                * composite_days
            )
        )

        window_end = (
            window_start
            + timedelta(
                days=composite_days
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


        # ----------------------------------------------
        # L1C — PyEOGPR
        # ----------------------------------------------

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


        # ----------------------------------------------
        # L2A — NDVI / NDMI
        # ----------------------------------------------

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


        status = classify_window(
            l1c_count,
            l1c_clear,
            l2a_count,
            l2a_clear,
        )


        row = {

            "composite_days":
                composite_days,

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


    return (
        results,
        remainder_days,
    )


# ======================================================
# 8. RUN BOTH AUDITS
# ======================================================

results_10, remainder_10 = (
    audit_composite_length(10)
)


results_15, remainder_15 = (
    audit_composite_length(15)
)


# ======================================================
# 9. SUMMARIZE
# ======================================================

def summarize(
    results,
):

    return {

        "GOOD": sum(
            row["status"] == "GOOD"
            for row in results
        ),

        "LIMITED": sum(
            row["status"] == "LIMITED"
            for row in results
        ),

        "POOR": sum(
            row["status"] == "POOR"
            for row in results
        ),

        "TOTAL": len(results),

    }


summary_10 = summarize(
    results_10
)

summary_15 = summarize(
    results_15
)


print("\n" + "=" * 80)
print("COMPARATIVE SUMMARY")
print("=" * 80)


print("\n10-day composites")

for key, value in summary_10.items():

    print(
        f"{key}: {value}"
    )


print(
    "Remainder days:",
    remainder_10,
)


print("\n15-day composites")

for key, value in summary_15.items():

    print(
        f"{key}: {value}"
    )


print(
    "Remainder days:",
    remainder_15,
)


# ======================================================
# 10. SIMPLE DECISION SUPPORT
# ======================================================

print("\n" + "=" * 80)
print("TEMPORAL DESIGN DIAGNOSTIC")
print("=" * 80)


if (
    summary_15["POOR"] == 0
    and summary_15["GOOD"]
    > summary_15["LIMITED"]
):

    recommendation = (
        "15-DAY COMPOSITES LOOK SUITABLE "
        "FOR PRODUCTION."
    )

elif (
    summary_15["POOR"]
    < summary_10["POOR"]
):

    recommendation = (
        "15-DAY COMPOSITES IMPROVE COVERAGE, "
        "BUT LIMITED WINDOWS STILL REQUIRE REVIEW."
    )

else:

    recommendation = (
        "15-DAY COMPOSITES DO NOT FULLY SOLVE "
        "THE TEMPORAL-COVERAGE PROBLEM."
    )


print(recommendation)


# ======================================================
# 11. SAVE COMBINED CSV
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
    / "temporal_resolution_comparison.csv"
)


all_results = (
    results_10
    + results_15
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
            "composite_days",
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
        all_results
    )


print(
    "\nCSV saved to:",
    csv_path,
)


# ======================================================
# 12. FINAL STATUS
# ======================================================

print("\n" + "=" * 80)
print("✅ STEP 11 TEMPORAL COMPARISON COMPLETE")
print("=" * 80)

print(
    "No final temporal resolution has yet been frozen."
)

print(
    "No full-season PyEOGPR retrieval has been run."
)

print(
    "No Earth Engine assets or GeoTIFFs were exported."
)