# Install dependencies in the environment, not in this Python script:
# pip install numpy matplotlib
from pathlib import Path
import csv

import numpy as np
import matplotlib.pyplot as plt


# ======================================================
# PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEASON_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17a"
    / "seasonal_window_statistics.csv"
)

TEMPORAL_CORR_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17a"
    / "temporal_correlations_good_windows.csv"
)

RU_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step17b"
    / "ru_good_window_summary.csv"
)

HYDRO_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "analysis"
    / "step18b"
    / "integrated_EO_hydroclimate.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "figures"
    / "core"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# WINDOW AXIS
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

X = np.arange(
    len(WINDOW_ORDER)
)


# ======================================================
# HELPERS
# ======================================================

def read_csv(path):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def seasonal_array(
    records,
    field,
):

    lookup = {
        row["window_id"]:
            float(row[field])
        for row in records
    }

    return np.asarray(
        [
            lookup.get(
                window_id,
                np.nan,
            )
            for window_id
            in WINDOW_ORDER
        ],
        dtype=float,
    )


def save_figure(
    fig,
    filename,
):

    path = (
        OUTPUT_DIR
        / filename
    )

    fig.savefig(
        path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    print(
        "✅",
        path,
    )


# ======================================================
# LOAD DATA
# ======================================================

season = read_csv(
    SEASON_CSV
)

hydro = read_csv(
    HYDRO_CSV
)

ru = read_csv(
    RU_CSV
)


# ======================================================
# FIGURE 1
# SEASONAL PyEOGPR TRAJECTORIES
# ======================================================

traits = [

    (
        "Cw",
        "Cw",
        "cm",
    ),

    (
        "laiCw",
        "laiCw",
        "g m$^{-2}$",
    ),

    (
        "LAI",
        "LAI",
        "m$^2$ m$^{-2}$",
    ),
]


fig, axes = plt.subplots(
    3,
    1,
    figsize=(9, 9),
    sharex=True,
)


for ax, (
    variable,
    label,
    unit,
) in zip(
    axes,
    traits,
):

    p25 = seasonal_array(
        season,
        f"{variable}_p25",
    )

    p50 = seasonal_array(
        season,
        f"{variable}_p50",
    )

    p75 = seasonal_array(
        season,
        f"{variable}_p75",
    )


    ax.plot(
        X,
        p50,
        marker="o",
        linewidth=1.8,
    )


    ax.fill_between(
        X,
        p25,
        p75,
        alpha=0.20,
    )


    # Highlight W09 as LIMITED
    w09_index = (
        WINDOW_ORDER.index(
            "W09"
        )
    )


    ax.scatter(
        [w09_index],
        [p50[w09_index]],
        marker="D",
        s=70,
        facecolors="none",
        edgecolors="black",
        linewidths=1.3,
        zorder=5,
    )


    ax.set_ylabel(
        f"{label}\n({unit})"
    )

    ax.grid(
        alpha=0.25
    )


axes[-1].set_xticks(
    X
)

axes[-1].set_xticklabels(
    WINDOW_ORDER
)

axes[-1].set_xlabel(
    "15-day seasonal window"
)


fig.suptitle(
    "Seasonal PyEOGPR vegetation-trait retrievals"
)


fig.text(
    0.5,
    0.01,
    (
        "Line = median; shaded interval = IQR. "
        "W03 = missing observation; open diamond = W09 limited coverage."
    ),
    ha="center",
    fontsize=9,
)


fig.tight_layout(
    rect=[
        0,
        0.04,
        1,
        0.96,
    ]
)


save_figure(
    fig,
    "Figure_01_PyEOGPR_seasonal_traits.png",
)


# ======================================================
# FIGURE 2
# NDVI + NDMI SEASONAL TRAJECTORIES
# ======================================================

fig, axes = plt.subplots(
    2,
    1,
    figsize=(9, 6.5),
    sharex=True,
)


for ax, variable in zip(
    axes,
    [
        "NDVI",
        "NDMI",
    ],
):

    p25 = seasonal_array(
        season,
        f"{variable}_p25",
    )

    p50 = seasonal_array(
        season,
        f"{variable}_p50",
    )

    p75 = seasonal_array(
        season,
        f"{variable}_p75",
    )


    ax.plot(
        X,
        p50,
        marker="o",
        linewidth=1.8,
    )


    ax.fill_between(
        X,
        p25,
        p75,
        alpha=0.20,
    )


    w09_index = (
        WINDOW_ORDER.index(
            "W09"
        )
    )


    ax.scatter(
        [w09_index],
        [p50[w09_index]],
        marker="D",
        s=70,
        facecolors="none",
        edgecolors="black",
        linewidths=1.3,
        zorder=5,
    )


    ax.set_ylabel(
        variable
    )

    ax.grid(
        alpha=0.25
    )


axes[-1].set_xticks(
    X
)

axes[-1].set_xticklabels(
    WINDOW_ORDER
)

axes[-1].set_xlabel(
    "15-day seasonal window"
)


fig.suptitle(
    "Seasonal Sentinel-2 vegetation indices"
)


fig.tight_layout(
    rect=[
        0,
        0,
        1,
        0.95,
    ]
)


save_figure(
    fig,
    "Figure_02_NDVI_NDMI_seasonal.png",
)


# ======================================================
# FIGURE 3
# HYDROCLIMATE CONTEXT
# ======================================================

hydro_lookup = {
    row["window_id"]:
        row
    for row in hydro
}


def hydro_array(field):

    return np.asarray(

        [
            float(
                hydro_lookup[
                    window_id
                ][
                    field
                ]
            )

            if window_id
            in hydro_lookup

            else np.nan

            for window_id
            in WINDOW_ORDER
        ],

        dtype=float,
    )


P15 = hydro_array(
    "P15"
)

Pprior = hydro_array(
    "Pprior30"
)

SM = hydro_array(
    "SM0_28"
)

T = hydro_array(
    "T2m"
)


fig, axes = plt.subplots(
    3,
    1,
    figsize=(9, 8),
    sharex=True,
)


axes[0].bar(
    X - 0.18,
    P15,
    width=0.36,
    label="Window rainfall",
)

axes[0].bar(
    X + 0.18,
    Pprior,
    width=0.36,
    label="Prior 30-day rainfall",
)

axes[0].set_ylabel(
    "Rainfall\n(mm)"
)

axes[0].legend(
    frameon=False
)


axes[1].plot(
    X,
    SM,
    marker="o",
)

axes[1].set_ylabel(
    "SM 0–28 cm\n(m³ m⁻³)"
)


axes[2].plot(
    X,
    T,
    marker="o",
)

axes[2].set_ylabel(
    "T2m\n(°C)"
)


for ax in axes:

    ax.grid(
        alpha=0.25
    )


axes[-1].set_xticks(
    X
)

axes[-1].set_xticklabels(
    WINDOW_ORDER
)

axes[-1].set_xlabel(
    "15-day seasonal window"
)


fig.suptitle(
    "Hydroclimatic context across the study season"
)


fig.tight_layout(
    rect=[
        0,
        0,
        1,
        0.95,
    ]
)


save_figure(
    fig,
    "Figure_03_hydroclimate_context.png",
)


# ======================================================
# FIGURE 4
# RU RETENTION
# ======================================================

fig, ax = plt.subplots(
    figsize=(8, 5.5)
)


for trait in [
    "Cw",
    "laiCw",
    "LAI",
]:

    selected = [

        row
        for row in ru

        if row[
            "trait"
        ] == trait
    ]


    selected = sorted(
        selected,
        key=lambda row:
        float(
            row[
                "RU_threshold_percent"
            ]
        ),
    )


    thresholds = np.asarray(
        [
            float(
                row[
                    "RU_threshold_percent"
                ]
            )
            for row in selected
        ]
    )


    retention = np.asarray(
        [
            float(
                row[
                    "median_agricultural_domain_retention_percent"
                ]
            )
            for row in selected
        ]
    )


    ax.plot(
        thresholds,
        retention,
        marker="o",
        label=trait,
    )


ax.set_xlabel(
    "Relative-uncertainty threshold (%)"
)

ax.set_ylabel(
    "Median agricultural domain retained (%)"
)

ax.set_xticks(
    [
        20,
        30,
        40,
    ]
)

ax.legend(
    frameon=False
)

ax.grid(
    alpha=0.25
)

ax.set_title(
    "Effect of hard relative-uncertainty filtering"
)


fig.tight_layout()


save_figure(
    fig,
    "Figure_04_RU_retention_sensitivity.png",
)


# ======================================================
# FIGURE 5
# STANDARDIZED EO TRAJECTORIES
# ======================================================

fig, ax = plt.subplots(
    figsize=(9, 5.5)
)


for variable in [
    "Cw",
    "laiCw",
    "LAI",
    "NDVI",
    "NDMI",
]:

    values = seasonal_array(
        season,
        f"{variable}_p50",
    )


    finite = np.isfinite(
        values
    )


    standardized = np.full(
        values.shape,
        np.nan,
    )


    valid_values = (
        values[
            finite
        ]
    )


    standardized[
        finite
    ] = (

        valid_values
        - np.mean(
            valid_values
        )

    ) / np.std(
        valid_values
    )


    ax.plot(
        X,
        standardized,
        marker="o",
        label=variable,
    )


ax.axhline(
    0,
    linewidth=0.8,
)

ax.set_xticks(
    X
)

ax.set_xticklabels(
    WINDOW_ORDER
)

ax.set_xlabel(
    "15-day seasonal window"
)

ax.set_ylabel(
    "Standardized seasonal value (z-score)"
)

ax.legend(
    ncol=3,
    frameon=False,
)

ax.grid(
    alpha=0.25
)

ax.set_title(
    "Relative seasonal trajectories of PyEOGPR traits and vegetation indices"
)


fig.tight_layout()


save_figure(
    fig,
    "Figure_05_standardized_EO_trajectories.png",
)


print("\n" + "=" * 90)
print("✅ STEP 19A COMPLETE")
print("=" * 90)

print(
    "Figures written to:"
)

print(
    OUTPUT_DIR
)