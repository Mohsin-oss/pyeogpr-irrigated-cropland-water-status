from pathlib import Path
import csv
import json

import numpy as np
import rasterio


# ======================================================
# PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MASK_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_C25_N40_final.tif"
)

PYEO_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "final"
)

INDEX_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "indices"
    / "final"
)

STEP17A_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17a"
    / "seasonal_window_statistics.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17c"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# WINDOWS
# ======================================================

WINDOWS = {

    "W01": {
        "start": "2025-11-15",
        "end": "2025-11-30",
        "status": "GOOD",
    },

    "W02": {
        "start": "2025-11-30",
        "end": "2025-12-15",
        "status": "GOOD",
    },

    "W04": {
        "start": "2025-12-30",
        "end": "2026-01-14",
        "status": "GOOD",
    },

    "W05": {
        "start": "2026-01-14",
        "end": "2026-01-29",
        "status": "GOOD",
    },

    "W06": {
        "start": "2026-01-29",
        "end": "2026-02-13",
        "status": "GOOD",
    },

    "W07": {
        "start": "2026-02-13",
        "end": "2026-02-28",
        "status": "GOOD",
    },

    "W08": {
        "start": "2026-02-28",
        "end": "2026-03-15",
        "status": "GOOD",
    },

    "W09": {
        "start": "2026-03-15",
        "end": "2026-03-30",
        "status": "LIMITED",
    },

    "W10": {
        "start": "2026-03-30",
        "end": "2026-04-14",
        "status": "GOOD",
    },
}


GOOD_WINDOWS = [
    "W01",
    "W02",
    "W04",
    "W05",
    "W06",
    "W07",
    "W08",
    "W10",
]


AVAILABLE_WINDOWS = [
    "W01",
    "W02",
    "W04",
    "W05",
    "W06",
    "W07",
    "W08",
    "W09",
    "W10",
]


VARIABLES = [
    "Cw",
    "laiCw",
    "LAI",
    "NDVI",
    "NDMI",
]


PYEO_BANDS = [
    "Cw",
    "Cw_UNCERTAINTY",
    "laiCw",
    "laiCw_UNCERTAINTY",
    "LAI",
    "LAI_UNCERTAINTY",
]


INDEX_BANDS = [
    "NDVI",
    "NDMI",
]


print("=" * 96)
print("STEP 17C — STABLE SPATIAL-SUPPORT SENSITIVITY")
print("=" * 96)


# ======================================================
# HELPERS
# ======================================================

def pyeo_path(window_id):

    m = WINDOWS[window_id]

    start = m["start"].replace("-", "")
    end = m["end"].replace("-", "")

    return (
        PYEO_DIR
        / (
            f"pyeogpr_{window_id}_"
            f"{start}_{end}_final.tif"
        )
    )


def index_path(window_id):

    m = WINDOWS[window_id]

    start = m["start"].replace("-", "")
    end = m["end"].replace("-", "")

    return (
        INDEX_DIR
        / (
            f"indices_{window_id}_"
            f"{start}_{end}_final.tif"
        )
    )


def pearson_r(x, y):

    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    good = (
        np.isfinite(x)
        & np.isfinite(y)
    )

    x = x[good]
    y = y[good]

    if len(x) < 3:
        return np.nan

    if (
        np.std(x) == 0
        or np.std(y) == 0
    ):
        return np.nan

    return float(
        np.corrcoef(
            x,
            y,
        )[0, 1]
    )


# ======================================================
# 1. LOAD FINAL AGRICULTURAL MASK
# ======================================================

if not MASK_PATH.exists():

    raise FileNotFoundError(
        MASK_PATH
    )


with rasterio.open(
    MASK_PATH
) as src:

    mask_crs = src.crs
    mask_transform = src.transform

    width = src.width
    height = src.height

    m = src.read(
        1,
        masked=True,
    )


agricultural = (

    ~np.ma.getmaskarray(
        m
    )

    & (
        m.filled(0)
        == 1
    )
)


agricultural_pixels = int(
    agricultural.sum()
)


print(
    "\nAgricultural pixels:",
    agricultural_pixels,
)


# ======================================================
# 2. VERIFY GRID
# ======================================================

def verify_grid(src, path):

    if (
        src.width != width
        or src.height != height
    ):

        raise RuntimeError(
            f"Grid size differs: {path}"
        )


    if src.crs != mask_crs:

        raise RuntimeError(
            f"CRS differs: {path}"
        )


    if not src.transform.almost_equals(
        mask_transform
    ):

        raise RuntimeError(
            f"Transform differs: {path}"
        )


# ======================================================
# 3. LOAD ALL WINDOWS
# ======================================================

window_data = {}


for window_id in AVAILABLE_WINDOWS:

    pp = pyeo_path(
        window_id
    )

    ip = index_path(
        window_id
    )


    with rasterio.open(
        pp
    ) as src:

        verify_grid(
            src,
            pp,
        )

        if list(
            src.descriptions
        ) != PYEO_BANDS:

            raise RuntimeError(
                f"{window_id}: "
                "unexpected PyEOGPR bands."
            )

        pyeo = src.read(
            masked=True
        )


    with rasterio.open(
        ip
    ) as src:

        verify_grid(
            src,
            ip,
        )

        if list(
            src.descriptions
        ) != INDEX_BANDS:

            raise RuntimeError(
                f"{window_id}: "
                "unexpected index bands."
            )

        indices = src.read(
            masked=True
        )


    arrays = {

        "Cw":
            pyeo[0]
            .filled(np.nan),

        "Cw_UNCERTAINTY":
            pyeo[1]
            .filled(np.nan),

        "laiCw":
            pyeo[2]
            .filled(np.nan),

        "laiCw_UNCERTAINTY":
            pyeo[3]
            .filled(np.nan),

        "LAI":
            pyeo[4]
            .filled(np.nan),

        "LAI_UNCERTAINTY":
            pyeo[5]
            .filled(np.nan),

        "NDVI":
            indices[0]
            .filled(np.nan),

        "NDMI":
            indices[1]
            .filled(np.nan),
    }


    common = agricultural.copy()


    for array in arrays.values():

        common &= np.isfinite(
            array
        )


    window_data[
        window_id
    ] = {

        "arrays":
            arrays,

        "common":
            common,
    }


# ======================================================
# 4. BUILD STABLE GOOD-WINDOW CORE
# ======================================================

stable_core = agricultural.copy()


for window_id in GOOD_WINDOWS:

    stable_core &= (
        window_data[
            window_id
        ][
            "common"
        ]
    )


stable_pixels = int(
    stable_core.sum()
)


stable_pct_agriculture = (

    100.0
    * stable_pixels
    / agricultural_pixels
)


print("\n" + "=" * 96)
print("STABLE GOOD-WINDOW SUPPORT")
print("=" * 96)

print(
    "Stable pixels:",
    stable_pixels,
)

print(
    f"Stable agricultural-domain coverage: "
    f"{stable_pct_agriculture:.4f}%"
)


# ======================================================
# 5. LOAD STEP 17A BASELINE MEDIANS
# ======================================================

baseline = {}


with open(
    STEP17A_CSV,
    "r",
    encoding="utf-8",
) as f:

    reader = csv.DictReader(
        f
    )

    for row in reader:

        baseline[
            row[
                "window_id"
            ]
        ] = {

            variable:
                float(
                    row[
                        f"{variable}_p50"
                    ]
                )

            for variable in VARIABLES
        }


# ======================================================
# 6. STABLE-CORE MEDIANS
# ======================================================

rows = []


for window_id in GOOD_WINDOWS:

    arrays = (
        window_data[
            window_id
        ][
            "arrays"
        ]
    )


    row = {

        "window_id":
            window_id,

        "status":
            "GOOD",

        "stable_pixels":
            stable_pixels,

        "stable_agricultural_percent":
            stable_pct_agriculture,
    }


    for variable in VARIABLES:

        values = (
            arrays[
                variable
            ][
                stable_core
            ]
        )


        values = values[
            np.isfinite(
                values
            )
        ]


        stable_median = float(
            np.median(
                values
            )
        )


        baseline_median = (
            baseline[
                window_id
            ][
                variable
            ]
        )


        difference = (
            stable_median
            - baseline_median
        )


        if baseline_median != 0:

            difference_pct = (

                100.0
                * difference
                / baseline_median
            )

        else:

            difference_pct = np.nan


        row[
            f"{variable}_baseline"
        ] = baseline_median


        row[
            f"{variable}_stable"
        ] = stable_median


        row[
            f"{variable}_difference"
        ] = difference


        row[
            f"{variable}_difference_pct"
        ] = difference_pct


    rows.append(
        row
    )


# ======================================================
# 7. SEASONAL TRAJECTORY ROBUSTNESS
# ======================================================

summary_rows = []


for variable in VARIABLES:

    baseline_series = np.asarray(
        [
            row[
                f"{variable}_baseline"
            ]
            for row in rows
        ],
        dtype=float,
    )


    stable_series = np.asarray(
        [
            row[
                f"{variable}_stable"
            ]
            for row in rows
        ],
        dtype=float,
    )


    seasonal_range = float(
        np.max(
            baseline_series
        )
        - np.min(
            baseline_series
        )
    )


    absolute_difference = np.abs(
        stable_series
        - baseline_series
    )


    mean_abs_difference = float(
        np.mean(
            absolute_difference
        )
    )


    maximum_abs_difference = float(
        np.max(
            absolute_difference
        )
    )


    if seasonal_range > 0:

        normalized_mad_pct = (

            100.0
            * mean_abs_difference
            / seasonal_range
        )


        normalized_max_pct = (

            100.0
            * maximum_abs_difference
            / seasonal_range
        )

    else:

        normalized_mad_pct = np.nan
        normalized_max_pct = np.nan


    trajectory_r = pearson_r(
        baseline_series,
        stable_series,
    )


    maximum_relative_shift = float(
        np.nanmax(
            np.abs(
                [
                    row[
                        f"{variable}_difference_pct"
                    ]
                    for row in rows
                ]
            )
        )
    )


    summary_rows.append({

        "variable":
            variable,

        "seasonal_range":
            seasonal_range,

        "mean_absolute_difference":
            mean_abs_difference,

        "maximum_absolute_difference":
            maximum_abs_difference,

        "normalized_mean_absolute_difference_percent":
            normalized_mad_pct,

        "normalized_maximum_difference_percent":
            normalized_max_pct,

        "maximum_relative_median_shift_percent":
            maximum_relative_shift,

        "trajectory_pearson_r":
            trajectory_r,
    })


# ======================================================
# 8. W09 OVERLAP WITH STABLE CORE
# ======================================================

w09_common = (
    window_data[
        "W09"
    ][
        "common"
    ]
)


w09_on_stable = (
    stable_core
    & w09_common
)


w09_stable_pixels = int(
    w09_on_stable.sum()
)


w09_pct_stable = (

    100.0
    * w09_stable_pixels
    / stable_pixels
)


print("\n" + "=" * 96)
print("STABLE-SUPPORT TRAJECTORY ROBUSTNESS")
print("=" * 96)


for row in summary_rows:

    print(

        f"{row['variable']}"

        f" | nMAD="
        f"{row['normalized_mean_absolute_difference_percent']:.4f}%"

        f" | max normalized difference="
        f"{row['normalized_maximum_difference_percent']:.4f}%"

        f" | max relative median shift="
        f"{row['maximum_relative_median_shift_percent']:.4f}%"

        f" | trajectory r="
        f"{row['trajectory_pearson_r']:.6f}"
    )


print("\n" + "=" * 96)
print("W09 OVERLAP WITH STABLE GOOD-WINDOW CORE")
print("=" * 96)

print(
    "Stable-core pixels:",
    stable_pixels,
)

print(
    "W09 stable-core pixels observed:",
    w09_stable_pixels,
)

print(
    f"W09 coverage of stable core: "
    f"{w09_pct_stable:.4f}%"
)


# ======================================================
# 9. SAVE STABLE CORE RASTER
# ======================================================

STABLE_MASK_PATH = (
    OUTPUT_DIR
    / "stable_good_window_core.tif"
)


with rasterio.open(
    MASK_PATH
) as src:

    profile = src.profile.copy()


profile.update(
    dtype="uint8",
    count=1,
    nodata=255,
    compress="DEFLATE",
    tiled=True,
)


output = np.where(
    agricultural,
    stable_core.astype(
        np.uint8
    ),
    255,
).astype(
    np.uint8
)


with rasterio.open(
    STABLE_MASK_PATH,
    "w",
    **profile,
) as dst:

    dst.write(
        output,
        1,
    )

    dst.set_band_description(
        1,
        "stable_good_window_core"
    )


# ======================================================
# 10. SAVE CSVs
# ======================================================

window_csv = (
    OUTPUT_DIR
    / "stable_support_window_comparison.csv"
)


with open(
    window_csv,
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


summary_csv = (
    OUTPUT_DIR
    / "stable_support_summary.csv"
)


with open(
    summary_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
    )


# ======================================================
# 11. JSON
# ======================================================

json_path = (
    OUTPUT_DIR
    / "step17c_stable_support.json"
)


json_output = {

    "agricultural_pixels":
        agricultural_pixels,

    "stable_good_window_pixels":
        stable_pixels,

    "stable_good_window_percent":
        stable_pct_agriculture,

    "GOOD_windows":
        GOOD_WINDOWS,

    "W09_stable_core_pixels":
        w09_stable_pixels,

    "W09_stable_core_coverage_percent":
        w09_pct_stable,

    "trajectory_robustness":
        summary_rows,

    "window_comparison":
        rows,
}


with open(
    json_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        json_output,
        f,
        indent=2,
    )


# ======================================================
# FINISH
# ======================================================

print("\n" + "=" * 96)
print("STEP 17C OUTPUTS")
print("=" * 96)

print(
    "Stable mask:",
    STABLE_MASK_PATH,
)

print(
    "Window comparison:",
    window_csv,
)

print(
    "Summary:",
    summary_csv,
)

print(
    "JSON:",
    json_path,
)


print("\n" + "=" * 96)
print("✅ STEP 17C COMPLETE")
print("=" * 96)
