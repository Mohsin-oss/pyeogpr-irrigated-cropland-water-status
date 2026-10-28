from pathlib import Path
import sys
import csv
import json

import ee


# ======================================================
# PROJECT
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.project_config import GEE_PROJECT_ID
from config.study_config import STUDY_BBOX


OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "hydroclimate"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# DATASETS
# ======================================================

CHIRPS_ID = "UCSB-CHG/CHIRPS/DAILY"

ERA5_ID = (
    "ECMWF/ERA5_LAND/DAILY_AGGR"
)


# ======================================================
# WINDOWS
# ======================================================

WINDOWS = [

    {
        "id": "W01",
        "start": "2025-11-15",
        "end": "2025-11-30",
        "status": "GOOD",
    },

    {
        "id": "W02",
        "start": "2025-11-30",
        "end": "2025-12-15",
        "status": "GOOD",
    },

    {
        "id": "W03",
        "start": "2025-12-15",
        "end": "2025-12-30",
        "status": "MISSING",
    },

    {
        "id": "W04",
        "start": "2025-12-30",
        "end": "2026-01-14",
        "status": "GOOD",
    },

    {
        "id": "W05",
        "start": "2026-01-14",
        "end": "2026-01-29",
        "status": "GOOD",
    },

    {
        "id": "W06",
        "start": "2026-01-29",
        "end": "2026-02-13",
        "status": "GOOD",
    },

    {
        "id": "W07",
        "start": "2026-02-13",
        "end": "2026-02-28",
        "status": "GOOD",
    },

    {
        "id": "W08",
        "start": "2026-02-28",
        "end": "2026-03-15",
        "status": "GOOD",
    },

    {
        "id": "W09",
        "start": "2026-03-15",
        "end": "2026-03-30",
        "status": "LIMITED",
    },

    {
        "id": "W10",
        "start": "2026-03-30",
        "end": "2026-04-14",
        "status": "GOOD",
    },
]


# ======================================================
# INITIALIZE
# ======================================================

print("=" * 92)
print("STEP 18A — HYDROCLIMATIC CONTEXT EXTRACTION")
print("=" * 92)


ee.Initialize(
    project=GEE_PROJECT_ID
)


print(
    "\n✅ Earth Engine initialized."
)


aoi = ee.Geometry.Rectangle(
    STUDY_BBOX,
    proj="EPSG:4326",
    geodesic=False,
)


chirps = ee.ImageCollection(
    CHIRPS_ID
)


era5 = ee.ImageCollection(
    ERA5_ID
)


# ======================================================
# HELPERS
# ======================================================

def spatial_mean(
    image,
    band,
    scale,
):

    result = (
        image
        .select(
            band
        )
        .reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=scale,
            bestEffort=True,
            maxPixels=1e7,
        )
        .get(
            band
        )
    )

    value = (
        result
        .getInfo()
    )

    if value is None:

        return None

    return float(
        value
    )


def chirps_sum(
    start,
    end,
):

    collection = (
        chirps
        .filterBounds(
            aoi
        )
        .filterDate(
            start,
            end,
        )
        .select(
            "precipitation"
        )
    )


    count = int(
        collection
        .size()
        .getInfo()
    )


    image = (
        collection
        .sum()
    )


    rainfall = (
        spatial_mean(
            image=image,
            band="precipitation",
            scale=5566,
        )
    )


    return (
        count,
        rainfall,
    )


def era5_window(
    start,
    end,
):

    collection = (
        era5
        .filterBounds(
            aoi
        )
        .filterDate(
            start,
            end,
        )
    )


    count = int(
        collection
        .size()
        .getInfo()
    )


    mean_image = (
        collection
        .select(
            [
                "volumetric_soil_water_layer_1",
                "volumetric_soil_water_layer_2",
                "temperature_2m",
            ]
        )
        .mean()
    )


    swvl1 = spatial_mean(
        image=mean_image,
        band=(
            "volumetric_soil_water_layer_1"
        ),
        scale=11132,
    )


    swvl2 = spatial_mean(
        image=mean_image,
        band=(
            "volumetric_soil_water_layer_2"
        ),
        scale=11132,
    )


    t2m_k = spatial_mean(
        image=mean_image,
        band="temperature_2m",
        scale=11132,
    )


    return (
        count,
        swvl1,
        swvl2,
        t2m_k,
    )


# ======================================================
# EXTRACTION
# ======================================================

rows = []


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


    print("\n" + "=" * 92)

    print(
        f"{window_id}: "
        f"{start} → {end}"
    )

    print(
        "EO status:",
        window["status"],
    )


    # --------------------------------------------------
    # Number of days
    # --------------------------------------------------

    start_date = ee.Date(
        start
    )

    end_date = ee.Date(
        end
    )


    window_days = int(
        end_date
        .difference(
            start_date,
            "day",
        )
        .getInfo()
    )


    # --------------------------------------------------
    # Rainfall during current window
    # --------------------------------------------------

    (
        chirps_count,
        rainfall_window_mm,
    ) = chirps_sum(
        start,
        end,
    )


    # --------------------------------------------------
    # Antecedent 30-day rainfall
    #
    # Ends exactly when the EO window begins.
    # Therefore it does NOT include rainfall occurring
    # within the EO window itself.
    # --------------------------------------------------

    prior_start = (
        start_date
        .advance(
            -30,
            "day",
        )
        .format(
            "YYYY-MM-dd"
        )
        .getInfo()
    )


    (
        chirps_prior_count,
        rainfall_prior30_mm,
    ) = chirps_sum(
        prior_start,
        start,
    )


    # --------------------------------------------------
    # ERA5-Land
    # --------------------------------------------------

    (
        era5_count,
        swvl1,
        swvl2,
        t2m_k,
    ) = era5_window(
        start,
        end,
    )


    # --------------------------------------------------
    # Derived quantities
    # --------------------------------------------------

    if (
        swvl1 is not None
        and swvl2 is not None
    ):

        soil_water_0_28 = (

            7.0 * swvl1
            + 21.0 * swvl2

        ) / 28.0

    else:

        soil_water_0_28 = None


    if t2m_k is not None:

        t2m_c = (
            t2m_k
            - 273.15
        )

    else:

        t2m_c = None


    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    expected_days = (
        window_days
    )


    chirps_complete = (
        chirps_count
        == expected_days
    )


    era5_complete = (
        era5_count
        == expected_days
    )


    prior_complete = (
        chirps_prior_count
        == 30
    )


    print(
        "Window days:",
        window_days,
    )

    print(
        "CHIRPS images:",
        chirps_count,
        "| complete:",
        chirps_complete,
    )

    print(
        "ERA5 images:",
        era5_count,
        "| complete:",
        era5_complete,
    )

    print(
        "Prior-30d CHIRPS images:",
        chirps_prior_count,
        "| complete:",
        prior_complete,
    )


    print(
        f"Rainfall window = "
        f"{rainfall_window_mm:.2f} mm"
    )

    print(
        f"Rainfall prior 30 d = "
        f"{rainfall_prior30_mm:.2f} mm"
    )

    print(
        f"SWVL1 = "
        f"{swvl1:.4f}"
    )

    print(
        f"SWVL2 = "
        f"{swvl2:.4f}"
    )

    print(
        f"SM 0–28 cm proxy = "
        f"{soil_water_0_28:.4f}"
    )

    print(
        f"T2m = "
        f"{t2m_c:.2f} °C"
    )


    rows.append({

        "window_id":
            window_id,

        "start":
            start,

        "end_exclusive":
            end,

        "EO_status":
            window["status"],

        "window_days":
            window_days,

        "CHIRPS_daily_images":
            chirps_count,

        "CHIRPS_complete":
            chirps_complete,

        "rainfall_window_mm":
            rainfall_window_mm,

        "rainfall_prior30_mm":
            rainfall_prior30_mm,

        "rainfall_prior30_images":
            chirps_prior_count,

        "rainfall_prior30_complete":
            prior_complete,

        "ERA5_daily_images":
            era5_count,

        "ERA5_complete":
            era5_complete,

        "soil_water_layer1_m3m3":
            swvl1,

        "soil_water_layer2_m3m3":
            swvl2,

        "soil_water_0_28cm_proxy_m3m3":
            soil_water_0_28,

        "temperature_2m_C":
            t2m_c,
    })


# ======================================================
# QA
# ======================================================

print("\n" + "=" * 92)
print("HYDROCLIMATE QA")
print("=" * 92)


all_complete = True


for row in rows:

    complete = (

        row[
            "CHIRPS_complete"
        ]

        and row[
            "rainfall_prior30_complete"
        ]

        and row[
            "ERA5_complete"
        ]
    )


    print(
        f"{row['window_id']}: "
        f"{'PASS' if complete else 'CHECK'}"
    )


    if not complete:

        all_complete = False


# ======================================================
# SAVE CSV
# ======================================================

csv_path = (
    OUTPUT_DIR
    / "hydroclimate_15day_windows.csv"
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
            rows[0].keys()
        ),
    )

    writer.writeheader()

    writer.writerows(
        rows
    )


# ======================================================
# SAVE JSON
# ======================================================

json_path = (
    OUTPUT_DIR
    / "hydroclimate_15day_windows.json"
)


metadata = {

    "CHIRPS": {

        "dataset":
            CHIRPS_ID,

        "variable":
            "precipitation",

        "units":
            "mm",

        "use":
            (
                "AOI-mean precipitation "
                "temporal context"
            ),
    },

    "ERA5_Land": {

        "dataset":
            ERA5_ID,

        "variables": {

            "volumetric_soil_water_layer_1":
                "0-7 cm",

            "volumetric_soil_water_layer_2":
                "7-28 cm",

            "temperature_2m":
                "converted K to deg C",
        },

        "use":
            (
                "Coarse hydroclimatic context; "
                "not field validation or "
                "irrigation measurement."
            ),
    },

    "derived": {

        "soil_water_0_28cm_proxy":
            (
                "(7 * SWVL1 + "
                "21 * SWVL2) / 28"
            ),

        "rainfall_prior30":
            (
                "30 days immediately before "
                "each EO window start"
            ),
    },

    "windows":
        rows,
}


with open(
    json_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        metadata,
        f,
        indent=2,
    )


# ======================================================
# FINAL SUMMARY
# ======================================================

print("\n" + "=" * 92)
print("HYDROCLIMATE WINDOW SUMMARY")
print("=" * 92)


for row in rows:

    print(

        f"{row['window_id']}"

        f" | {row['EO_status']}"

        f" | P15="
        f"{row['rainfall_window_mm']:.2f} mm"

        f" | Pprior30="
        f"{row['rainfall_prior30_mm']:.2f} mm"

        f" | SM0-28="
        f"{row['soil_water_0_28cm_proxy_m3m3']:.4f}"

        f" | T2m="
        f"{row['temperature_2m_C']:.2f} °C"
    )


print(
    "\nCSV:",
    csv_path,
)

print(
    "JSON:",
    json_path,
)


if all_complete:

    print(
        "\n✅ ALL HYDROCLIMATE WINDOWS "
        "PASSED TEMPORAL COMPLETENESS QA."
    )

else:

    print(
        "\n⚠️ ONE OR MORE WINDOWS "
        "REQUIRE COVERAGE REVIEW."
    )


print("\n" + "=" * 92)
print("✅ STEP 18A COMPLETE")
print("=" * 92)