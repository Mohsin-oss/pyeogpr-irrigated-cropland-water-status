from pathlib import Path
import csv
import json
import math

import numpy as np
import rasterio


# ======================================================
# PROJECT
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "final_evidence"
    / "step20a"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# INPUT PATHS
# ======================================================

SEASON_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17a"
    / "seasonal_window_statistics.csv"
)

SPATIAL_CORR_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17a"
    / "spatial_correlations_by_window.csv"
)

TEMPORAL_CORR_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17a"
    / "temporal_correlations_good_windows.csv"
)

RU_SUMMARY_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17b"
    / "ru_good_window_summary.csv"
)

STABLE_SUMMARY_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17c"
    / "stable_support_summary.csv"
)

STABLE_JSON = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17c"
    / "step17c_stable_support.json"
)

HYDRO_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "hydroclimate"
    / "hydroclimate_15day_windows.csv"
)

HYDRO_CORR_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step18b"
    / "EO_hydroclimate_correlations_GOOD.csv"
)

MASK_SENSITIVITY_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "qa"
    / "mask_sensitivity_summary.csv"
)

MASK_MANIFEST = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_C25_N40_manifest.json"
)

FINAL_MASK_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_C25_N40_final.tif"
)

REFERENCE_GOOD_RASTER = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "final"
    / "pyeogpr_W06_20260129_20260213_final.tif"
)


# ======================================================
# WINDOW DEFINITIONS
# ======================================================

WINDOW_ORDER = [
    "W01",
    "W02",
    "W03",
    "W04",
    "W05",
    "W06",
    "W07",
    "W08",
    "W09",
    "W10",
]

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

EXPECTED_AVAILABLE_EO = [
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


print("=" * 100)
print("STEP 20A — FINAL RESULTS TABLES + EVIDENCE AUDIT")
print("=" * 100)


# ======================================================
# HELPERS
# ======================================================

def read_csv(path):

    if not path.exists():
        raise FileNotFoundError(path)

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def read_json(path):

    if not path.exists():
        raise FileNotFoundError(path)

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def write_csv(
    path,
    rows,
):

    if len(rows) == 0:
        raise RuntimeError(
            f"No rows supplied for {path}"
        )

    with open(
        path,
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
        writer.writerows(rows)


def ffloat(
    value,
    default=np.nan,
):

    if value is None:
        return default

    text = str(value).strip()

    if text == "":
        return default

    try:
        return float(text)

    except Exception:
        return default


def fint(
    value,
    default=None,
):

    try:
        return int(
            float(value)
        )

    except Exception:
        return default


def rounded(
    value,
    digits,
):

    value = ffloat(value)

    if not np.isfinite(value):
        return ""

    return round(
        value,
        digits,
    )


def require(
    condition,
    message,
):

    if not condition:
        AUDIT_ERRORS.append(
            message
        )


def warn(
    condition,
    message,
):

    if not condition:
        AUDIT_WARNINGS.append(
            message
        )


# ======================================================
# STORAGE
# ======================================================

AUDIT_ERRORS = []
AUDIT_WARNINGS = []


# ======================================================
# LOAD ALL EVIDENCE
# ======================================================

season_rows = read_csv(
    SEASON_CSV
)

spatial_rows = read_csv(
    SPATIAL_CORR_CSV
)

temporal_rows = read_csv(
    TEMPORAL_CORR_CSV
)

ru_rows = read_csv(
    RU_SUMMARY_CSV
)

stable_rows = read_csv(
    STABLE_SUMMARY_CSV
)

stable_json = read_json(
    STABLE_JSON
)

hydro_rows = read_csv(
    HYDRO_CSV
)

hydro_corr_rows = read_csv(
    HYDRO_CORR_CSV
)

mask_sensitivity_rows = read_csv(
    MASK_SENSITIVITY_CSV
)

mask_manifest = read_json(
    MASK_MANIFEST
)


# ======================================================
# 1. BASIC FILE/ROW AUDIT
# ======================================================

print("\n" + "=" * 100)
print("1. BASIC EVIDENCE AUDIT")
print("=" * 100)


season_ids = [
    row["window_id"]
    for row in season_rows
]

hydro_ids = [
    row["window_id"]
    for row in hydro_rows
]


require(
    season_ids == EXPECTED_AVAILABLE_EO,
    (
        "Seasonal EO table does not contain exactly "
        "W01,W02,W04,W05,W06,W07,W08,W09,W10 "
        "in expected order."
    ),
)


require(
    hydro_ids == WINDOW_ORDER,
    (
        "Hydroclimate table does not contain "
        "all ten windows W01-W10."
    ),
)


season_lookup = {
    row["window_id"]:
        row
    for row in season_rows
}


require(
    season_lookup[
        "W09"
    ][
        "status"
    ] == "LIMITED",
    "W09 is not labelled LIMITED.",
)


require(
    len(temporal_rows) == 6,
    (
        "Expected six PyEOGPR/index "
        "temporal correlation pairs."
    ),
)


for row in temporal_rows:

    require(
        fint(
            row["n_windows"]
        ) == 8,
        (
            f"{row['trait']} vs "
            f"{row['index']} temporal correlation "
            "does not use exactly eight GOOD windows."
        ),
    )


require(
    len(ru_rows) == 9,
    (
        "RU summary should contain "
        "3 traits × 3 thresholds = 9 rows."
    ),
)


require(
    len(mask_sensitivity_rows) == 9,
    (
        "Mask sensitivity should contain "
        "nine candidate masks."
    ),
)


require(
    len(stable_rows) == 5,
    (
        "Stable-support summary should contain "
        "Cw, laiCw, LAI, NDVI and NDMI."
    ),
)


require(
    len(hydro_corr_rows) == 20,
    (
        "Hydroclimate correlation table should contain "
        "5 EO variables × 4 environmental variables."
    ),
)


print(
    "Seasonal EO rows:",
    len(season_rows),
)

print(
    "Hydroclimate rows:",
    len(hydro_rows),
)

print(
    "Temporal correlations:",
    len(temporal_rows),
)

print(
    "Spatial correlation records:",
    len(spatial_rows),
)

print(
    "RU summary rows:",
    len(ru_rows),
)

print(
    "Mask candidates:",
    len(mask_sensitivity_rows),
)


# ======================================================
# 2. FINAL MASK / OBSERVATION-FOOTPRINT AUDIT
# ======================================================

print("\n" + "=" * 100)
print("2. FINAL MASK + RETRIEVAL FOOTPRINT AUDIT")
print("=" * 100)


require(
    mask_manifest.get(
        "status"
    )
    == "FROZEN_PRIMARY_ANALYSIS_MASK",
    "Mask manifest is not marked FROZEN_PRIMARY_ANALYSIS_MASK.",
)


driver_file = str(
    mask_manifest.get(
        "driver_file",
        "",
    )
)


require(
    "_v2" in driver_file,
    (
        "Final mask manifest does not point to "
        "the projection-corrected v2 driver raster."
    ),
)


# ------------------------------------------------------
# Read agricultural mask
# ------------------------------------------------------

with rasterio.open(
    FINAL_MASK_PATH
) as src:

    mask_data = src.read(
        1,
        masked=True,
    )

    mask_transform = src.transform
    mask_crs = src.crs
    mask_width = src.width
    mask_height = src.height


agricultural_mask = (

    ~np.ma.getmaskarray(
        mask_data
    )

    & (
        mask_data.filled(0)
        == 1
    )
)


mask_defined_pixels = int(
    agricultural_mask.sum()
)


pixel_area_m2 = abs(
    mask_transform.a
    * mask_transform.e
)


mask_defined_area_km2 = (

    mask_defined_pixels
    * pixel_area_m2
    / 1_000_000
)


# ------------------------------------------------------
# Use one GOOD production product to define the actual
# retrieval-supported footprint.
#
# Step 17C established that all eight GOOD windows use
# exactly the same common footprint.
# ------------------------------------------------------

with rasterio.open(
    REFERENCE_GOOD_RASTER
) as src:

    require(
        src.crs == mask_crs,
        "Reference GOOD raster CRS differs from final mask.",
    )

    require(
        src.width == mask_width
        and src.height == mask_height,
        "Reference GOOD raster dimensions differ from final mask.",
    )

    require(
        src.transform.almost_equals(
            mask_transform
        ),
        "Reference GOOD raster transform differs from final mask.",
    )

    pyeo = src.read(
        masked=True
    )


pyeo_mask = np.any(
    np.ma.getmaskarray(
        pyeo
    ),
    axis=0,
)


pyeo_data = pyeo.filled(
    np.nan
)


pyeo_finite = np.all(
    np.isfinite(
        pyeo_data
    ),
    axis=0,
)


good_retrieval_footprint = (
    (~pyeo_mask)
    & pyeo_finite
)


supported_agricultural = (
    agricultural_mask
    & good_retrieval_footprint
)


supported_pixels = int(
    supported_agricultural.sum()
)


unsupported_agricultural_pixels = (
    mask_defined_pixels
    - supported_pixels
)


supported_pct_of_mask = (

    100.0
    * supported_pixels
    / mask_defined_pixels
)


supported_area_km2 = (

    supported_pixels
    * pixel_area_m2
    / 1_000_000
)


stable_pixels_reported = int(
    stable_json[
        "stable_good_window_pixels"
    ]
)


require(
    supported_pixels
    == stable_pixels_reported,
    (
        "Reference GOOD retrieval footprint does not match "
        "the Step 17C stable GOOD-window core."
    ),
)


print(
    "Mask-defined agricultural pixels:",
    mask_defined_pixels,
)

print(
    f"Mask-defined agricultural area: "
    f"{mask_defined_area_km2:.4f} km²"
)

print(
    "GOOD-window supported agricultural pixels:",
    supported_pixels,
)

print(
    f"GOOD-window supported agricultural area: "
    f"{supported_area_km2:.4f} km²"
)

print(
    "Agricultural pixels outside GOOD retrieval footprint:",
    unsupported_agricultural_pixels,
)

print(
    f"Supported fraction of frozen mask: "
    f"{supported_pct_of_mask:.4f}%"
)


if unsupported_agricultural_pixels > 0:

    AUDIT_WARNINGS.append(
        (
            f"The threshold-defined C25-N40 mask contains "
            f"{unsupported_agricultural_pixels} agricultural pixels "
            f"outside the common GOOD-window retrieval footprint. "
            f"All Step 17 analyses already excluded these through "
            f"the common-validity mask. Report the effective "
            f"analysis-supported agricultural domain as "
            f"{supported_pixels} pixels "
            f"({supported_area_km2:.4f} km²), while retaining "
            f"{mask_defined_pixels} pixels "
            f"({mask_defined_area_km2:.4f} km²) as the "
            f"threshold-defined mask."
        )
    )


# ======================================================
# 3. MASK-SENSITIVITY AUDIT
# ======================================================

print("\n" + "=" * 100)
print("3. AGRICULTURAL MASK SENSITIVITY AUDIT")
print("=" * 100)


mask_areas = np.asarray(
    [
        ffloat(
            row["area_percent"]
        )
        for row in mask_sensitivity_rows
    ],
    dtype=float,
)


mask_max_nmad = np.asarray(
    [
        ffloat(
            row["maximum_normalized_MAD_pct"]
        )
        for row in mask_sensitivity_rows
    ],
    dtype=float,
)


mask_min_r = np.asarray(
    [
        ffloat(
            row["minimum_seasonal_pearson_r"]
        )
        for row in mask_sensitivity_rows
    ],
    dtype=float,
)


mask_area_min = float(
    np.nanmin(
        mask_areas
    )
)

mask_area_max = float(
    np.nanmax(
        mask_areas
    )
)

mask_area_spread = (
    mask_area_max
    - mask_area_min
)


maximum_mask_nmad = float(
    np.nanmax(
        mask_max_nmad
    )
)


minimum_mask_r = float(
    np.nanmin(
        mask_min_r
    )
)


require(
    mask_area_spread > 0.1,
    (
        "Mask candidates are nearly/fully identical; "
        "possible stale failed v1 sensitivity result."
    ),
)


require(
    mask_area_max < 99.0,
    (
        "Mask candidate area approaches 100%; "
        "possible stale v1 constant-driver result."
    ),
)


print(
    f"Candidate area range: "
    f"{mask_area_min:.4f}% → "
    f"{mask_area_max:.4f}%"
)

print(
    f"Area spread: "
    f"{mask_area_spread:.4f} percentage points"
)

print(
    f"Maximum normalized trajectory MAD: "
    f"{maximum_mask_nmad:.4f}%"
)

print(
    f"Minimum trajectory Pearson r: "
    f"{minimum_mask_r:.6f}"
)


# ======================================================
# 4. STABLE-SPATIAL-SUPPORT AUDIT
# ======================================================

print("\n" + "=" * 100)
print("4. STABLE-SPATIAL-SUPPORT AUDIT")
print("=" * 100)


stable_pct = ffloat(
    stable_json[
        "stable_good_window_percent"
    ]
)


w09_stable_pct = ffloat(
    stable_json[
        "W09_stable_core_coverage_percent"
    ]
)


stable_nmad = np.asarray(
    [
        ffloat(
            row[
                "normalized_mean_absolute_difference_percent"
            ]
        )
        for row in stable_rows
    ],
    dtype=float,
)


stable_r = np.asarray(
    [
        ffloat(
            row[
                "trajectory_pearson_r"
            ]
        )
        for row in stable_rows
    ],
    dtype=float,
)


maximum_stable_nmad = float(
    np.nanmax(
        stable_nmad
    )
)


minimum_stable_r = float(
    np.nanmin(
        stable_r
    )
)


print(
    f"Stable GOOD-window support: "
    f"{stable_pct:.4f}%"
)

print(
    f"Maximum stable-support nMAD: "
    f"{maximum_stable_nmad:.6f}%"
)

print(
    f"Minimum stable-support trajectory r: "
    f"{minimum_stable_r:.6f}"
)

print(
    f"W09 coverage of stable core: "
    f"{w09_stable_pct:.4f}%"
)


# ======================================================
# 5. BUILD TABLE 1 — FINAL SEASONAL SUMMARY
# ======================================================

hydro_lookup = {
    row["window_id"]:
        row
    for row in hydro_rows
}


table1 = []


for window_id in WINDOW_ORDER:

    hydro = hydro_lookup[
        window_id
    ]


    if window_id in season_lookup:

        eo = season_lookup[
            window_id
        ]

        status = eo[
            "status"
        ]

        coverage = rounded(
            eo[
                "common_coverage_percent"
            ],
            2,
        )

        Cw = rounded(
            eo["Cw_p50"],
            6,
        )

        laiCw = rounded(
            eo["laiCw_p50"],
            2,
        )

        LAI = rounded(
            eo["LAI_p50"],
            3,
        )

        NDVI = rounded(
            eo["NDVI_p50"],
            4,
        )

        NDMI = rounded(
            eo["NDMI_p50"],
            4,
        )

    else:

        status = "MISSING"

        coverage = ""
        Cw = ""
        laiCw = ""
        LAI = ""
        NDVI = ""
        NDMI = ""


    table1.append({

        "window":
            window_id,

        "EO_status":
            status,

        "common_agricultural_coverage_pct":
            coverage,

        "Cw_median_cm":
            Cw,

        "laiCw_median_g_m2":
            laiCw,

        "LAI_median_m2_m2":
            LAI,

        "NDVI_median":
            NDVI,

        "NDMI_median":
            NDMI,

        "rainfall_15d_mm":
            rounded(
                hydro[
                    "rainfall_window_mm"
                ],
                2,
            ),

        "antecedent_rainfall_30d_mm":
            rounded(
                hydro[
                    "rainfall_prior30_mm"
                ],
                2,
            ),

        "soil_water_0_28cm_proxy_m3m3":
            rounded(
                hydro[
                    "soil_water_0_28cm_proxy_m3m3"
                ],
                4,
            ),

        "temperature_2m_C":
            rounded(
                hydro[
                    "temperature_2m_C"
                ],
                2,
            ),
    })


# ======================================================
# 6. TABLE 2 — GOOD-WINDOW TEMPORAL CORRELATIONS
# ======================================================

table2 = []


for row in temporal_rows:

    table2.append({

        "trait":
            row["trait"],

        "index":
            row["index"],

        "n_GOOD_windows":
            fint(
                row["n_windows"]
            ),

        "Pearson_r":
            rounded(
                row["pearson_r"],
                4,
            ),

        "Spearman_r":
            rounded(
                row["spearman_r"],
                4,
            ),
    })


# ======================================================
# 7. TABLE 3 — GOOD-WINDOW SPATIAL CORRELATION SUMMARY
# ======================================================

pairs = sorted(
    set(
        (
            row["trait"],
            row["index"],
        )
        for row in spatial_rows
    )
)


table3 = []


for trait, index_name in pairs:

    subset = [

        row
        for row in spatial_rows

        if (
            row["trait"] == trait
            and row["index"] == index_name
            and row["status"] == "GOOD"
        )
    ]


    pearson = np.asarray(
        [
            ffloat(
                row["pearson_r"]
            )
            for row in subset
        ],
        dtype=float,
    )


    spearman = np.asarray(
        [
            ffloat(
                row["spearman_r"]
            )
            for row in subset
        ],
        dtype=float,
    )


    min_idx = int(
        np.nanargmin(
            pearson
        )
    )

    max_idx = int(
        np.nanargmax(
            pearson
        )
    )


    table3.append({

        "trait":
            trait,

        "index":
            index_name,

        "n_GOOD_windows":
            len(
                subset
            ),

        "Pearson_min":
            round(
                float(
                    np.nanmin(
                        pearson
                    )
                ),
                4,
            ),

        "Pearson_median":
            round(
                float(
                    np.nanmedian(
                        pearson
                    )
                ),
                4,
            ),

        "Pearson_max":
            round(
                float(
                    np.nanmax(
                        pearson
                    )
                ),
                4,
            ),

        "Pearson_min_window":
            subset[
                min_idx
            ][
                "window_id"
            ],

        "Pearson_max_window":
            subset[
                max_idx
            ][
                "window_id"
            ],

        "Spearman_min":
            round(
                float(
                    np.nanmin(
                        spearman
                    )
                ),
                4,
            ),

        "Spearman_median":
            round(
                float(
                    np.nanmedian(
                        spearman
                    )
                ),
                4,
            ),

        "Spearman_max":
            round(
                float(
                    np.nanmax(
                        spearman
                    )
                ),
                4,
            ),
    })


# ======================================================
# 8. TABLE 4 — RU SENSITIVITY
# ======================================================

table4 = []


for row in ru_rows:

    table4.append({

        "trait":
            row["trait"],

        "comparison_index":
            row[
                "comparison_index"
            ],

        "RU_threshold_pct":
            fint(
                row[
                    "RU_threshold_percent"
                ]
            ),

        "retention_min_pct":
            rounded(
                row[
                    "minimum_retention_percent"
                ],
                2,
            ),

        "retention_median_pct":
            rounded(
                row[
                    "median_retention_percent"
                ],
                2,
            ),

        "retention_max_pct":
            rounded(
                row[
                    "maximum_retention_percent"
                ],
                2,
            ),

        "median_agricultural_domain_retained_pct":
            rounded(
                row[
                    "median_agricultural_domain_retention_percent"
                ],
                2,
            ),

        "max_absolute_median_shift_pct":
            rounded(
                row[
                    "maximum_absolute_median_shift_percent"
                ],
                2,
            ),

        "median_absolute_median_shift_pct":
            rounded(
                row[
                    "median_absolute_median_shift_percent"
                ],
                2,
            ),

        "median_filtered_spatial_Pearson_r":
            rounded(
                row[
                    "median_filtered_spatial_pearson_r"
                ],
                4,
            ),
    })


# ======================================================
# 9. TABLE 5 — ROBUSTNESS CHECKS
# ======================================================

table5 = [

    {
        "test":
            "Agricultural-mask threshold sensitivity",

        "primary_result":
            (
                f"Area {mask_area_min:.2f}–"
                f"{mask_area_max:.2f}%"
            ),

        "secondary_result":
            (
                f"max nMAD="
                f"{maximum_mask_nmad:.2f}%; "
                f"min r="
                f"{minimum_mask_r:.4f}"
            ),

        "interpretation":
            (
                "Seasonal trajectories robust to "
                "reasonable mask-threshold perturbations."
            ),
    },

    {
        "test":
            "Stable GOOD-window spatial support",

        "primary_result":
            (
                f"{supported_pixels:,} pixels; "
                f"{supported_area_km2:.2f} km²"
            ),

        "secondary_result":
            (
                f"{stable_pct:.2f}% of threshold-defined "
                f"agricultural mask"
            ),

        "interpretation":
            (
                "All eight GOOD-window seasonal trajectories "
                "use the same retrieval-supported agricultural footprint."
            ),
    },

    {
        "test":
            "Stable-support trajectory sensitivity",

        "primary_result":
            (
                f"max nMAD="
                f"{maximum_stable_nmad:.4f}%"
            ),

        "secondary_result":
            (
                f"min trajectory r="
                f"{minimum_stable_r:.6f}"
            ),

        "interpretation":
            (
                "Seasonal medians unchanged when restricted "
                "to identical spatial support."
            ),
    },

    {
        "test":
            "W09 spatial support",

        "primary_result":
            (
                f"{w09_stable_pct:.2f}% "
                "of stable GOOD-window core"
            ),

        "secondary_result":
            "Status = LIMITED",

        "interpretation":
            (
                "W09 retained descriptively but excluded "
                "from primary eight-window temporal correlations."
            ),
    },

    {
        "test":
            "Relative-uncertainty filtering",

        "primary_result":
            "RU <20%, <30%, <40% tested",

        "secondary_result":
            (
                "Strong retention loss and "
                "large trait-median shifts"
            ),

        "interpretation":
            (
                "RU thresholds are sensitivity treatments only; "
                "no universal hard RU cutoff used."
            ),
    },

]


# ======================================================
# 10. TABLE 6 — EO / HYDROCLIMATE CORRELATIONS
# ======================================================

table6 = []


for row in hydro_corr_rows:

    table6.append({

        "EO_variable":
            row[
                "EO_variable"
            ],

        "environmental_variable":
            row[
                "climate_variable"
            ],

        "n_GOOD_windows":
            fint(
                row[
                    "n_windows"
                ]
            ),

        "Pearson_r":
            rounded(
                row[
                    "pearson_r"
                ],
                4,
            ),

        "Spearman_r":
            rounded(
                row[
                    "spearman_r"
                ],
                4,
            ),
    })


# ======================================================
# 11. HEADLINE EVIDENCE REGISTER
# ======================================================

def temporal_pair(
    trait,
    index_name,
):

    matches = [

        row
        for row in temporal_rows

        if (
            row["trait"] == trait
            and row["index"] == index_name
        )
    ]

    if len(matches) != 1:
        raise RuntimeError(
            f"Could not uniquely find "
            f"{trait} vs {index_name}"
        )

    return matches[0]


def spatial_pair_summary(
    trait,
    index_name,
):

    matches = [

        row
        for row in table3

        if (
            row["trait"] == trait
            and row["index"] == index_name
        )
    ]

    if len(matches) != 1:
        raise RuntimeError(
            f"Could not find spatial summary "
            f"{trait} vs {index_name}"
        )

    return matches[0]


lai_ndvi = temporal_pair(
    "laiCw",
    "NDVI",
)

lai_ndmi = temporal_pair(
    "laiCw",
    "NDMI",
)

lai_lai_ndvi = temporal_pair(
    "LAI",
    "NDVI",
)

cw_ndmi_spatial = spatial_pair_summary(
    "Cw",
    "NDMI",
)


ru_max_row = max(
    ru_rows,
    key=lambda row:
        ffloat(
            row[
                "maximum_absolute_median_shift_percent"
            ],
            -np.inf,
        ),
)


strongest_hydro = max(
    hydro_corr_rows,
    key=lambda row:
        abs(
            ffloat(
                row[
                    "pearson_r"
                ],
                0,
            )
        ),
)


evidence_register = {

    "analysis_status":
        "FINAL_EVIDENCE_AUDIT",

    "primary_analysis": {

        "threshold_defined_mask":
            "C25-N40",

        "threshold_defined_agricultural_pixels":
            mask_defined_pixels,

        "threshold_defined_agricultural_area_km2":
            mask_defined_area_km2,

        "GOOD_window_supported_agricultural_pixels":
            supported_pixels,

        "GOOD_window_supported_agricultural_area_km2":
            supported_area_km2,

        "GOOD_window_supported_fraction_of_mask_pct":
            supported_pct_of_mask,

        "GOOD_windows":
            GOOD_WINDOWS,

        "limited_window":
            "W09",

        "missing_window":
            "W03",
    },

    "headline_results": {

        "laiCw_vs_NDVI_temporal_Pearson_r":
            ffloat(
                lai_ndvi[
                    "pearson_r"
                ]
            ),

        "laiCw_vs_NDMI_temporal_Pearson_r":
            ffloat(
                lai_ndmi[
                    "pearson_r"
                ]
            ),

        "LAI_vs_NDVI_temporal_Pearson_r":
            ffloat(
                lai_lai_ndvi[
                    "pearson_r"
                ]
            ),

        "Cw_vs_NDMI_spatial_Pearson_range_GOOD":
            [
                cw_ndmi_spatial[
                    "Pearson_min"
                ],
                cw_ndmi_spatial[
                    "Pearson_max"
                ],
            ],

        "Cw_vs_NDMI_spatial_min_window":
            cw_ndmi_spatial[
                "Pearson_min_window"
            ],

        "Cw_vs_NDMI_spatial_max_window":
            cw_ndmi_spatial[
                "Pearson_max_window"
            ],

        "mask_sensitivity_max_normalized_MAD_pct":
            maximum_mask_nmad,

        "stable_support_max_normalized_MAD_pct":
            maximum_stable_nmad,

        "largest_RU_filter_median_shift": {

            "trait":
                ru_max_row[
                    "trait"
                ],

            "RU_threshold_pct":
                fint(
                    ru_max_row[
                        "RU_threshold_percent"
                    ]
                ),

            "maximum_absolute_median_shift_pct":
                ffloat(
                    ru_max_row[
                        "maximum_absolute_median_shift_percent"
                    ]
                ),
        },

        "strongest_absolute_raw_hydroclimate_Pearson": {

            "EO_variable":
                strongest_hydro[
                    "EO_variable"
                ],

            "climate_variable":
                strongest_hydro[
                    "climate_variable"
                ],

            "Pearson_r":
                ffloat(
                    strongest_hydro[
                        "pearson_r"
                    ]
                ),

            "interpretation":
                (
                    "Descriptive only; not causal and "
                    "strongly confounded by seasonal phenology."
                ),
        },
    },

    "claim_boundaries": [

        (
            "PyEOGPR/index agreement is comparison between "
            "Sentinel-2-derived approaches, not independent validation."
        ),

        (
            "Cw's weaker or more variable relationship with indices "
            "does not prove superior water-stress sensitivity."
        ),

        (
            "CHIRPS and ERA5-Land provide environmental context "
            "and do not measure field-level irrigation."
        ),

        (
            "RU thresholds are sensitivity treatments only."
        ),

        (
            "W09 is retained descriptively but excluded from "
            "primary GOOD-window temporal correlations."
        ),

        (
            "W03 is a genuine missing EO window and is not interpolated."
        ),
    ],

    "source_files": {

        "seasonal_statistics":
            str(SEASON_CSV),

        "spatial_correlations":
            str(SPATIAL_CORR_CSV),

        "temporal_correlations":
            str(TEMPORAL_CORR_CSV),

        "RU_sensitivity":
            str(RU_SUMMARY_CSV),

        "stable_support":
            str(STABLE_SUMMARY_CSV),

        "hydroclimate":
            str(HYDRO_CSV),

        "hydroclimate_correlations":
            str(HYDRO_CORR_CSV),

        "mask_sensitivity":
            str(MASK_SENSITIVITY_CSV),

        "mask_manifest":
            str(MASK_MANIFEST),
    },
}


# ======================================================
# 12. WRITE OUTPUT TABLES
# ======================================================

TABLE1_PATH = (
    OUTPUT_DIR
    / "Table_01_final_seasonal_summary.csv"
)

TABLE2_PATH = (
    OUTPUT_DIR
    / "Table_02_temporal_correlations_GOOD.csv"
)

TABLE3_PATH = (
    OUTPUT_DIR
    / "Table_03_spatial_correlation_summary_GOOD.csv"
)

TABLE4_PATH = (
    OUTPUT_DIR
    / "Table_04_RU_sensitivity.csv"
)

TABLE5_PATH = (
    OUTPUT_DIR
    / "Table_05_robustness_checks.csv"
)

TABLE6_PATH = (
    OUTPUT_DIR
    / "Table_06_EO_hydroclimate_correlations.csv"
)


write_csv(
    TABLE1_PATH,
    table1,
)

write_csv(
    TABLE2_PATH,
    table2,
)

write_csv(
    TABLE3_PATH,
    table3,
)

write_csv(
    TABLE4_PATH,
    table4,
)

write_csv(
    TABLE5_PATH,
    table5,
)

write_csv(
    TABLE6_PATH,
    table6,
)


# ======================================================
# 13. WRITE EVIDENCE REGISTER
# ======================================================

REGISTER_PATH = (
    OUTPUT_DIR
    / "final_evidence_register.json"
)


with open(
    REGISTER_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        evidence_register,
        f,
        indent=2,
    )


# ======================================================
# 14. WRITE HUMAN-READABLE AUDIT REPORT
# ======================================================

REPORT_PATH = (
    OUTPUT_DIR
    / "final_evidence_audit.txt"
)


with open(
    REPORT_PATH,
    "w",
    encoding="utf-8",
) as f:

    f.write(
        "STEP 20A — FINAL EVIDENCE AUDIT\n"
    )

    f.write(
        "=" * 80
        + "\n\n"
    )


    f.write(
        "PRIMARY DOMAIN\n"
    )

    f.write(
        "-" * 80
        + "\n"
    )

    f.write(
        f"Threshold-defined C25-N40 mask: "
        f"{mask_defined_pixels:,} pixels "
        f"({mask_defined_area_km2:.4f} km²)\n"
    )

    f.write(
        f"GOOD-window retrieval-supported agricultural domain: "
        f"{supported_pixels:,} pixels "
        f"({supported_area_km2:.4f} km²)\n"
    )

    f.write(
        f"Supported fraction of threshold mask: "
        f"{supported_pct_of_mask:.4f}%\n"
    )

    f.write(
        f"W09 stable-core coverage: "
        f"{w09_stable_pct:.4f}%\n\n"
    )


    f.write(
        "HEADLINE CORRELATIONS\n"
    )

    f.write(
        "-" * 80
        + "\n"
    )

    f.write(
        f"laiCw vs NDVI temporal Pearson r = "
        f"{ffloat(lai_ndvi['pearson_r']):.4f}\n"
    )

    f.write(
        f"laiCw vs NDMI temporal Pearson r = "
        f"{ffloat(lai_ndmi['pearson_r']):.4f}\n"
    )

    f.write(
        f"LAI vs NDVI temporal Pearson r = "
        f"{ffloat(lai_lai_ndvi['pearson_r']):.4f}\n"
    )

    f.write(
        f"Cw vs NDMI spatial Pearson range across GOOD windows = "
        f"{cw_ndmi_spatial['Pearson_min']:.4f} "
        f"to {cw_ndmi_spatial['Pearson_max']:.4f}\n\n"
    )


    f.write(
        "ROBUSTNESS\n"
    )

    f.write(
        "-" * 80
        + "\n"
    )

    f.write(
        f"Mask sensitivity area range = "
        f"{mask_area_min:.4f}% to "
        f"{mask_area_max:.4f}%\n"
    )

    f.write(
        f"Maximum mask-sensitivity nMAD = "
        f"{maximum_mask_nmad:.4f}%\n"
    )

    f.write(
        f"Stable-support maximum nMAD = "
        f"{maximum_stable_nmad:.6f}%\n"
    )

    f.write(
        f"Stable-support minimum trajectory r = "
        f"{minimum_stable_r:.6f}\n\n"
    )


    f.write(
        "UNCERTAINTY\n"
    )

    f.write(
        "-" * 80
        + "\n"
    )

    f.write(
        f"Largest RU-induced maximum median shift = "
        f"{ru_max_row['trait']} at RU <"
        f"{fint(ru_max_row['RU_threshold_percent'])}%: "
        f"{ffloat(ru_max_row['maximum_absolute_median_shift_percent']):.2f}%\n"
    )

    f.write(
        "No universal hard RU threshold is used.\n\n"
    )


    f.write(
        "HYDROCLIMATE\n"
    )

    f.write(
        "-" * 80
        + "\n"
    )

    f.write(
        f"Strongest absolute raw Pearson association = "
        f"{strongest_hydro['EO_variable']} vs "
        f"{strongest_hydro['climate_variable']}: "
        f"r={ffloat(strongest_hydro['pearson_r']):+.4f}\n"
    )

    f.write(
        "Interpretation: descriptive environmental context only; "
        "not causal validation.\n\n"
    )


    f.write(
        "AUDIT WARNINGS\n"
    )

    f.write(
        "-" * 80
        + "\n"
    )

    if len(
        AUDIT_WARNINGS
    ) == 0:

        f.write(
            "None.\n"
        )

    else:

        for item in AUDIT_WARNINGS:

            f.write(
                f"- {item}\n"
            )


    f.write(
        "\nAUDIT ERRORS\n"
    )

    f.write(
        "-" * 80
        + "\n"
    )

    if len(
        AUDIT_ERRORS
    ) == 0:

        f.write(
            "None.\n"
        )

    else:

        for item in AUDIT_ERRORS:

            f.write(
                f"- {item}\n"
            )


# ======================================================
# 15. FINAL TERMINAL SUMMARY
# ======================================================

print("\n" + "=" * 100)
print("FINAL EVIDENCE AUDIT SUMMARY")
print("=" * 100)

print(
    f"Threshold-defined agricultural mask: "
    f"{mask_defined_pixels:,} pixels "
    f"({mask_defined_area_km2:.2f} km²)"
)

print(
    f"GOOD-window supported agricultural domain: "
    f"{supported_pixels:,} pixels "
    f"({supported_area_km2:.2f} km²)"
)

print(
    f"Supported mask fraction: "
    f"{supported_pct_of_mask:.4f}%"
)

print(
    f"W09 stable-core coverage: "
    f"{w09_stable_pct:.4f}%"
)

print(
    f"Mask sensitivity max nMAD: "
    f"{maximum_mask_nmad:.4f}%"
)

print(
    f"Stable-support max nMAD: "
    f"{maximum_stable_nmad:.6f}%"
)

print(
    f"laiCw–NDVI temporal r: "
    f"{ffloat(lai_ndvi['pearson_r']):.4f}"
)

print(
    f"laiCw–NDMI temporal r: "
    f"{ffloat(lai_ndmi['pearson_r']):.4f}"
)

print(
    f"LAI–NDVI temporal r: "
    f"{ffloat(lai_lai_ndvi['pearson_r']):.4f}"
)

print(
    f"Cw–NDMI spatial r range: "
    f"{cw_ndmi_spatial['Pearson_min']:.4f} "
    f"to "
    f"{cw_ndmi_spatial['Pearson_max']:.4f}"
)


print("\nAudit warnings:")

if AUDIT_WARNINGS:

    for item in AUDIT_WARNINGS:

        print(
            "⚠️",
            item
        )

else:

    print(
        "None."
    )


print("\nAudit errors:")

if AUDIT_ERRORS:

    for item in AUDIT_ERRORS:

        print(
            "❌",
            item
        )

else:

    print(
        "None."
    )


print("\nOutputs:")

for path in [
    TABLE1_PATH,
    TABLE2_PATH,
    TABLE3_PATH,
    TABLE4_PATH,
    TABLE5_PATH,
    TABLE6_PATH,
    REGISTER_PATH,
    REPORT_PATH,
]:

    print(
        path
    )


print("\n" + "=" * 100)

if AUDIT_ERRORS:

    print(
        "❌ STEP 20A DID NOT PASS — "
        "resolve audit errors before manuscript writing."
    )

else:

    print(
        "✅ STEP 20A COMPLETE — "
        "FINAL NUMERICAL EVIDENCE LOCKED."
    )

print("=" * 100)