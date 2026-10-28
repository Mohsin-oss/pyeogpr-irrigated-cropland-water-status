from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap


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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "figures"
    / "spatial"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# WINDOWS
# ======================================================

GOOD_WINDOWS = {

    "W01": ("20251115", "20251130"),
    "W02": ("20251130", "20251215"),
    "W04": ("20251230", "20260114"),
    "W05": ("20260114", "20260129"),
    "W06": ("20260129", "20260213"),
    "W07": ("20260213", "20260228"),
    "W08": ("20260228", "20260315"),
    "W10": ("20260330", "20260414"),
}


DISPLAY_WINDOWS = {

    "W02": {
        "start": "20251130",
        "end": "20251215",
        "title": "W02 — early season",
    },

    "W07": {
        "start": "20260213",
        "end": "20260228",
        "title": "W07 — peak vegetation",
    },

    "W10": {
        "start": "20260330",
        "end": "20260414",
        "title": "W10 — late season",
    },
}


# ======================================================
# BANDS
# ======================================================

BANDS = {

    "Cw": {
        "band": 1,
        "label": "Cw",
        "unit": "cm",
    },

    "Cw_UNCERTAINTY": {
        "band": 2,
        "label": "Cw uncertainty",
        "unit": "cm",
    },

    "laiCw": {
        "band": 3,
        "label": "laiCw",
        "unit": "g m$^{-2}$",
    },

    "laiCw_UNCERTAINTY": {
        "band": 4,
        "label": "laiCw uncertainty",
        "unit": "g m$^{-2}$",
    },

    "LAI": {
        "band": 5,
        "label": "LAI",
        "unit": "m$^2$ m$^{-2}$",
    },

    "LAI_UNCERTAINTY": {
        "band": 6,
        "label": "LAI uncertainty",
        "unit": "m$^2$ m$^{-2}$",
    },
}


TRAITS = [
    "Cw",
    "laiCw",
    "LAI",
]


UNCERTAINTIES = [
    "Cw_UNCERTAINTY",
    "laiCw_UNCERTAINTY",
    "LAI_UNCERTAINTY",
]


# ======================================================
# HELPERS
# ======================================================

def pyeo_path(
    window_id,
    start,
    end,
):

    return (
        PYEO_DIR
        / (
            f"pyeogpr_{window_id}_"
            f"{start}_{end}_final.tif"
        )
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


# ======================================================
# 1. LOAD FINAL AGRICULTURAL MASK
# ======================================================

with rasterio.open(
    MASK_PATH
) as src:

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


    reference_crs = src.crs
    reference_transform = src.transform
    reference_bounds = src.bounds

    width = src.width
    height = src.height


agricultural_pixels = int(
    agricultural.sum()
)


pixel_area = abs(
    reference_transform.a
    * reference_transform.e
)


agricultural_area_km2 = (

    agricultural_pixels
    * pixel_area
    / 1_000_000
)


print("=" * 94)
print("STEP 19C — SPATIAL FIGURES")
print("=" * 94)

print(
    "\nAgricultural pixels:",
    agricultural_pixels,
)

print(
    f"Agricultural area: "
    f"{agricultural_area_km2:.2f} km²"
)


# ======================================================
# MAP EXTENT IN UTM KILOMETRES
# ======================================================

extent_km = [

    reference_bounds.left / 1000,
    reference_bounds.right / 1000,

    reference_bounds.bottom / 1000,
    reference_bounds.top / 1000,
]


# ======================================================
# 2. READ ALL GOOD WINDOWS TO DEFINE COMMON COLOR SCALES
# ======================================================

global_values = {

    variable: []

    for variable in BANDS
}


for window_id, (
    start,
    end,
) in GOOD_WINDOWS.items():

    path = pyeo_path(
        window_id,
        start,
        end,
    )


    with rasterio.open(
        path
    ) as src:

        if (
            src.crs != reference_crs

            or src.width != width

            or src.height != height

            or not src.transform.almost_equals(
                reference_transform
            )
        ):

            raise RuntimeError(
                f"Grid mismatch: "
                f"{path}"
            )


        for variable, config in BANDS.items():

            band = (
                src.read(
                    config[
                        "band"
                    ],
                    masked=True,
                )
                .filled(
                    np.nan
                )
            )


            valid = (

                agricultural

                & np.isfinite(
                    band
                )
            )


            values = band[
                valid
            ]


            global_values[
                variable
            ].append(
                values
            )


# ======================================================
# 3. ROBUST GLOBAL DISPLAY LIMITS
# ======================================================

display_limits = {}


for variable in BANDS:

    values = np.concatenate(
        global_values[
            variable
        ]
    )


    lower, upper = np.percentile(
        values,
        [
            2,
            98,
        ],
    )


    display_limits[
        variable
    ] = (
        float(lower),
        float(upper),
    )


    print(
        f"{variable}: "
        f"display range "
        f"{lower:.5f} → "
        f"{upper:.5f}"
    )


# ======================================================
# 4. LOAD REPRESENTATIVE WINDOWS
# ======================================================

representative = {}


for window_id, config in DISPLAY_WINDOWS.items():

    path = pyeo_path(
        window_id,
        config["start"],
        config["end"],
    )


    with rasterio.open(
        path
    ) as src:

        data = src.read(
            masked=True
        )


    representative[
        window_id
    ] = {}


    for variable, band_config in BANDS.items():

        array = (
            data[
                band_config[
                    "band"
                ] - 1
            ]
            .filled(
                np.nan
            )
        )


        valid = (

            agricultural

            & np.isfinite(
                array
            )
        )


        mapped = np.full(
            array.shape,
            np.nan,
            dtype=float,
        )


        mapped[
            valid
        ] = array[
            valid
        ]


        representative[
            window_id
        ][
            variable
        ] = mapped


# ======================================================
# FIGURE 07
# FINAL AGRICULTURAL DOMAIN
# ======================================================

fig, ax = plt.subplots(
    figsize=(7.5, 7)
)


domain = np.where(
    agricultural,
    1.0,
    np.nan,
)


cmap = ListedColormap(
    [
        "forestgreen"
    ]
)


ax.imshow(
    domain,
    extent=extent_km,
    origin="upper",
    cmap=cmap,
    interpolation="nearest",
)


ax.set_xlabel(
    "UTM Easting (km)"
)

ax.set_ylabel(
    "UTM Northing (km)"
)

ax.set_title(
    "Frozen agricultural analysis domain — C25-N40"
)


ax.text(
    0.02,
    0.02,
    (
        f"Agricultural pixels: "
        f"{agricultural_pixels:,}\n"
        f"Area: "
        f"{agricultural_area_km2:.2f} km²"
    ),
    transform=ax.transAxes,
    verticalalignment="bottom",
    bbox={
        "facecolor": "white",
        "alpha": 0.85,
        "edgecolor": "none",
    },
)


ax.set_aspect(
    "equal"
)

ax.grid(
    alpha=0.20
)


fig.tight_layout()


save_figure(
    fig,
    "Figure_07_agricultural_domain.png",
)


# ======================================================
# FUNCTION FOR 3 × 3 SPATIAL FIGURES
# ======================================================

def create_spatial_matrix(
    variables,
    title,
    filename,
):

    fig, axes = plt.subplots(
        len(variables),
        len(DISPLAY_WINDOWS),
        figsize=(12, 10),
        sharex=True,
        sharey=True,
    )


    last_images = {}


    for row_index, variable in enumerate(
        variables
    ):

        vmin, vmax = (
            display_limits[
                variable
            ]
        )


        for column_index, (
            window_id,
            window_config,
        ) in enumerate(
            DISPLAY_WINDOWS.items()
        ):

            ax = axes[
                row_index,
                column_index
            ]


            image = ax.imshow(

                representative[
                    window_id
                ][
                    variable
                ],

                extent=extent_km,
                origin="upper",

                vmin=vmin,
                vmax=vmax,

                interpolation="nearest",
            )


            last_images[
                variable
            ] = image


            if row_index == 0:

                ax.set_title(
                    window_config[
                        "title"
                    ]
                )


            if column_index == 0:

                label = (
                    BANDS[
                        variable
                    ][
                        "label"
                    ]
                )

                unit = (
                    BANDS[
                        variable
                    ][
                        "unit"
                    ]
                )


                ax.set_ylabel(
                    f"{label}\n"
                    f"Northing (km)"
                )


            if row_index == (
                len(variables) - 1
            ):

                ax.set_xlabel(
                    "Easting (km)"
                )


            ax.set_aspect(
                "equal"
            )


    # --------------------------------------------------
    # ONE COLORBAR PER VARIABLE / ROW
    # --------------------------------------------------

    for row_index, variable in enumerate(
        variables
    ):

        unit = (
            BANDS[
                variable
            ][
                "unit"
            ]
        )


        cbar = fig.colorbar(

            last_images[
                variable
            ],

            ax=axes[
                row_index,
                :
            ].tolist(),

            fraction=0.025,
            pad=0.02,
        )


        cbar.set_label(
            unit
        )


    fig.suptitle(
        title,
        fontsize=15,
    )


    fig.text(

        0.5,
        0.01,

        (
            "All dates use identical per-variable color scales "
            "derived from the 2nd–98th percentiles across all "
            "eight GOOD windows. Only the frozen agricultural "
            "analysis domain is displayed."
        ),

        ha="center",
        fontsize=9,
    )


    fig.subplots_adjust(
        left=0.08,
        right=0.90,
        bottom=0.07,
        top=0.92,
        wspace=0.08,
        hspace=0.10,
    )


    save_figure(
        fig,
        filename,
    )


# ======================================================
# FIGURE 08
# TRAIT MAPS
# ======================================================

create_spatial_matrix(

    variables=TRAITS,

    title=(
        "Spatial evolution of "
        "PyEOGPR vegetation traits"
    ),

    filename=(
        "Figure_08_trait_maps_"
        "early_peak_late.png"
    ),
)


# ======================================================
# FIGURE 09
# UNCERTAINTY MAPS
# ======================================================

create_spatial_matrix(

    variables=UNCERTAINTIES,

    title=(
        "Spatial evolution of "
        "native PyEOGPR retrieval uncertainty"
    ),

    filename=(
        "Figure_09_uncertainty_maps_"
        "early_peak_late.png"
    ),
)


print("\n" + "=" * 94)
print("✅ STEP 19C COMPLETE")
print("=" * 94)

print(
    "\nSpatial figures:"
)

print(
    OUTPUT_DIR
)