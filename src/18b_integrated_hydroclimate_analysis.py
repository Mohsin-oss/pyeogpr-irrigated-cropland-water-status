from pathlib import Path
import csv
import json

import numpy as np


# ======================================================
# PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EO_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17a"
    / "seasonal_window_statistics.csv"
)

CLIMATE_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "hydroclimate"
    / "hydroclimate_15day_windows.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step18b"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# VARIABLES
# ======================================================

EO_VARIABLES = [
    "Cw",
    "laiCw",
    "LAI",
    "NDVI",
    "NDMI",
]


CLIMATE_VARIABLES = {

    "P15":
        "rainfall_window_mm",

    "Pprior30":
        "rainfall_prior30_mm",

    "SM0_28":
        "soil_water_0_28cm_proxy_m3m3",

    "T2m":
        "temperature_2m_C",
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


LIMITED_WINDOW = "W09"


print("=" * 96)
print("STEP 18B — INTEGRATED EO + HYDROCLIMATE ANALYSIS")
print("=" * 96)


# ======================================================
# HELPERS
# ======================================================

def pearson_r(x, y):

    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    valid = (
        np.isfinite(x)
        & np.isfinite(y)
    )

    x = x[valid]
    y = y[valid]

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
            and sorted_values[j] == sorted_values[i]
        ):
            j += 1

        average_rank = (
            (i + 1)
            + j
        ) / 2.0

        ranks[
            order[i:j]
        ] = average_rank

        i = j

    return ranks


def spearman_r(x, y):

    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    valid = (
        np.isfinite(x)
        & np.isfinite(y)
    )

    x = x[valid]
    y = y[valid]

    if len(x) < 3:
        return np.nan

    return pearson_r(
        rankdata(x),
        rankdata(y),
    )


def zscore(values):

    values = np.asarray(
        values,
        dtype=float,
    )

    mean = np.mean(
        values
    )

    std = np.std(
        values
    )

    if std == 0:
        return np.zeros_like(
            values
        )

    return (
        values - mean
    ) / std


# ======================================================
# 1. READ EO DATA
# ======================================================

eo = {}


with open(
    EO_CSV,
    "r",
    encoding="utf-8",
) as f:

    reader = csv.DictReader(
        f
    )

    for row in reader:

        window_id = (
            row["window_id"]
        )

        eo[
            window_id
        ] = {

            "status":
                row["status"],

            "Cw":
                float(
                    row["Cw_p50"]
                ),

            "laiCw":
                float(
                    row["laiCw_p50"]
                ),

            "LAI":
                float(
                    row["LAI_p50"]
                ),

            "NDVI":
                float(
                    row["NDVI_p50"]
                ),

            "NDMI":
                float(
                    row["NDMI_p50"]
                ),

            "coverage":
                float(
                    row[
                        "common_coverage_percent"
                    ]
                ),
        }


# ======================================================
# 2. READ HYDROCLIMATE DATA
# ======================================================

climate = {}


with open(
    CLIMATE_CSV,
    "r",
    encoding="utf-8",
) as f:

    reader = csv.DictReader(
        f
    )

    for row in reader:

        window_id = (
            row["window_id"]
        )

        climate[
            window_id
        ] = {

            "P15":
                float(
                    row[
                        "rainfall_window_mm"
                    ]
                ),

            "Pprior30":
                float(
                    row[
                        "rainfall_prior30_mm"
                    ]
                ),

            "SM0_28":
                float(
                    row[
                        "soil_water_0_28cm_proxy_m3m3"
                    ]
                ),

            "T2m":
                float(
                    row[
                        "temperature_2m_C"
                    ]
                ),
        }


# ======================================================
# 3. CHECK GOOD WINDOWS
# ======================================================

for window_id in GOOD_WINDOWS:

    if window_id not in eo:

        raise RuntimeError(
            f"{window_id}: missing EO data"
        )

    if window_id not in climate:

        raise RuntimeError(
            f"{window_id}: missing climate data"
        )


print(
    "\n✅ All 8 GOOD windows have "
    "matched EO + hydroclimate records."
)


# ======================================================
# 4. BUILD INTEGRATED TABLE
# ======================================================

integrated_rows = []


for window_id in [
    "W01",
    "W02",
    "W04",
    "W05",
    "W06",
    "W07",
    "W08",
    "W09",
    "W10",
]:

    row = {

        "window_id":
            window_id,

        "status":
            eo[
                window_id
            ]["status"],

        "coverage_percent":
            eo[
                window_id
            ]["coverage"],
    }


    for variable in EO_VARIABLES:

        row[
            variable
        ] = (
            eo[
                window_id
            ][
                variable
            ]
        )


    for variable in CLIMATE_VARIABLES:

        row[
            variable
        ] = (
            climate[
                window_id
            ][
                variable
            ]
        )


    integrated_rows.append(
        row
    )


# ======================================================
# 5. GOOD-WINDOW CORRELATIONS
# ======================================================

correlation_rows = []


for eo_variable in EO_VARIABLES:

    eo_values = np.asarray(
        [
            eo[
                window_id
            ][
                eo_variable
            ]

            for window_id
            in GOOD_WINDOWS
        ],
        dtype=float,
    )


    for climate_variable in CLIMATE_VARIABLES:

        climate_values = np.asarray(
            [
                climate[
                    window_id
                ][
                    climate_variable
                ]

                for window_id
                in GOOD_WINDOWS
            ],
            dtype=float,
        )


        correlation_rows.append({

            "EO_variable":
                eo_variable,

            "climate_variable":
                climate_variable,

            "n_windows":
                len(
                    GOOD_WINDOWS
                ),

            "windows":
                ",".join(
                    GOOD_WINDOWS
                ),

            "pearson_r":
                pearson_r(
                    eo_values,
                    climate_values,
                ),

            "spearman_r":
                spearman_r(
                    eo_values,
                    climate_values,
                ),
        })


# ======================================================
# 6. STANDARDIZED TRAJECTORIES
#
# These are descriptive only.
# Standardization allows variables with different units
# to be compared by relative seasonal position.
# ======================================================

standardized = {}


for variable in EO_VARIABLES:

    values = np.asarray(
        [
            eo[
                window_id
            ][
                variable
            ]

            for window_id
            in GOOD_WINDOWS
        ],
        dtype=float,
    )

    standardized[
        variable
    ] = zscore(
        values
    )


for variable in CLIMATE_VARIABLES:

    values = np.asarray(
        [
            climate[
                window_id
            ][
                variable
            ]

            for window_id
            in GOOD_WINDOWS
        ],
        dtype=float,
    )

    standardized[
        variable
    ] = zscore(
        values
    )


standardized_rows = []


for index, window_id in enumerate(
    GOOD_WINDOWS
):

    row = {
        "window_id":
            window_id,
    }


    for variable in standardized:

        row[
            variable
        ] = float(
            standardized[
                variable
            ][
                index
            ]
        )


    standardized_rows.append(
        row
    )


# ======================================================
# 7. PRINT CORRELATION MATRIX
# ======================================================

print("\n" + "=" * 96)
print("GOOD-WINDOW EO–HYDROCLIMATE CORRELATIONS")
print("=" * 96)


for row in correlation_rows:

    print(

        f"{row['EO_variable']} "
        f"vs {row['climate_variable']}"

        f" | Pearson="
        f"{row['pearson_r']:+.4f}"

        f" | Spearman="
        f"{row['spearman_r']:+.4f}"
    )


# ======================================================
# 8. W09 CONTEXT
# ======================================================

print("\n" + "=" * 96)
print("W09 LIMITED-WINDOW CONTEXT")
print("=" * 96)


w09 = next(
    row
    for row in integrated_rows
    if row["window_id"] == "W09"
)


print(
    f"coverage="
    f"{w09['coverage_percent']:.2f}%"
)

print(
    f"Cw={w09['Cw']:.6f}"
)

print(
    f"laiCw={w09['laiCw']:.2f}"
)

print(
    f"LAI={w09['LAI']:.3f}"
)

print(
    f"NDVI={w09['NDVI']:.4f}"
)

print(
    f"NDMI={w09['NDMI']:.4f}"
)

print(
    f"P15={w09['P15']:.2f} mm"
)

print(
    f"Pprior30={w09['Pprior30']:.2f} mm"
)

print(
    f"SM0_28={w09['SM0_28']:.4f}"
)

print(
    f"T2m={w09['T2m']:.2f} °C"
)


# ======================================================
# 9. SAVE INTEGRATED TABLE
# ======================================================

integrated_csv = (
    OUTPUT_DIR
    / "integrated_EO_hydroclimate.csv"
)


with open(
    integrated_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            integrated_rows[0].keys()
        ),
    )

    writer.writeheader()

    writer.writerows(
        integrated_rows
    )


# ======================================================
# 10. SAVE CORRELATIONS
# ======================================================

correlation_csv = (
    OUTPUT_DIR
    / "EO_hydroclimate_correlations_GOOD.csv"
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


# ======================================================
# 11. SAVE STANDARDIZED SERIES
# ======================================================

standardized_csv = (
    OUTPUT_DIR
    / "standardized_GOOD_window_trajectories.csv"
)


with open(
    standardized_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            standardized_rows[0].keys()
        ),
    )

    writer.writeheader()

    writer.writerows(
        standardized_rows
    )


# ======================================================
# 12. JSON
# ======================================================

json_path = (
    OUTPUT_DIR
    / "step18b_integrated_hydroclimate.json"
)


output = {

    "primary_windows":
        GOOD_WINDOWS,

    "n_primary_windows":
        len(
            GOOD_WINDOWS
        ),

    "limited_window":
        "W09",

    "interpretation": {

        "role_of_hydroclimate":
            (
                "Environmental temporal context only; "
                "not validation of PyEOGPR retrievals."
            ),

        "causality":
            (
                "Correlations are descriptive and "
                "must not be interpreted causally."
            ),

        "phenology_warning":
            (
                "EO variables and hydroclimate both "
                "change seasonally; raw temporal "
                "correlations may therefore reflect "
                "shared or opposing seasonal trends."
            ),

        "irrigation_warning":
            (
                "CHIRPS and ERA5-Land do not measure "
                "field-level canal irrigation."
            ),
    },

    "integrated_table":
        integrated_rows,

    "correlations":
        correlation_rows,

    "standardized_good_window_series":
        standardized_rows,
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
# 13. FINISH
# ======================================================

print("\n" + "=" * 96)
print("STEP 18B OUTPUTS")
print("=" * 96)

print(
    "Integrated table:",
    integrated_csv,
)

print(
    "Correlations:",
    correlation_csv,
)

print(
    "Standardized trajectories:",
    standardized_csv,
)

print(
    "JSON:",
    json_path,
)


print("\n" + "=" * 96)
print("✅ STEP 18B COMPLETE")
print("=" * 96)