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
    / "spatial_final"
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
        "title": "W07 — high-canopy stage",
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
        facecolor="white",
    )

    plt.close(
        fig
    )

    print(
        "✅",
        output,
    )


# ======================================================
# LOAD AGRICULTURAL MASK
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


pixel_area_m2 = abs(
    reference_transform.a
    * reference_transform.e
)


agricultural_area_km2 = (

    agricultural_pixels
    * pixel_area_m2
    / 1_000_000
)


# ======================================================
# MAP EXTENT — UTM KM
# ======================================================

extent_km = [

    reference_bounds.left / 1000,
    reference_bounds.right / 1000,

    reference_bounds.bottom / 1000,
    reference_bounds.top / 1000,
]


print("=" * 94)
print("STEP 19C-v2 — FINAL SPATIAL FIGURE FORMATTING")
print("=" * 94)

print(
    "Agricultural pixels:",
    agricultural_pixels,
)

print(
    f"Agricultural area: "
    f"{agricultural_area_km2:.2f} km²"
)


# ======================================================
# READ ALL GOOD WINDOWS
# FOR CONSISTENT DISPLAY LIMITS
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
                f"Grid mismatch:\n{path}"
            )


        for variable, config in BANDS.items():

            array = (
                src.read(
                    config["band"],
                    masked=True,
                )
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


            global_values[
                variable
            ].append(
                array[
                    valid
                ]
            )


# ======================================================
# COMMON DISPLAY LIMITS
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
        [2, 98],
    )


    display_limits[
        variable
    ] = (
        float(lower),
        float(upper),
    )


    print(
        f"{variable}: "
        f"{lower:.6f} → "
        f"{upper:.6f}"
    )


# ======================================================
# LOAD REPRESENTATIVE WINDOWS
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
# AGRICULTURAL DOMAIN
# ======================================================

fig, ax = plt.subplots(
    figsize=(7.8, 7.4)
)


domain = np.ma.masked_where(
    ~agricultural,
    agricultural.astype(float),
)


domain_cmap = ListedColormap(
    ["forestgreen"]
)

domain_cmap.set_bad(
    "white"
)


ax.imshow(
    domain,
    extent=extent_km,
    origin="upper",
    cmap=domain_cmap,
    interpolation="nearest",
)


ax.set_title(
    "Threshold-defined agricultural mask — C25-N40",
    pad=12,
)

ax.set_xlabel(
    "UTM Easting (km)"
)

ax.set_ylabel(
    "UTM Northing (km)"
)

ax.set_aspect(
    "equal"
)

ax.grid(
    alpha=0.18,
)


# ------------------------------------------------------
# North arrow — unobtrusive
# ------------------------------------------------------

ax.annotate(

    "N",

    xy=(0.95, 0.94),
    xytext=(0.95, 0.84),

    xycoords="axes fraction",

    ha="center",
    va="center",

    fontsize=13,
    fontweight="bold",

    arrowprops={
        "arrowstyle": "-|>",
        "linewidth": 1.4,
    },
)


# ------------------------------------------------------
# Put metadata BELOW map, not over data
# ------------------------------------------------------

fig.text(

    0.5,
    0.025,

    (
        f"Agricultural pixels = "
        f"{agricultural_pixels:,}   |   "
        f"Area = "
        f"{agricultural_area_km2:.2f} km²   |   "
        f"Grid resolution = 20 m"
    ),

    ha="center",
    fontsize=9.5,
)


fig.subplots_adjust(
    bottom=0.11,
)


save_figure(
    fig,
    "Figure_07_agricultural_domain_final.png",
)


# ======================================================
# SPATIAL MATRIX FUNCTION
#
# IMPORTANT:
# 3 MAP COLUMNS + 1 DEDICATED COLORBAR COLUMN
# ======================================================

def create_spatial_matrix(
    variables,
    title,
    filename,
):

    fig = plt.figure(
        figsize=(13.2, 10.2)
    )


    gs = fig.add_gridspec(

        nrows=3,
        ncols=4,

        width_ratios=[
            1,
            1,
            1,
            0.055,
        ],

        left=0.075,
        right=0.955,

        bottom=0.085,
        top=0.91,

        wspace=0.10,
        hspace=0.12,
    )


    map_axes = []


    for row_index, variable in enumerate(
        variables
    ):

        row_axes = []


        vmin, vmax = (
            display_limits[
                variable
            ]
        )


        image_for_colorbar = None


        for column_index, (
            window_id,
            window_config,
        ) in enumerate(
            DISPLAY_WINDOWS.items()
        ):

            ax = fig.add_subplot(
                gs[
                    row_index,
                    column_index
                ]
            )


            array = (
                representative[
                    window_id
                ][
                    variable
                ]
            )


            masked_array = np.ma.masked_invalid(
                array
            )


            cmap = plt.get_cmap(
                "viridis"
            ).copy()

            cmap.set_bad(
                "white"
            )


            image = ax.imshow(

                masked_array,

                extent=extent_km,
                origin="upper",

                cmap=cmap,

                vmin=vmin,
                vmax=vmax,

                interpolation="nearest",
            )


            image_for_colorbar = image


            # ------------------------------------------
            # Column titles
            # ------------------------------------------

            if row_index == 0:

                ax.set_title(
                    window_config[
                        "title"
                    ],
                    fontsize=11,
                    pad=8,
                )


            # ------------------------------------------
            # Y axis only in first column
            # ------------------------------------------

            if column_index == 0:

                label = (
                    BANDS[
                        variable
                    ][
                        "label"
                    ]
                )


                ax.set_ylabel(
                    f"{label}\n"
                    "UTM Northing (km)",
                    fontsize=9.5,
                )

            else:

                ax.tick_params(
                    labelleft=False
                )


            # ------------------------------------------
            # X axis only bottom row
            # ------------------------------------------

            if row_index == (
                len(variables) - 1
            ):

                ax.set_xlabel(
                    "UTM Easting (km)",
                    fontsize=9.5,
                )

            else:

                ax.tick_params(
                    labelbottom=False
                )


            ax.tick_params(
                labelsize=8.5
            )


            ax.set_aspect(
                "equal"
            )


            row_axes.append(
                ax
            )


        map_axes.append(
            row_axes
        )


        # ==================================================
        # DEDICATED COLORBAR AXIS
        # ==================================================

        cax = fig.add_subplot(
            gs[
                row_index,
                3
            ]
        )


        cbar = fig.colorbar(
            image_for_colorbar,
            cax=cax,
        )


        cbar.set_label(

            BANDS[
                variable
            ][
                "unit"
            ],

            fontsize=9.5,
            labelpad=8,
        )


        cbar.ax.tick_params(
            labelsize=8.5
        )


    fig.suptitle(
        title,
        fontsize=15,
        y=0.965,
    )


    fig.text(

        0.5,
        0.025,

        (
            "Color limits are fixed for each variable using "
            "the 2nd–98th percentiles across all eight GOOD windows. "
            "White pixels are outside the mask or lack valid retrievals."
        ),

        ha="center",
        fontsize=9,
    )


    save_figure(
        fig,
        filename,
    )


# ======================================================
# FIGURE 08 — TRAITS
# ======================================================

create_spatial_matrix(

    variables=TRAITS,

    title=(
        "Spatial evolution of PyEOGPR vegetation traits"
    ),

    filename=(
        "Figure_08_trait_maps_final.png"
    ),
)


# ======================================================
# FIGURE 09 — UNCERTAINTIES
# ======================================================

create_spatial_matrix(

    variables=UNCERTAINTIES,

    title=(
        "Spatial evolution of native PyEOGPR retrieval uncertainty"
    ),

    filename=(
        "Figure_09_uncertainty_maps_final.png"
    ),
)


print("\n" + "=" * 94)
print("✅ STEP 19C-v2 COMPLETE")
print("=" * 94)

print(
    "Final spatial figures:"
)

print(
    OUTPUT_DIR
)