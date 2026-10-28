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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17b"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# SETTINGS
# ======================================================

RU_THRESHOLDS = [
    20,
    30,
    40,
]

MAX_SAMPLE = 10000

RANDOM_SEED = 1702


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


AVAILABLE_WINDOWS = list(
    WINDOWS.keys()
)


GOOD_WINDOWS = [
    window_id
    for window_id in AVAILABLE_WINDOWS
    if WINDOWS[window_id]["status"] == "GOOD"
]


# ======================================================
# TRAIT DEFINITIONS
# ======================================================

TRAITS = {

    "Cw": {
        "prediction_band": 1,
        "uncertainty_band": 2,
        "comparison_index": "NDMI",
    },

    "laiCw": {
        "prediction_band": 3,
        "uncertainty_band": 4,
        "comparison_index": "NDMI",
    },

    "LAI": {
        "prediction_band": 5,
        "uncertainty_band": 6,
        "comparison_index": "NDVI",
    },
}


INDEX_BANDS = {

    "NDVI": 1,
    "NDMI": 2,
}


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


def rankdata(values):

    values = np.asarray(
        values,
        dtype=float,
    )

    order = np.argsort(
        values,
        kind="mergesort",
    )

    sorted_values = (
        values[order]
    )

    ranks = np.empty(
        len(values),
        dtype=float,
    )

    i = 0

    while i < len(values):

        j = i + 1

        while (
            j < len(values)
            and sorted_values[j]
            == sorted_values[i]
        ):
            j += 1

        rank = (
            (i + 1)
            + j
        ) / 2.0

        ranks[
            order[i:j]
        ] = rank

        i = j

    return ranks


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


def spearman_r(x, y):

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

    return pearson_r(
        rankdata(x),
        rankdata(y),
    )


def percentile_stats(values):

    values = np.asarray(
        values,
        dtype=float,
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:

        return {
            "p25": np.nan,
            "p50": np.nan,
            "p75": np.nan,
            "p95": np.nan,
        }

    p = np.percentile(
        values,
        [
            25,
            50,
            75,
            95,
        ],
    )

    return {
        "p25": float(p[0]),
        "p50": float(p[1]),
        "p75": float(p[2]),
        "p95": float(p[3]),
    }


def sampled_correlations(
    prediction,
    index,
    mask,
    seed,
):

    flat = np.flatnonzero(
        mask
    )

    n_available = len(
        flat
    )

    if n_available < 3:

        return {
            "sample_n": n_available,
            "pearson_r": np.nan,
            "spearman_r": np.nan,
        }


    rng = np.random.default_rng(
        seed
    )


    if n_available > MAX_SAMPLE:

        flat = rng.choice(
            flat,
            size=MAX_SAMPLE,
            replace=False,
        )


    x = (
        prediction
        .ravel()[
            flat
        ]
    )

    y = (
        index
        .ravel()[
            flat
        ]
    )


    return {

        "sample_n":
            len(flat),

        "pearson_r":
            pearson_r(
                x,
                y,
            ),

        "spearman_r":
            spearman_r(
                x,
                y,
            ),
    }


# ======================================================
# START
# ======================================================

print("=" * 96)
print("STEP 17B — UNCERTAINTY-AWARE SENSITIVITY ANALYSIS")
print("=" * 96)


# ======================================================
# 1. LOAD FROZEN MASK
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
    mask_width = src.width
    mask_height = src.height

    mask_image = src.read(
        1,
        masked=True,
    )


agricultural = (

    ~np.ma.getmaskarray(
        mask_image
    )

    & (
        mask_image.filled(0)
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
# 2. GRID VALIDATION
# ======================================================

def verify_grid(
    src,
    path,
):

    if (
        src.width != mask_width
        or src.height != mask_height
    ):

        raise RuntimeError(
            f"Dimensions differ: "
            f"{path}"
        )


    if src.crs != mask_crs:

        raise RuntimeError(
            f"CRS differs: "
            f"{path}"
        )


    if not src.transform.almost_equals(
        mask_transform
    ):

        raise RuntimeError(
            f"Transform differs: "
            f"{path}"
        )


# ======================================================
# 3. STORAGE
# ======================================================

window_rows = []

correlation_rows = []


# ======================================================
# 4. PROCESS WINDOWS
# ======================================================

for window_number, window_id in enumerate(
    AVAILABLE_WINDOWS
):

    metadata = WINDOWS[
        window_id
    ]


    print("\n" + "=" * 96)

    print(
        f"{window_id} "
        f"[{metadata['status']}]"
    )

    print("=" * 96)


    pp = pyeo_path(
        window_id
    )

    ip = index_path(
        window_id
    )


    # --------------------------------------------------
    # PyEOGPR
    # --------------------------------------------------

    with rasterio.open(
        pp
    ) as src:

        verify_grid(
            src,
            pp,
        )

        pyeo = src.read(
            masked=True
        )


    # --------------------------------------------------
    # Indices
    # --------------------------------------------------

    with rasterio.open(
        ip
    ) as src:

        verify_grid(
            src,
            ip,
        )

        index_data = src.read(
            masked=True
        )


    ndvi = (
        index_data[
            INDEX_BANDS["NDVI"] - 1
        ]
        .filled(np.nan)
    )


    ndmi = (
        index_data[
            INDEX_BANDS["NDMI"] - 1
        ]
        .filled(np.nan)
    )


    index_arrays = {
        "NDVI": ndvi,
        "NDMI": ndmi,
    }


    # --------------------------------------------------
    # Trait processing
    # --------------------------------------------------

    for trait_number, (
        trait,
        config,
    ) in enumerate(
        TRAITS.items()
    ):

        prediction = (
            pyeo[
                config[
                    "prediction_band"
                ] - 1
            ]
            .filled(np.nan)
        )


        uncertainty = (
            pyeo[
                config[
                    "uncertainty_band"
                ] - 1
            ]
            .filled(np.nan)
        )


        index_name = (
            config[
                "comparison_index"
            ]
        )


        index_array = (
            index_arrays[
                index_name
            ]
        )


        # ----------------------------------------------
        # Primary finite support
        # ----------------------------------------------

        common = (

            agricultural

            & np.isfinite(
                prediction
            )

            & np.isfinite(
                uncertainty
            )

            & np.isfinite(
                index_array
            )
        )


        common_pixels = int(
            common.sum()
        )


        # Relative uncertainty requires positive
        # prediction denominator.
        positive = (

            common

            & (
                prediction > 0
            )

            & (
                uncertainty >= 0
            )
        )


        positive_pixels = int(
            positive.sum()
        )


        positive_pct_common = (

            100.0
            * positive_pixels
            / common_pixels

            if common_pixels > 0
            else np.nan
        )


        # ----------------------------------------------
        # RU
        # ----------------------------------------------

        ru = np.full(
            prediction.shape,
            np.nan,
            dtype=float,
        )


        ru[
            positive
        ] = (

            uncertainty[
                positive
            ]

            / prediction[
                positive
            ]

            * 100.0
        )


        ru_values = (
            ru[
                positive
            ]
        )


        ru_stats = percentile_stats(
            ru_values
        )


        baseline_prediction = (
            prediction[
                positive
            ]
        )


        baseline_median = float(
            np.median(
                baseline_prediction
            )
        )


        baseline_corr = (
            sampled_correlations(

                prediction,
                index_array,
                positive,

                seed=(
                    RANDOM_SEED
                    + window_number * 100
                    + trait_number
                ),
            )
        )


        print(
            f"\n{trait}:"
        )

        print(
            f"  positive RU support = "
            f"{positive_pct_common:.2f}%"
        )

        print(
            f"  RU P25/P50/P75/P95 = "
            f"{ru_stats['p25']:.2f} / "
            f"{ru_stats['p50']:.2f} / "
            f"{ru_stats['p75']:.2f} / "
            f"{ru_stats['p95']:.2f}"
        )

        print(
            f"  baseline {trait} median = "
            f"{baseline_median:.6f}"
        )


        # ----------------------------------------------
        # RU thresholds
        # ----------------------------------------------

        for threshold in RU_THRESHOLDS:

            accepted = (

                positive

                & (
                    ru < threshold
                )
            )


            accepted_pixels = int(
                accepted.sum()
            )


            retention_pct = (

                100.0
                * accepted_pixels
                / positive_pixels

                if positive_pixels > 0
                else np.nan
            )


            agricultural_retention_pct = (

                100.0
                * accepted_pixels
                / agricultural_pixels
            )


            if accepted_pixels > 0:

                accepted_values = (
                    prediction[
                        accepted
                    ]
                )


                accepted_uncertainty = (
                    uncertainty[
                        accepted
                    ]
                )


                filtered_median = float(
                    np.median(
                        accepted_values
                    )
                )


                filtered_uncertainty_median = float(
                    np.median(
                        accepted_uncertainty
                    )
                )


                shift_absolute = (
                    filtered_median
                    - baseline_median
                )


                if baseline_median != 0:

                    shift_percent = (

                        100.0
                        * shift_absolute
                        / baseline_median
                    )

                else:

                    shift_percent = np.nan


                corr = sampled_correlations(

                    prediction,
                    index_array,
                    accepted,

                    seed=(
                        RANDOM_SEED
                        + window_number * 100
                        + trait_number * 10
                        + threshold
                    ),
                )


            else:

                filtered_median = np.nan
                filtered_uncertainty_median = np.nan

                shift_absolute = np.nan
                shift_percent = np.nan

                corr = {
                    "sample_n": 0,
                    "pearson_r": np.nan,
                    "spearman_r": np.nan,
                }


            window_rows.append({

                "window_id":
                    window_id,

                "status":
                    metadata["status"],

                "trait":
                    trait,

                "comparison_index":
                    index_name,

                "RU_threshold_percent":
                    threshold,

                "common_pixels":
                    common_pixels,

                "positive_RU_pixels":
                    positive_pixels,

                "positive_RU_percent_of_common":
                    positive_pct_common,

                "RU_p25":
                    ru_stats["p25"],

                "RU_p50":
                    ru_stats["p50"],

                "RU_p75":
                    ru_stats["p75"],

                "RU_p95":
                    ru_stats["p95"],

                "accepted_pixels":
                    accepted_pixels,

                "retention_percent_of_positive_support":
                    retention_pct,

                "retention_percent_of_agricultural_domain":
                    agricultural_retention_pct,

                "baseline_trait_median":
                    baseline_median,

                "filtered_trait_median":
                    filtered_median,

                "median_shift_absolute":
                    shift_absolute,

                "median_shift_percent":
                    shift_percent,

                "filtered_uncertainty_median":
                    filtered_uncertainty_median,
            })


            correlation_rows.append({

                "window_id":
                    window_id,

                "status":
                    metadata["status"],

                "trait":
                    trait,

                "index":
                    index_name,

                "RU_threshold_percent":
                    threshold,

                "sample_n":
                    corr["sample_n"],

                "baseline_pearson_r":
                    baseline_corr[
                        "pearson_r"
                    ],

                "filtered_pearson_r":
                    corr[
                        "pearson_r"
                    ],

                "baseline_spearman_r":
                    baseline_corr[
                        "spearman_r"
                    ],

                "filtered_spearman_r":
                    corr[
                        "spearman_r"
                    ],
            })


            print(

                f"  RU <{threshold:02d}%: "

                f"retain="
                f"{retention_pct:.2f}%"

                f" | ag-domain="
                f"{agricultural_retention_pct:.2f}%"

                f" | median="
                f"{filtered_median:.6f}"

                f" | shift="
                f"{shift_percent:+.2f}%"

                f" | r="
                f"{corr['pearson_r']:.4f}"
            )


# ======================================================
# 5. GOOD-WINDOW SUMMARY
# ======================================================

summary_rows = []


for trait in TRAITS:

    for threshold in RU_THRESHOLDS:

        rows = [

            row

            for row in window_rows

            if (
                row["trait"] == trait

                and row[
                    "RU_threshold_percent"
                ] == threshold

                and row[
                    "status"
                ] == "GOOD"
            )
        ]


        retention = np.asarray(
            [
                row[
                    "retention_percent_of_positive_support"
                ]
                for row in rows
            ],
            dtype=float,
        )


        domain_retention = np.asarray(
            [
                row[
                    "retention_percent_of_agricultural_domain"
                ]
                for row in rows
            ],
            dtype=float,
        )


        shifts = np.asarray(
            [
                row[
                    "median_shift_percent"
                ]
                for row in rows
            ],
            dtype=float,
        )


        finite_shifts = shifts[
            np.isfinite(
                shifts
            )
        ]


        corr_rows = [

            row

            for row in correlation_rows

            if (
                row["trait"] == trait

                and row[
                    "RU_threshold_percent"
                ] == threshold

                and row[
                    "status"
                ] == "GOOD"
            )
        ]


        filtered_r = np.asarray(
            [
                row[
                    "filtered_pearson_r"
                ]
                for row in corr_rows
            ],
            dtype=float,
        )


        finite_r = filtered_r[
            np.isfinite(
                filtered_r
            )
        ]


        summary_rows.append({

            "trait":
                trait,

            "comparison_index":
                TRAITS[
                    trait
                ][
                    "comparison_index"
                ],

            "RU_threshold_percent":
                threshold,

            "GOOD_windows_n":
                len(rows),

            "minimum_retention_percent":
                float(
                    np.nanmin(
                        retention
                    )
                ),

            "median_retention_percent":
                float(
                    np.nanmedian(
                        retention
                    )
                ),

            "maximum_retention_percent":
                float(
                    np.nanmax(
                        retention
                    )
                ),

            "median_agricultural_domain_retention_percent":
                float(
                    np.nanmedian(
                        domain_retention
                    )
                ),

            "maximum_absolute_median_shift_percent":
                (
                    float(
                        np.max(
                            np.abs(
                                finite_shifts
                            )
                        )
                    )
                    if len(
                        finite_shifts
                    ) > 0
                    else np.nan
                ),

            "median_absolute_median_shift_percent":
                (
                    float(
                        np.median(
                            np.abs(
                                finite_shifts
                            )
                        )
                    )
                    if len(
                        finite_shifts
                    ) > 0
                    else np.nan
                ),

            "median_filtered_spatial_pearson_r":
                (
                    float(
                        np.median(
                            finite_r
                        )
                    )
                    if len(
                        finite_r
                    ) > 0
                    else np.nan
                ),
        })


# ======================================================
# 6. PRINT GOOD-WINDOW SUMMARY
# ======================================================

print("\n" + "=" * 96)
print("GOOD-WINDOW RU SENSITIVITY SUMMARY")
print("=" * 96)


for row in summary_rows:

    print(

        f"{row['trait']} "

        f"RU <{row['RU_threshold_percent']}%"

        f" | retention "
        f"min/median/max="
        f"{row['minimum_retention_percent']:.2f}/"
        f"{row['median_retention_percent']:.2f}/"
        f"{row['maximum_retention_percent']:.2f}%"

        f" | median domain retained="
        f"{row['median_agricultural_domain_retention_percent']:.2f}%"

        f" | max |median shift|="
        f"{row['maximum_absolute_median_shift_percent']:.2f}%"

        f" | median filtered r="
        f"{row['median_filtered_spatial_pearson_r']:.4f}"
    )


# ======================================================
# 7. PRINT W09 SEPARATELY
# ======================================================

print("\n" + "=" * 96)
print("W09 LIMITED-WINDOW RU SENSITIVITY")
print("=" * 96)


for row in window_rows:

    if row[
        "window_id"
    ] != "W09":

        continue


    print(

        f"{row['trait']} "

        f"RU <{row['RU_threshold_percent']}%"

        f" | retain="
        f"{row['retention_percent_of_positive_support']:.2f}%"

        f" | agricultural domain="
        f"{row['retention_percent_of_agricultural_domain']:.2f}%"

        f" | median shift="
        f"{row['median_shift_percent']:+.2f}%"
    )


# ======================================================
# 8. SAVE CSVs
# ======================================================

window_csv = (
    OUTPUT_DIR
    / "ru_window_sensitivity.csv"
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


correlation_csv = (
    OUTPUT_DIR
    / "ru_spatial_correlation_sensitivity.csv"
)


with open(
    correlation_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            correlation_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        correlation_rows
    )


summary_csv = (
    OUTPUT_DIR
    / "ru_good_window_summary.csv"
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
# 9. JSON
# ======================================================

json_path = (
    OUTPUT_DIR
    / "step17b_uncertainty_sensitivity.json"
)


output = {

    "primary_analysis":
        (
            "All valid agricultural-domain retrievals; "
            "no universal hard RU threshold."
        ),

    "RU_definition":
        (
            "100 * native PyEOGPR absolute uncertainty "
            "/ positive retrieved trait value."
        ),

    "RU_thresholds_percent":
        RU_THRESHOLDS,

    "interpretation_warning":
        (
            "RU increases mechanically as the retrieved "
            "trait approaches zero. Threshold filtering "
            "therefore changes both uncertainty and the "
            "trait-magnitude distribution."
        ),

    "window_results":
        window_rows,

    "correlation_results":
        correlation_rows,

    "GOOD_window_summary":
        summary_rows,
}


with open(
    json_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        output,
        f,
        indent=2,
    )


# ======================================================
# FINISH
# ======================================================

print("\n" + "=" * 96)
print("STEP 17B OUTPUTS")
print("=" * 96)

print(
    "Window sensitivity:",
    window_csv,
)

print(
    "Correlation sensitivity:",
    correlation_csv,
)

print(
    "GOOD-window summary:",
    summary_csv,
)

print(
    "Full JSON:",
    json_path,
)


print("\n" + "=" * 96)
print("✅ STEP 17B COMPLETE")
print("=" * 96)