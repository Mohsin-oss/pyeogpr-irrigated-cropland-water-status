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
    / "hydroclimate"
    / "hydroclimate_15day_windows.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "figures"
    / "final_core"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# WINDOWS
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


X = np.arange(
    len(WINDOW_ORDER)
)


W09_INDEX = WINDOW_ORDER.index(
    "W09"
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
                window,
                np.nan,
            )
            for window in WINDOW_ORDER
        ],
        dtype=float,
    )


def save_figure(
    fig,
    filename,
):

    output = (
        OUTPUT_DIR
        / filename
    )

    fig.savefig(
        output,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    print(
        "✅",
        output,
    )


def mark_limited(
    ax,
    value,
):

    if np.isfinite(
        value
    ):

        ax.scatter(
            [W09_INDEX],
            [value],
            marker="D",
            s=72,
            facecolors="none",
            edgecolors="black",
            linewidths=1.4,
            zorder=10,
        )


# ======================================================
# DATA
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
# PYEO GPR TRAITS
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


    mark_limited(
        ax,
        p50[
            W09_INDEX
        ],
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
        "Line = agricultural-domain median; "
        "shading = spatial interquartile range. "
        "W03 = missing; open diamond = W09 limited coverage."
    ),
    ha="center",
    fontsize=9,
)


fig.tight_layout(
    rect=[
        0,
        0.045,
        1,
        0.96,
    ]
)


save_figure(
    fig,
    "Figure_01_PyEOGPR_traits_final.png",
)


# ======================================================
# FIGURE 2
# VEGETATION INDICES
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


    mark_limited(
        ax,
        p50[
            W09_INDEX
        ],
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


fig.text(
    0.5,
    0.01,
    (
        "Line = agricultural-domain median; "
        "shading = spatial interquartile range. "
        "W03 = missing; open diamond = W09 limited coverage."
    ),
    ha="center",
    fontsize=9,
)


fig.tight_layout(
    rect=[
        0,
        0.05,
        1,
        0.95,
    ]
)


save_figure(
    fig,
    "Figure_02_indices_final.png",
)


# ======================================================
# FIGURE 3
# HYDROCLIMATE — CORRECTED TO INCLUDE W03
# ======================================================

hydro_lookup = {
    row["window_id"]:
        row
    for row in hydro
}


def hydro_array(
    field,
):

    return np.asarray(
        [
            float(
                hydro_lookup[
                    window
                ][
                    field
                ]
            )
            for window in WINDOW_ORDER
        ],
        dtype=float,
    )


P15 = hydro_array(
    "rainfall_window_mm"
)

Pprior = hydro_array(
    "rainfall_prior30_mm"
)

SM = hydro_array(
    "soil_water_0_28cm_proxy_m3m3"
)

T = hydro_array(
    "temperature_2m_C"
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
    label="15-day rainfall",
)

axes[0].bar(
    X + 0.18,
    Pprior,
    width=0.36,
    label="Antecedent 30-day rainfall",
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
    "Upper-soil-water proxy\n(m$^3$ m$^{-3}$)"
)


axes[2].plot(
    X,
    T,
    marker="o",
)

axes[2].set_ylabel(
    "2-m temperature\n(°C)"
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


fig.text(
    0.5,
    0.01,
    (
        "Hydroclimate is shown as environmental context, "
        "not as field-level irrigation observations or retrieval validation."
    ),
    ha="center",
    fontsize=9,
)


fig.tight_layout(
    rect=[
        0,
        0.04,
        1,
        0.95,
    ]
)


save_figure(
    fig,
    "Figure_03_hydroclimate_final.png",
)


# ======================================================
# FIGURE 4
# RU SELECTION EFFECT
# ======================================================

fig, axes = plt.subplots(
    2,
    1,
    figsize=(8.5, 8),
    sharex=True,
)


for trait in [
    "Cw",
    "laiCw",
    "LAI",
]:

    selected = sorted(

        [
            row
            for row in ru
            if row["trait"] == trait
        ],

        key=lambda row:
            float(
                row[
                    "RU_threshold_percent"
                ]
            ),
    )


    threshold = np.asarray(
        [
            float(
                row[
                    "RU_threshold_percent"
                ]
            )
            for row in selected
        ]
    )


    domain_retention = np.asarray(
        [
            float(
                row[
                    "median_agricultural_domain_retention_percent"
                ]
            )
            for row in selected
        ]
    )


    median_shift = np.asarray(
        [
            float(
                row[
                    "median_absolute_median_shift_percent"
                ]
            )
            for row in selected
        ]
    )


    axes[0].plot(
        threshold,
        domain_retention,
        marker="o",
        label=trait,
    )


    axes[1].plot(
        threshold,
        median_shift,
        marker="o",
        label=trait,
    )


axes[0].set_ylabel(
    "Median agricultural\ndomain retained (%)"
)

axes[0].legend(
    frameon=False
)

axes[0].grid(
    alpha=0.25
)


axes[1].set_ylabel(
    "Median absolute shift in\ntrait median (%)"
)

axes[1].set_xlabel(
    "Relative-uncertainty threshold (%)"
)

axes[1].set_xticks(
    [
        20,
        30,
        40,
    ]
)

axes[1].grid(
    alpha=0.25
)


fig.suptitle(
    "Selection effects of hard relative-uncertainty filtering"
)


fig.text(
    0.5,
    0.01,
    (
        "Statistics summarize the eight GOOD windows. "
        "RU thresholds are sensitivity treatments, not validity criteria."
    ),
    ha="center",
    fontsize=9,
)


fig.tight_layout(
    rect=[
        0,
        0.045,
        1,
        0.95,
    ]
)


save_figure(
    fig,
    "Figure_04_RU_selection_effect_final.png",
)


# ======================================================
# FIGURE 5
# STANDARDIZED EO TRAJECTORIES
#
# Z-score parameters use GOOD windows ONLY.
# W09 is transformed using those GOOD-window parameters
# but does not influence mean or SD.
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


    good_indices = np.asarray(
        [
            WINDOW_ORDER.index(
                window
            )
            for window in GOOD_WINDOWS
        ]
    )


    good_values = values[
        good_indices
    ]


    mean_good = np.mean(
        good_values
    )

    std_good = np.std(
        good_values
    )


    standardized = (
        values
        - mean_good
    ) / std_good


    ax.plot(
        X,
        standardized,
        marker="o",
        label=variable,
    )


    mark_limited(
        ax,
        standardized[
            W09_INDEX
        ],
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


fig.text(
    0.5,
    0.01,
    (
        "Standardization parameters calculated from the eight GOOD windows only. "
        "W03 = missing; open diamonds identify W09 limited coverage."
    ),
    ha="center",
    fontsize=9,
)


fig.tight_layout(
    rect=[
        0,
        0.05,
        1,
        1,
    ]
)


save_figure(
    fig,
    "Figure_05_standardized_EO_final.png",
)


# ======================================================
# FIGURE 6
# NATIVE PYEO GPR ABSOLUTE UNCERTAINTY
# ======================================================

uncertainty_variables = [

    (
        "Cw_UNCERTAINTY",
        "Cw uncertainty",
        "cm",
    ),

    (
        "laiCw_UNCERTAINTY",
        "laiCw uncertainty",
        "g m$^{-2}$",
    ),

    (
        "LAI_UNCERTAINTY",
        "LAI uncertainty",
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
    uncertainty_variables,
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


    mark_limited(
        ax,
        p50[
            W09_INDEX
        ],
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
    "Native PyEOGPR retrieval uncertainty across the season"
)


fig.text(
    0.5,
    0.01,
    (
        "Lines show median native absolute GPR uncertainty; "
        "shading shows its spatial IQR. "
        "These are not confidence intervals for the seasonal median."
    ),
    ha="center",
    fontsize=9,
)


fig.tight_layout(
    rect=[
        0,
        0.05,
        1,
        0.96,
    ]
)


save_figure(
    fig,
    "Figure_06_PyEOGPR_uncertainty_final.png",
)


print("\n" + "=" * 92)
print("✅ STEP 19B COMPLETE")
print("=" * 92)

print(
    "Refined figures:"
)

print(
    OUTPUT_DIR
)