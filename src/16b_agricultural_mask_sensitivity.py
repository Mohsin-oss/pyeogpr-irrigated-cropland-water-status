from pathlib import Path
import csv
import json

import numpy as np
import rasterio


# ======================================================
# PROJECT PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DRIVER_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_drivers_20251115_20260415_v2.tif"
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

QA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "qa"
)

QA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# CONSTANTS
# ======================================================

NODATA_VALUE = -9999.0

REFERENCE_CANDIDATE = "C25-N40"

BUILT_THRESHOLD = 0.20
WATER_THRESHOLD = 0.20


DRIVER_BANDS = [
    "crop_frequency",
    "built_frequency",
    "water_frequency",
    "seasonal_max_ndvi",
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


VARIABLES = [
    "Cw",
    "laiCw",
    "LAI",
    "NDVI",
    "NDMI",
]


# ======================================================
# WINDOW DEFINITIONS
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

    "W03": {
        "start": "2025-12-15",
        "end": "2025-12-30",
        "status": "MISSING",
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


GOOD_WINDOWS = [
    window_id
    for window_id in AVAILABLE_WINDOWS
    if WINDOWS[window_id]["status"] == "GOOD"
]


# ======================================================
# MASK CANDIDATES
# ======================================================

CANDIDATES = {}


for crop_threshold in [
    0.20,
    0.25,
    0.30,
]:

    for ndvi_threshold in [
        0.35,
        0.40,
        0.45,
    ]:

        name = (
            f"C{int(crop_threshold * 100):02d}"
            f"-N{int(ndvi_threshold * 100):02d}"
        )

        CANDIDATES[name] = {

            "crop_threshold":
                crop_threshold,

            "ndvi_threshold":
                ndvi_threshold,
        }


print("=" * 94)
print("STEP 16B — AGRICULTURAL-MASK SENSITIVITY")
print("=" * 94)


# ======================================================
# 1. CHECK REQUIRED FILES
# ======================================================

if not DRIVER_PATH.exists():

    raise FileNotFoundError(
        f"Mask-driver raster not found:\n"
        f"{DRIVER_PATH}"
    )


def pyeo_path(window_id):

    metadata = WINDOWS[
        window_id
    ]

    start = (
        metadata["start"]
        .replace("-", "")
    )

    end = (
        metadata["end"]
        .replace("-", "")
    )

    return (
        PYEO_DIR
        / (
            f"pyeogpr_{window_id}_"
            f"{start}_{end}_final.tif"
        )
    )


def index_path(window_id):

    metadata = WINDOWS[
        window_id
    ]

    start = (
        metadata["start"]
        .replace("-", "")
    )

    end = (
        metadata["end"]
        .replace("-", "")
    )

    return (
        INDEX_DIR
        / (
            f"indices_{window_id}_"
            f"{start}_{end}_final.tif"
        )
    )


for window_id in AVAILABLE_WINDOWS:

    if not pyeo_path(
        window_id
    ).exists():

        raise FileNotFoundError(
            f"Missing PyEOGPR raster:\n"
            f"{pyeo_path(window_id)}"
        )


    if not index_path(
        window_id
    ).exists():

        raise FileNotFoundError(
            f"Missing index raster:\n"
            f"{index_path(window_id)}"
        )


print(
    "✅ Driver and all seasonal "
    "analysis rasters found."
)


# ======================================================
# 2. READ DRIVER RASTER
# ======================================================

with rasterio.open(
    DRIVER_PATH
) as src:

    driver_crs = src.crs
    driver_transform = src.transform

    driver_width = src.width
    driver_height = src.height

    driver_descriptions = list(
        src.descriptions
    )

    driver_data = src.read(
        masked=True
    )


print("\nDriver grid:")

print(
    "CRS:",
    driver_crs,
)

print(
    "Dimensions:",
    driver_width,
    "x",
    driver_height,
)

print(
    "Resolution:",
    (
        abs(driver_transform.a),
        abs(driver_transform.e),
    ),
)

print(
    "Bands:",
    driver_descriptions,
)


if driver_descriptions != DRIVER_BANDS:

    raise RuntimeError(
        f"Unexpected driver bands: "
        f"{driver_descriptions}"
    )


# ======================================================
# 3. DRIVER VALUES
# ======================================================

crop_frequency = (
    driver_data[0]
    .filled(np.nan)
    .astype(float)
)

built_frequency = (
    driver_data[1]
    .filled(np.nan)
    .astype(float)
)

water_frequency = (
    driver_data[2]
    .filled(np.nan)
    .astype(float)
)

seasonal_max_ndvi = (
    driver_data[3]
    .filled(np.nan)
    .astype(float)
)


driver_valid = (

    np.isfinite(
        crop_frequency
    )

    & np.isfinite(
        built_frequency
    )

    & np.isfinite(
        water_frequency
    )

    & np.isfinite(
        seasonal_max_ndvi
    )
)


driver_valid_pixels = int(
    driver_valid.sum()
)


total_grid_pixels = int(
    driver_valid.size
)


print(
    "\nDriver-valid pixels:",
    driver_valid_pixels,
    "/",
    total_grid_pixels,
)


# ======================================================
# 4. VALIDATE GRIDS + LOAD SEASONAL DATA
# ======================================================

season_data = {}


def verify_grid(
    src,
    path,
):

    if (
        src.width
        != driver_width

        or src.height
        != driver_height
    ):

        raise RuntimeError(
            f"Grid dimensions differ:\n{path}"
        )


    if src.crs != driver_crs:

        raise RuntimeError(
            f"CRS differs:\n{path}"
        )


    if not src.transform.almost_equals(
        driver_transform
    ):

        raise RuntimeError(
            f"Transform differs:\n{path}"
        )


for window_id in AVAILABLE_WINDOWS:

    # --------------------------------------------------
    # PyEOGPR
    # --------------------------------------------------

    pp = pyeo_path(
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


    # --------------------------------------------------
    # NDVI / NDMI
    # --------------------------------------------------

    ip = index_path(
        window_id
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


    # --------------------------------------------------
    # Common valid masks
    # --------------------------------------------------

    pyeo_mask = np.any(
        np.ma.getmaskarray(
            pyeo
        ),
        axis=0,
    )


    index_mask = np.any(
        np.ma.getmaskarray(
            indices
        ),
        axis=0,
    )


    pyeo_valid = (
        ~pyeo_mask
    )


    index_valid = (
        ~index_mask
    )


    comparative_valid = (
        pyeo_valid
        & index_valid
    )


    season_data[
        window_id
    ] = {

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

        "pyeo_valid":
            pyeo_valid,

        "index_valid":
            index_valid,

        "comparative_valid":
            comparative_valid,
    }


print(
    "✅ All production grids "
    "match the driver grid."
)


# ======================================================
# 5. BUILD NINE CANDIDATE MASKS
# ======================================================

candidate_masks = {}

area_rows = []


for candidate_name, config in CANDIDATES.items():

    mask = (

        driver_valid

        & (
            crop_frequency
            >= config[
                "crop_threshold"
            ]
        )

        & (
            seasonal_max_ndvi
            >= config[
                "ndvi_threshold"
            ]
        )

        & (
            built_frequency
            < BUILT_THRESHOLD
        )

        & (
            water_frequency
            < WATER_THRESHOLD
        )
    )


    candidate_masks[
        candidate_name
    ] = mask


    pixels = int(
        mask.sum()
    )


    pct_driver = (
        100
        * pixels
        / driver_valid_pixels
    )


    pct_grid = (
        100
        * pixels
        / total_grid_pixels
    )


    area_rows.append({

        "candidate":
            candidate_name,

        "crop_threshold":
            config[
                "crop_threshold"
            ],

        "ndvi_threshold":
            config[
                "ndvi_threshold"
            ],

        "built_threshold":
            BUILT_THRESHOLD,

        "water_threshold":
            WATER_THRESHOLD,

        "pixels":
            pixels,

        "percent_driver_valid_area":
            pct_driver,

        "percent_full_grid":
            pct_grid,
    })


# ======================================================
# 6. REFERENCE AREA DIFFERENCE
# ======================================================

reference_area = next(

    row[
        "percent_driver_valid_area"
    ]

    for row in area_rows

    if row[
        "candidate"
    ] == REFERENCE_CANDIDATE
)


for row in area_rows:

    row[
        "area_difference_pp_vs_reference"
    ] = (

        row[
            "percent_driver_valid_area"
        ]
        - reference_area
    )


print("\n" + "=" * 94)
print("CANDIDATE AGRICULTURAL AREA")
print("=" * 94)


for row in area_rows:

    print(
        f"{row['candidate']}: "
        f"{row['percent_driver_valid_area']:.2f}% "
        f"of driver-valid area "
        f"({row['area_difference_pp_vs_reference']:+.2f} pp "
        f"vs {REFERENCE_CANDIDATE})"
    )


# ======================================================
# 7. WINDOW STATISTICS FOR EVERY MASK
# ======================================================

window_rows = []


for candidate_name, mask in candidate_masks.items():

    candidate_pixels = int(
        mask.sum()
    )


    for window_id in AVAILABLE_WINDOWS:

        data = season_data[
            window_id
        ]


        pyeo_analysis_mask = (
            mask
            & data[
                "pyeo_valid"
            ]
        )


        index_analysis_mask = (
            mask
            & data[
                "index_valid"
            ]
        )


        common_analysis_mask = (
            mask
            & data[
                "comparative_valid"
            ]
        )


        pyeo_pixels = int(
            pyeo_analysis_mask.sum()
        )


        index_pixels = int(
            index_analysis_mask.sum()
        )


        common_pixels = int(
            common_analysis_mask.sum()
        )


        if candidate_pixels > 0:

            pyeo_retained_pct = (
                100
                * pyeo_pixels
                / candidate_pixels
            )

            index_retained_pct = (
                100
                * index_pixels
                / candidate_pixels
            )

            common_retained_pct = (
                100
                * common_pixels
                / candidate_pixels
            )

        else:

            pyeo_retained_pct = np.nan
            index_retained_pct = np.nan
            common_retained_pct = np.nan


        if common_pixels == 0:

            raise RuntimeError(
                f"{candidate_name} / "
                f"{window_id}: "
                "zero comparative pixels."
            )


        row = {

            "candidate":
                candidate_name,

            "window_id":
                window_id,

            "status":
                WINDOWS[
                    window_id
                ]["status"],

            "candidate_pixels":
                candidate_pixels,

            "pyeogpr_pixels":
                pyeo_pixels,

            "index_pixels":
                index_pixels,

            "common_pixels":
                common_pixels,

            "pyeogpr_retained_pct":
                pyeo_retained_pct,

            "index_retained_pct":
                index_retained_pct,

            "common_retained_pct":
                common_retained_pct,
        }


        # ----------------------------------------------
        # Trait medians
        # ----------------------------------------------

        for variable in [
            "Cw",
            "laiCw",
            "LAI",
            "NDVI",
            "NDMI",
        ]:

            values = (
                data[
                    variable
                ][
                    common_analysis_mask
                ]
            )


            values = values[
                np.isfinite(
                    values
                )
            ]


            row[
                f"{variable}_median"
            ] = float(
                np.median(
                    values
                )
            )


        # ----------------------------------------------
        # Absolute uncertainty medians
        # ----------------------------------------------

        for variable in [
            "Cw_UNCERTAINTY",
            "laiCw_UNCERTAINTY",
            "LAI_UNCERTAINTY",
        ]:

            values = (
                data[
                    variable
                ][
                    common_analysis_mask
                ]
            )


            values = values[
                np.isfinite(
                    values
                )
            ]


            row[
                f"{variable}_median"
            ] = float(
                np.median(
                    values
                )
            )


        window_rows.append(
            row
        )


# ======================================================
# 8. TRAJECTORY SENSITIVITY VS REFERENCE MASK
# ======================================================

sensitivity_rows = []


def get_window_row(
    candidate,
    window_id,
):

    for row in window_rows:

        if (
            row[
                "candidate"
            ] == candidate

            and row[
                "window_id"
            ] == window_id
        ):

            return row


    raise KeyError(
        f"{candidate} / {window_id}"
    )


for candidate_name in CANDIDATES:

    # --------------------------------------------------
    # GOOD windows only for primary sensitivity
    #
    # W09 is excluded here because its reduced spatial
    # coverage is a separate observational limitation.
    # --------------------------------------------------

    for variable in VARIABLES:

        reference_series = []

        candidate_series = []


        for window_id in GOOD_WINDOWS:

            reference_series.append(

                get_window_row(
                    REFERENCE_CANDIDATE,
                    window_id,
                )[
                    f"{variable}_median"
                ]
            )


            candidate_series.append(

                get_window_row(
                    candidate_name,
                    window_id,
                )[
                    f"{variable}_median"
                ]
            )


        reference_series = np.asarray(
            reference_series,
            dtype=float,
        )


        candidate_series = np.asarray(
            candidate_series,
            dtype=float,
        )


        differences = (
            candidate_series
            - reference_series
        )


        absolute_differences = (
            np.abs(
                differences
            )
        )


        mean_abs_difference = float(
            np.mean(
                absolute_differences
            )
        )


        max_abs_difference = float(
            np.max(
                absolute_differences
            )
        )


        reference_range = float(
            np.max(
                reference_series
            )
            - np.min(
                reference_series
            )
        )


        if reference_range > 0:

            normalized_mad_pct = (
                100
                * mean_abs_difference
                / reference_range
            )

        else:

            normalized_mad_pct = np.nan


        if (
            np.std(
                reference_series
            ) > 0

            and np.std(
                candidate_series
            ) > 0
        ):

            pearson_r = float(
                np.corrcoef(
                    reference_series,
                    candidate_series,
                )[0, 1]
            )

        else:

            pearson_r = np.nan


        sensitivity_rows.append({

            "candidate":
                candidate_name,

            "reference":
                REFERENCE_CANDIDATE,

            "variable":
                variable,

            "good_windows_n":
                len(
                    GOOD_WINDOWS
                ),

            "mean_absolute_difference":
                mean_abs_difference,

            "maximum_absolute_difference":
                max_abs_difference,

            "reference_seasonal_range":
                reference_range,

            "normalized_MAD_percent_of_reference_range":
                normalized_mad_pct,

            "pearson_r":
                pearson_r,
        })


# ======================================================
# 9. CANDIDATE-LEVEL SUMMARY
# ======================================================

summary_rows = []


for candidate_name in CANDIDATES:

    area_row = next(

        row
        for row in area_rows

        if row[
            "candidate"
        ] == candidate_name
    )


    good_common_coverages = []


    for window_id in GOOD_WINDOWS:

        row = get_window_row(
            candidate_name,
            window_id,
        )


        good_common_coverages.append(
            row[
                "common_retained_pct"
            ]
        )


    w09_row = get_window_row(
        candidate_name,
        "W09",
    )


    variable_sensitivities = [

        row

        for row in sensitivity_rows

        if row[
            "candidate"
        ] == candidate_name
    ]


    max_normalized_mad = float(
        np.nanmax(
            [
                row[
                    "normalized_MAD_percent_of_reference_range"
                ]

                for row
                in variable_sensitivities
            ]
        )
    )


    min_trajectory_r = float(
        np.nanmin(
            [
                row[
                    "pearson_r"
                ]

                for row
                in variable_sensitivities
            ]
        )
    )


    summary_rows.append({

        "candidate":
            candidate_name,

        "area_percent":
            area_row[
                "percent_driver_valid_area"
            ],

        "area_difference_pp_vs_reference":
            area_row[
                "area_difference_pp_vs_reference"
            ],

        "mean_common_retention_GOOD_windows_pct":
            float(
                np.mean(
                    good_common_coverages
                )
            ),

        "minimum_common_retention_GOOD_windows_pct":
            float(
                np.min(
                    good_common_coverages
                )
            ),

        "W09_common_retention_pct":
            w09_row[
                "common_retained_pct"
            ],

        "maximum_normalized_MAD_pct":
            max_normalized_mad,

        "minimum_seasonal_pearson_r":
            min_trajectory_r,
    })


# ======================================================
# 10. PRINT SENSITIVITY SUMMARY
# ======================================================

print("\n" + "=" * 94)
print("MASK SENSITIVITY SUMMARY")
print("=" * 94)


for row in summary_rows:

    print(
        f"{row['candidate']}: "
        f"area={row['area_percent']:.2f}%"
        f" | Δarea={row['area_difference_pp_vs_reference']:+.2f} pp"
        f" | GOOD common="
        f"{row['mean_common_retention_GOOD_windows_pct']:.2f}%"
        f" | W09 common="
        f"{row['W09_common_retention_pct']:.2f}%"
        f" | max nMAD="
        f"{row['maximum_normalized_MAD_pct']:.2f}%"
        f" | min r="
        f"{row['minimum_seasonal_pearson_r']:.4f}"
    )


# ======================================================
# 11. PRINT REFERENCE SEASONAL TRAJECTORY
# ======================================================

print("\n" + "=" * 94)
print(f"REFERENCE TRAJECTORY — {REFERENCE_CANDIDATE}")
print("=" * 94)


for window_id in AVAILABLE_WINDOWS:

    row = get_window_row(
        REFERENCE_CANDIDATE,
        window_id,
    )


    print(
        f"{window_id}"
        f" | status={row['status']}"
        f" | common={row['common_retained_pct']:.2f}%"
        f" | Cw={row['Cw_median']:.6f}"
        f" | laiCw={row['laiCw_median']:.2f}"
        f" | LAI={row['LAI_median']:.3f}"
        f" | NDVI={row['NDVI_median']:.4f}"
        f" | NDMI={row['NDMI_median']:.4f}"
    )


# ======================================================
# 12. SAVE CANDIDATE MASK STACK
# ======================================================

candidate_mask_path = (
    QA_DIR
    / "agricultural_mask_candidates.tif"
)


with rasterio.open(
    DRIVER_PATH
) as src:

    profile = (
        src.profile.copy()
    )


profile.update(
    dtype="uint8",
    count=len(
        CANDIDATES
    ),
    nodata=255,
    compress="DEFLATE",
    tiled=True,
)


with rasterio.open(
    candidate_mask_path,
    "w",
    **profile,
) as dst:

    for band_index, candidate_name in enumerate(
        CANDIDATES.keys(),
        start=1,
    ):

        output = np.where(
            driver_valid,
            candidate_masks[
                candidate_name
            ].astype(
                np.uint8
            ),
            255,
        ).astype(
            np.uint8
        )


        dst.write(
            output,
            band_index,
        )


        dst.set_band_description(
            band_index,
            candidate_name,
        )


# ======================================================
# 13. SAVE CSV FILES
# ======================================================

area_csv = (
    QA_DIR
    / "mask_candidate_area.csv"
)


with open(
    area_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            area_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        area_rows
    )


window_csv = (
    QA_DIR
    / "mask_window_statistics.csv"
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
            window_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        window_rows
    )


sensitivity_csv = (
    QA_DIR
    / "mask_sensitivity_vs_reference.csv"
)


with open(
    sensitivity_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            sensitivity_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        sensitivity_rows
    )


summary_csv = (
    QA_DIR
    / "mask_sensitivity_summary.csv"
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
# 14. SAVE JSON
# ======================================================

json_path = (
    QA_DIR
    / "mask_sensitivity_full.json"
)


json_output = {

    "reference_candidate":
        REFERENCE_CANDIDATE,

    "built_threshold":
        BUILT_THRESHOLD,

    "water_threshold":
        WATER_THRESHOLD,

    "candidate_area":
        area_rows,

    "candidate_summary":
        summary_rows,

    "window_statistics":
        window_rows,

    "trajectory_sensitivity":
        sensitivity_rows,

    "notes": [

        (
            "Primary trajectory sensitivity uses "
            "GOOD windows only."
        ),

        (
            "W09 is retained separately because "
            "it has reduced observational coverage."
        ),

        (
            "No candidate is automatically selected "
            "by this script."
        ),

        (
            "C25-N40 is the reference candidate, "
            "not a pre-declared winner."
        ),
    ],
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
# 15. FINAL STATUS
# ======================================================

print("\n" + "=" * 94)
print("STEP 16B OUTPUTS")
print("=" * 94)

print(
    "Candidate area:",
    area_csv,
)

print(
    "Window statistics:",
    window_csv,
)

print(
    "Sensitivity vs reference:",
    sensitivity_csv,
)

print(
    "Summary:",
    summary_csv,
)

print(
    "Candidate mask raster:",
    candidate_mask_path,
)

print(
    "Full JSON:",
    json_path,
)


print("\n" + "=" * 94)
print("✅ STEP 16B COMPLETE")
print("=" * 94)

print(
    "\nNo agricultural mask has "
    "been frozen automatically."
)

print(
    "Review sensitivity results "
    "before selecting the primary mask."
)