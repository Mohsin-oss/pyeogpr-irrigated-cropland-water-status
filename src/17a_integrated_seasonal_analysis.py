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
    / "step17a"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


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


TRAITS = [
    "Cw",
    "laiCw",
    "LAI",
]


INDICES = [
    "NDVI",
    "NDMI",
]


CORRELATION_PAIRS = [

    ("Cw", "NDVI"),
    ("Cw", "NDMI"),

    ("laiCw", "NDVI"),
    ("laiCw", "NDMI"),

    ("LAI", "NDVI"),
    ("LAI", "NDMI"),
]


# Fixed reproducible spatial sample.
MAX_SPATIAL_SAMPLE = 10000
RANDOM_SEED = 42


print("=" * 94)
print("STEP 17A — INTEGRATED SEASONAL PyEOGPR + INDEX ANALYSIS")
print("=" * 94)


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


def distribution(values):

    values = np.asarray(
        values,
        dtype=float,
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:

        raise RuntimeError(
            "No finite values supplied."
        )

    p = np.percentile(
        values,
        [
            5,
            25,
            50,
            75,
            95,
        ],
    )

    return {

        "p5": float(p[0]),
        "p25": float(p[1]),
        "p50": float(p[2]),
        "p75": float(p[3]),
        "p95": float(p[4]),

        "iqr": float(
            p[3] - p[1]
        ),
    }


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


        # Average rank for ties.
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


# ======================================================
# 1. LOAD FINAL AGRICULTURAL MASK
# ======================================================

if not MASK_PATH.exists():

    raise FileNotFoundError(
        f"Final mask not found:\n"
        f"{MASK_PATH}"
    )


with rasterio.open(
    MASK_PATH
) as src:

    mask_crs = src.crs
    mask_transform = src.transform

    mask_width = src.width
    mask_height = src.height

    mask_data = src.read(
        1,
        masked=True,
    )


agricultural_mask = (

    ~np.ma.getmaskarray(
        mask_data
    )

    & (
        mask_data.filled(0)
        == 1
    )
)


agricultural_pixels = int(
    agricultural_mask.sum()
)


print(
    "\nFrozen mask:",
    MASK_PATH.name,
)

print(
    "Agricultural pixels:",
    agricultural_pixels,
)

print(
    "CRS:",
    mask_crs,
)

print(
    "Grid:",
    mask_width,
    "x",
    mask_height,
)


# ======================================================
# 2. GRID CHECK HELPER
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
            f"Grid dimensions differ:\n"
            f"{path}"
        )


    if src.crs != mask_crs:

        raise RuntimeError(
            f"CRS differs:\n"
            f"{path}"
        )


    if not src.transform.almost_equals(
        mask_transform
    ):

        raise RuntimeError(
            f"Transform differs:\n"
            f"{path}"
        )


# ======================================================
# 3. RESULT STORAGE
# ======================================================

window_rows = []

spatial_rows = []

window_data = {}


# ======================================================
# 4. PROCESS EACH AVAILABLE WINDOW
# ======================================================

for window_number, window_id in enumerate(
    AVAILABLE_WINDOWS
):

    metadata = WINDOWS[
        window_id
    ]


    print("\n" + "=" * 94)

    print(
        f"{window_id}: "
        f"{metadata['start']} → "
        f"{metadata['end']}"
    )

    print(
        "Status:",
        metadata["status"],
    )

    print("=" * 94)


    pp = pyeo_path(
        window_id
    )

    ip = index_path(
        window_id
    )


    if not pp.exists():

        raise FileNotFoundError(
            pp
        )


    if not ip.exists():

        raise FileNotFoundError(
            ip
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
    # Indices
    # --------------------------------------------------

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
    # Convert to arrays
    # --------------------------------------------------

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


    # --------------------------------------------------
    # Common analysis support
    #
    # Require:
    # - final agricultural mask
    # - all PyEOGPR bands valid
    # - NDVI + NDMI valid
    # --------------------------------------------------

    common = (
        agricultural_mask.copy()
    )


    for array in arrays.values():

        common &= np.isfinite(
            array
        )


    common_pixels = int(
        common.sum()
    )


    common_pct = (
        100.0
        * common_pixels
        / agricultural_pixels
    )


    if common_pixels == 0:

        raise RuntimeError(
            f"{window_id}: "
            "no common analysis pixels."
        )


    print(
        "Common agricultural pixels:",
        common_pixels,
    )

    print(
        f"Common agricultural coverage: "
        f"{common_pct:.2f}%"
    )


    # --------------------------------------------------
    # Seasonal statistics
    # --------------------------------------------------

    row = {

        "window_id":
            window_id,

        "start":
            metadata["start"],

        "end_exclusive":
            metadata["end"],

        "status":
            metadata["status"],

        "agricultural_pixels":
            agricultural_pixels,

        "common_pixels":
            common_pixels,

        "common_coverage_percent":
            common_pct,
    }


    for variable in [
        "Cw",
        "laiCw",
        "LAI",
        "NDVI",
        "NDMI",
    ]:

        stats = distribution(
            arrays[
                variable
            ][
                common
            ]
        )


        for statistic, value in stats.items():

            row[
                f"{variable}_{statistic}"
            ] = value


    # --------------------------------------------------
    # Absolute uncertainty statistics
    # --------------------------------------------------

    for variable in [
        "Cw_UNCERTAINTY",
        "laiCw_UNCERTAINTY",
        "LAI_UNCERTAINTY",
    ]:

        stats = distribution(
            arrays[
                variable
            ][
                common
            ]
        )


        for statistic, value in stats.items():

            row[
                f"{variable}_{statistic}"
            ] = value


    # --------------------------------------------------
    # Relative uncertainty medians
    #
    # Diagnostic only.
    # No hard RU mask applied.
    # --------------------------------------------------

    for trait in TRAITS:

        prediction = (
            arrays[
                trait
            ][
                common
            ]
        )


        uncertainty = (
            arrays[
                trait
                + "_UNCERTAINTY"
            ][
                common
            ]
        )


        positive = (
            prediction > 0
        )


        ru = (
            uncertainty[
                positive
            ]
            / prediction[
                positive
            ]
            * 100.0
        )


        ru = ru[
            np.isfinite(
                ru
            )
        ]


        if len(ru) > 0:

            row[
                f"{trait}_RU_p50"
            ] = float(
                np.median(
                    ru
                )
            )

        else:

            row[
                f"{trait}_RU_p50"
            ] = np.nan


    window_rows.append(
        row
    )


    # --------------------------------------------------
    # Save data for temporal analysis
    # --------------------------------------------------

    window_data[
        window_id
    ] = {

        "row":
            row,

        "arrays":
            arrays,

        "common_mask":
            common,
    }


    # --------------------------------------------------
    # Descriptive spatial correlation
    #
    # Fixed reproducible sample of up to 10,000 pixels.
    # No p-values because pixels are spatially
    # autocorrelated.
    # --------------------------------------------------

    flat_indices = np.flatnonzero(
        common
    )


    rng = np.random.default_rng(
        RANDOM_SEED
        + window_number
    )


    if (
        len(flat_indices)
        > MAX_SPATIAL_SAMPLE
    ):

        selected = rng.choice(
            flat_indices,
            size=MAX_SPATIAL_SAMPLE,
            replace=False,
        )

    else:

        selected = flat_indices


    for trait, index_name in CORRELATION_PAIRS:

        x = (
            arrays[
                trait
            ]
            .ravel()[
                selected
            ]
        )


        y = (
            arrays[
                index_name
            ]
            .ravel()[
                selected
            ]
        )


        spatial_rows.append({

            "window_id":
                window_id,

            "status":
                metadata["status"],

            "trait":
                trait,

            "index":
                index_name,

            "sample_n":
                len(selected),

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
        })


    print(
        "Medians:"
    )

    print(
        f"  Cw     = "
        f"{row['Cw_p50']:.6f} cm"
    )

    print(
        f"  laiCw  = "
        f"{row['laiCw_p50']:.2f} g/m²"
    )

    print(
        f"  LAI    = "
        f"{row['LAI_p50']:.3f}"
    )

    print(
        f"  NDVI   = "
        f"{row['NDVI_p50']:.4f}"
    )

    print(
        f"  NDMI   = "
        f"{row['NDMI_p50']:.4f}"
    )


# ======================================================
# 5. TEMPORAL RELATIONSHIPS
#
# GOOD windows only.
#
# W09 excluded from primary temporal correlation because
# it has ~53% spatial coverage and therefore does not
# represent equivalent spatial support.
# ======================================================

temporal_rows = []


for trait, index_name in CORRELATION_PAIRS:

    x = []

    y = []


    for window_id in GOOD_WINDOWS:

        row = (
            window_data[
                window_id
            ]["row"]
        )


        x.append(
            row[
                f"{trait}_p50"
            ]
        )


        y.append(
            row[
                f"{index_name}_p50"
            ]
        )


    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )


    temporal_rows.append({

        "trait":
            trait,

        "index":
            index_name,

        "windows_used":
            ",".join(
                GOOD_WINDOWS
            ),

        "n_windows":
            len(
                GOOD_WINDOWS
            ),

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
    })


# ======================================================
# 6. PRINT SEASONAL TRAJECTORY
# ======================================================

print("\n" + "=" * 94)
print("FINAL MASKED SEASONAL TRAJECTORY")
print("=" * 94)


for row in window_rows:

    print(

        f"{row['window_id']}"

        f" | {row['status']}"

        f" | coverage="
        f"{row['common_coverage_percent']:.2f}%"

        f" | Cw="
        f"{row['Cw_p50']:.6f}"

        f" | laiCw="
        f"{row['laiCw_p50']:.2f}"

        f" | LAI="
        f"{row['LAI_p50']:.3f}"

        f" | NDVI="
        f"{row['NDVI_p50']:.4f}"

        f" | NDMI="
        f"{row['NDMI_p50']:.4f}"
    )


# ======================================================
# 7. PRINT TEMPORAL CORRELATIONS
# ======================================================

print("\n" + "=" * 94)
print("GOOD-WINDOW TEMPORAL CORRELATIONS")
print("=" * 94)


for row in temporal_rows:

    print(

        f"{row['trait']} vs "
        f"{row['index']}"

        f" | n={row['n_windows']}"

        f" | Pearson="
        f"{row['pearson_r']:.4f}"

        f" | Spearman="
        f"{row['spearman_r']:.4f}"
    )


# ======================================================
# 8. PRINT SELECTED SPATIAL RELATIONSHIPS
# ======================================================

print("\n" + "=" * 94)
print("WINDOW-LEVEL SPATIAL CORRELATIONS")
print("=" * 94)


for row in spatial_rows:

    if (
        (row["trait"] == "laiCw"
         and row["index"] == "NDMI")

        or

        (row["trait"] == "LAI"
         and row["index"] == "NDVI")

        or

        (row["trait"] == "Cw"
         and row["index"] == "NDMI")
    ):

        print(

            f"{row['window_id']} "
            f"[{row['status']}] "

            f"{row['trait']} vs "
            f"{row['index']}"

            f" | n={row['sample_n']}"

            f" | Pearson="
            f"{row['pearson_r']:.4f}"

            f" | Spearman="
            f"{row['spearman_r']:.4f}"
        )


# ======================================================
# 9. SAVE WINDOW SUMMARY CSV
# ======================================================

window_csv = (
    OUTPUT_DIR
    / "seasonal_window_statistics.csv"
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


# ======================================================
# 10. SAVE SPATIAL CORRELATIONS
# ======================================================

spatial_csv = (
    OUTPUT_DIR
    / "spatial_correlations_by_window.csv"
)


with open(
    spatial_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            spatial_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        spatial_rows
    )


# ======================================================
# 11. SAVE TEMPORAL CORRELATIONS
# ======================================================

temporal_csv = (
    OUTPUT_DIR
    / "temporal_correlations_good_windows.csv"
)


with open(
    temporal_csv,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            temporal_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        temporal_rows
    )


# ======================================================
# 12. SAVE JSON SUMMARY
# ======================================================

json_path = (
    OUTPUT_DIR
    / "step17a_integrated_analysis.json"
)


json_output = {

    "primary_mask":
        "C25-N40",

    "agricultural_pixels":
        agricultural_pixels,

    "available_windows":
        AVAILABLE_WINDOWS,

    "good_windows_primary_temporal_analysis":
        GOOD_WINDOWS,

    "missing_window":
        "W03",

    "limited_window":
        "W09",

    "spatial_correlation_sample_max":
        MAX_SPATIAL_SAMPLE,

    "statistical_interpretation": {

        "spatial_correlations":
            (
                "Descriptive only; no p-values because "
                "pixels exhibit spatial autocorrelation."
            ),

        "temporal_correlations":
            (
                "Descriptive relationships across eight "
                "GOOD 15-day windows. W09 excluded because "
                "of reduced spatial coverage."
            ),
    },

    "window_statistics":
        window_rows,

    "temporal_correlations":
        temporal_rows,

    "spatial_correlations":
        spatial_rows,
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
# 13. FINISH
# ======================================================

print("\n" + "=" * 94)
print("STEP 17A OUTPUTS")
print("=" * 94)

print(
    "Window statistics:",
    window_csv,
)

print(
    "Spatial correlations:",
    spatial_csv,
)

print(
    "Temporal correlations:",
    temporal_csv,
)

print(
    "Full JSON:",
    json_path,
)


print("\n" + "=" * 94)
print("✅ STEP 17A COMPLETE")
print("=" * 94)