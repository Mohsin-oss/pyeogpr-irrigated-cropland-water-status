from pathlib import Path
import sys

import ee
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio

from matplotlib.patches import Rectangle
from shapely.geometry import Point


# ======================================================
# PROJECT
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.project_config import GEE_PROJECT_ID
from config.study_config import STUDY_BBOX


MASK_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_C25_N40_final.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "figures"
    / "locator"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "Figure_10_study_area_locator.png"
)


# ======================================================
# AOI
# ======================================================

WEST, SOUTH, EAST, NORTH = STUDY_BBOX

AOI_CENTER_LON = (
    WEST + EAST
) / 2.0

AOI_CENTER_LAT = (
    SOUTH + NORTH
) / 2.0


print("=" * 92)
print("STEP 19D-v2 — STUDY-AREA LOCATOR MAP")
print("=" * 92)


# ======================================================
# 1. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(
    project=GEE_PROJECT_ID
)

print(
    "\n✅ Earth Engine initialized."
)


# ======================================================
# 2. GAUL 2025 SIMPLIFIED DATA
#
# No GAUL 2025 level0 asset is used.
#
# Pakistan national boundary will be constructed by
# dissolving Pakistan's level-1 administrative units.
# ======================================================

LEVEL1_ID = (
    "FAO/GAUL_SIMPLIFIED_500m/2025/level1"
)

LEVEL2_ID = (
    "FAO/GAUL_SIMPLIFIED_500m/2025/level2"
)


level1_fc = (
    ee.FeatureCollection(
        LEVEL1_ID
    )
    .filter(
        ee.Filter.eq(
            "GAUL0_NAME",
            "Pakistan",
        )
    )
)


level2_fc = (
    ee.FeatureCollection(
        LEVEL2_ID
    )
    .filter(
        ee.Filter.eq(
            "GAUL0_NAME",
            "Pakistan",
        )
    )
)


level1_count = int(
    level1_fc
    .size()
    .getInfo()
)

level2_count = int(
    level2_fc
    .size()
    .getInfo()
)


print(
    "Pakistan level-1 units:",
    level1_count,
)

print(
    "Pakistan level-2 units:",
    level2_count,
)


if level1_count == 0:

    raise RuntimeError(
        "No Pakistan level-1 GAUL features found."
    )


if level2_count == 0:

    raise RuntimeError(
        "No Pakistan level-2 GAUL features found."
    )


# ======================================================
# 3. EARTH ENGINE → GEOPANDAS
# ======================================================

def ee_fc_to_gdf(
    feature_collection
):

    info = (
        feature_collection
        .getInfo()
    )


    features = info.get(
        "features",
        []
    )


    if len(features) == 0:

        raise RuntimeError(
            "FeatureCollection returned no features."
        )


    return (
        gpd.GeoDataFrame
        .from_features(
            features,
            crs="EPSG:4326",
        )
    )


print(
    "\nDownloading Pakistan administrative boundaries..."
)


level1 = ee_fc_to_gdf(
    level1_fc
)

level2 = ee_fc_to_gdf(
    level2_fc
)


print(
    "✅ Administrative boundaries downloaded."
)


# ======================================================
# 4. BUILD PAKISTAN COUNTRY OUTLINE
#
# Dissolve all level-1 units.
# ======================================================

pakistan = (
    level1[
        ["geometry"]
    ]
    .dissolve()
    .reset_index(
        drop=True
    )
)


# ======================================================
# 5. IDENTIFY PROVINCE CONTAINING AOI
#
# More robust than assuming spelling of "Punjab".
# ======================================================

aoi_center = Point(
    AOI_CENTER_LON,
    AOI_CENTER_LAT,
)


province_candidates = (
    level1[
        level1
        .geometry
        .covers(
            aoi_center
        )
    ]
    .copy()
)


if len(
    province_candidates
) == 0:

    # Safe fallback by name.
    province_candidates = (
        level1[
            level1[
                "GAUL1_NAME"
            ]
            .astype(str)
            .str.contains(
                "Punjab",
                case=False,
                na=False,
            )
        ]
        .copy()
    )


if len(
    province_candidates
) == 0:

    print(
        "\nAvailable province names:"
    )

    print(
        sorted(
            level1[
                "GAUL1_NAME"
            ]
            .astype(str)
            .unique()
            .tolist()
        )
    )

    raise RuntimeError(
        "Could not identify the AOI province."
    )


province = (
    province_candidates
    .iloc[
        [0]
    ]
    .copy()
)


province_name = str(
    province
    .iloc[0][
        "GAUL1_NAME"
    ]
)


province_code = (
    province
    .iloc[0][
        "GAUL1_CODE"
    ]
)


print(
    "\nDetected province:",
    province_name,
)


# ======================================================
# 6. DISTRICTS OF SELECTED PROVINCE
# ======================================================

province_districts = (
    level2[
        level2[
            "GAUL1_CODE"
        ]
        == province_code
    ]
    .copy()
)


if len(
    province_districts
) == 0:

    raise RuntimeError(
        "No districts found for selected province."
    )


# ======================================================
# 7. IDENTIFY DISTRICT CONTAINING AOI CENTER
#
# Avoids relying entirely on district-name spelling.
# ======================================================

district_candidates = (
    province_districts[
        province_districts
        .geometry
        .covers(
            aoi_center
        )
    ]
    .copy()
)


if len(
    district_candidates
) == 0:

    # Fallback to Faisalabad text match.
    district_candidates = (
        province_districts[
            province_districts[
                "GAUL2_NAME"
            ]
            .astype(str)
            .str.contains(
                "Faisalabad",
                case=False,
                na=False,
            )
        ]
        .copy()
    )


if len(
    district_candidates
) == 0:

    print(
        "\nAvailable district names:"
    )

    print(
        sorted(
            province_districts[
                "GAUL2_NAME"
            ]
            .astype(str)
            .unique()
            .tolist()
        )
    )

    raise RuntimeError(
        "Could not identify the AOI district."
    )


district = (
    district_candidates
    .iloc[
        [0]
    ]
    .copy()
)


district_name = str(
    district
    .iloc[0][
        "GAUL2_NAME"
    ]
)


print(
    "Detected district:",
    district_name,
)


# ======================================================
# 8. LOAD FINAL AGRICULTURAL MASK
# ======================================================

if not MASK_PATH.exists():

    raise FileNotFoundError(
        MASK_PATH
    )


with rasterio.open(
    MASK_PATH
) as src:

    mask = src.read(
        1,
        masked=True,
    )


    agricultural = (

        ~np.ma.getmaskarray(
            mask
        )

        & (
            mask.filled(0)
            == 1
        )
    )


    bounds = src.bounds
    transform = src.transform
    crs = src.crs


extent_km = [

    bounds.left / 1000.0,
    bounds.right / 1000.0,

    bounds.bottom / 1000.0,
    bounds.top / 1000.0,
]


agricultural_pixels = int(
    agricultural.sum()
)


pixel_area_m2 = abs(
    transform.a
    * transform.e
)


agricultural_area_km2 = (

    agricultural_pixels
    * pixel_area_m2
    / 1_000_000
)


print(
    "\nAgricultural pixels:",
    agricultural_pixels,
)

print(
    f"Agricultural area: "
    f"{agricultural_area_km2:.2f} km²"
)


# ======================================================
# 9. FIGURE
# ======================================================

fig, axes = plt.subplots(

    1,
    3,

    figsize=(
        15.5,
        5.8,
    ),

    gridspec_kw={
        "width_ratios": [
            0.88,
            1.05,
            1.15,
        ]
    },

    constrained_layout=True,
)


ax_country = axes[0]
ax_province = axes[1]
ax_detail = axes[2]


# ======================================================
# PANEL A — PAKISTAN
# ======================================================

pakistan.plot(

    ax=ax_country,

    facecolor="0.94",
    edgecolor="0.20",

    linewidth=0.9,
)


level1.boundary.plot(

    ax=ax_country,

    color="0.68",
    linewidth=0.35,
)


province.plot(

    ax=ax_country,

    facecolor="0.70",
    edgecolor="black",

    linewidth=0.9,
)


ax_country.scatter(

    AOI_CENTER_LON,
    AOI_CENTER_LAT,

    marker="*",
    s=100,

    zorder=10,
)


ax_country.set_title(
    "(a) Pakistan"
)


ax_country.set_xlabel(
    "Longitude (°E)"
)

ax_country.set_ylabel(
    "Latitude (°N)"
)

ax_country.set_aspect(
    "equal",
    adjustable="datalim",
)


# ======================================================
# PANEL B — PROVINCE AND DISTRICT
# ======================================================

province.plot(

    ax=ax_province,

    facecolor="0.96",
    edgecolor="0.20",

    linewidth=1.0,
)


province_districts.boundary.plot(

    ax=ax_province,

    color="0.65",
    linewidth=0.45,
)


district.plot(

    ax=ax_province,

    facecolor="0.68",
    edgecolor="black",

    linewidth=1.1,
)


# AOI rectangle
aoi_rectangle = Rectangle(

    (
        WEST,
        SOUTH,
    ),

    EAST - WEST,
    NORTH - SOUTH,

    fill=False,

    linewidth=1.8,

    edgecolor="black",

    zorder=10,
)


ax_province.add_patch(
    aoi_rectangle
)


ax_province.scatter(

    AOI_CENTER_LON,
    AOI_CENTER_LAT,

    marker="*",
    s=85,

    zorder=11,
)


ax_province.set_title(
    f"(b) {province_name} — {district_name}"
)


ax_province.set_xlabel(
    "Longitude (°E)"
)

ax_province.set_ylabel(
    "Latitude (°N)"
)

ax_province.set_aspect(
    "equal",
    adjustable="datalim",
)


# ======================================================
# PANEL C — AGRICULTURAL AOI
# ======================================================

study_display = np.ma.masked_where(

    ~agricultural,

    agricultural.astype(
        float
    ),
)


cmap = plt.get_cmap(
    "Greens"
).copy()

cmap.set_bad(
    "white"
)


ax_detail.imshow(

    study_display,

    extent=extent_km,

    origin="upper",

    cmap=cmap,

    vmin=0,
    vmax=1,

    interpolation="nearest",
)


ax_detail.set_title(
    "(c) Threshold-defined C25-N40 mask"
)


ax_detail.set_xlabel(
    "UTM Easting (km)"
)

ax_detail.set_ylabel(
    "UTM Northing (km)"
)

ax_detail.set_aspect(
    "equal"
)


# ======================================================
# NORTH ARROW — PANEL C
# ======================================================

ax_detail.annotate(

    "N",

    xy=(
        0.93,
        0.93,
    ),

    xytext=(
        0.93,
        0.80,
    ),

    xycoords="axes fraction",

    ha="center",
    va="center",

    fontsize=12,
    fontweight="bold",

    arrowprops={
        "arrowstyle": "-|>",
        "linewidth": 1.3,
    },
)


# ======================================================
# SCALE BAR — PANEL C
#
# Coordinates are already kilometres.
# ======================================================

x_min, x_max = ax_detail.get_xlim()
y_min, y_max = ax_detail.get_ylim()


scale_length_km = 2.0


scale_x_start = (
    x_min
    + 0.07
    * (
        x_max
        - x_min
    )
)


scale_y = (
    y_min
    + 0.07
    * (
        y_max
        - y_min
    )
)


ax_detail.plot(

    [
        scale_x_start,
        scale_x_start
        + scale_length_km,
    ],

    [
        scale_y,
        scale_y,
    ],

    color="black",
    linewidth=3,
)


ax_detail.plot(

    [
        scale_x_start,
        scale_x_start,
    ],

    [
        scale_y - 0.06,
        scale_y + 0.06,
    ],

    color="black",
    linewidth=1.2,
)


ax_detail.plot(

    [
        scale_x_start
        + scale_length_km,
        scale_x_start
        + scale_length_km,
    ],

    [
        scale_y - 0.06,
        scale_y + 0.06,
    ],

    color="black",
    linewidth=1.2,
)


ax_detail.text(

    scale_x_start
    + scale_length_km / 2,

    scale_y + 0.10,

    "2 km",

    ha="center",
    va="bottom",

    fontsize=9,

    bbox={
        "facecolor": "white",
        "alpha": 0.75,
        "edgecolor": "none",
        "pad": 1.0,
    },
)


# ======================================================
# MAP FORMATTING
# ======================================================

for ax in axes:

    ax.tick_params(
        labelsize=8.5
    )


fig.suptitle(

    (
        "Study-area location: "
        "South Jaranwala agricultural landscape, "
        f"{district_name}, {province_name}, Pakistan"
    ),

    fontsize=14,
)


fig.supxlabel(

    (
        "Administrative boundaries: "
        "FAO GAUL 2025 simplified 500 m; "
        "study raster CRS: EPSG:32643."
    ),

    fontsize=8.5,
)


# ======================================================
# SAVE
# ======================================================

fig.savefig(

    OUTPUT_PATH,

    dpi=300,

    bbox_inches="tight",

    facecolor="white",
)


plt.close(
    fig
)


print(
    "\n✅ Locator map created:"
)

print(
    OUTPUT_PATH
)


print("\n" + "=" * 92)
print("✅ STEP 19D-v2 COMPLETE")
print("=" * 92)