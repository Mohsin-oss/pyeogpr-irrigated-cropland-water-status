from pathlib import Path
import json

import numpy as np
import rasterio


# ======================================================
# PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DRIVER_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_drivers_20251115_20260415_v2.tif"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_C25_N40_final.tif"
)

MANIFEST_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_C25_N40_manifest.json"
)


# ======================================================
# FROZEN THRESHOLDS
# ======================================================

CROP_THRESHOLD = 0.25
NDVI_THRESHOLD = 0.40

BUILT_THRESHOLD = 0.20
WATER_THRESHOLD = 0.20

NODATA_VALUE = 255


EXPECTED_BANDS = [
    "crop_frequency",
    "built_frequency",
    "water_frequency",
    "seasonal_max_ndvi",
]


print("=" * 88)
print("STEP 16C — CREATE FINAL AGRICULTURAL ANALYSIS MASK")
print("=" * 88)


# ======================================================
# 1. READ DRIVER PRODUCT
# ======================================================

if not DRIVER_PATH.exists():

    raise FileNotFoundError(
        f"Driver raster not found:\n"
        f"{DRIVER_PATH}"
    )


with rasterio.open(
    DRIVER_PATH
) as src:

    descriptions = list(
        src.descriptions
    )

    if descriptions != EXPECTED_BANDS:

        raise RuntimeError(
            f"Unexpected bands: "
            f"{descriptions}"
        )


    drivers = src.read(
        masked=True
    )


    profile = (
        src.profile.copy()
    )


    crs = src.crs
    transform = src.transform
    bounds = src.bounds
    width = src.width
    height = src.height


# ======================================================
# 2. EXTRACT DRIVERS
# ======================================================

crop = (
    drivers[0]
    .filled(np.nan)
    .astype(float)
)

built = (
    drivers[1]
    .filled(np.nan)
    .astype(float)
)

water = (
    drivers[2]
    .filled(np.nan)
    .astype(float)
)

max_ndvi = (
    drivers[3]
    .filled(np.nan)
    .astype(float)
)


driver_valid = (

    np.isfinite(crop)

    & np.isfinite(built)

    & np.isfinite(water)

    & np.isfinite(max_ndvi)
)


# ======================================================
# 3. CREATE FROZEN C25-N40 MASK
# ======================================================

agricultural = (

    driver_valid

    & (
        crop
        >= CROP_THRESHOLD
    )

    & (
        max_ndvi
        >= NDVI_THRESHOLD
    )

    & (
        built
        < BUILT_THRESHOLD
    )

    & (
        water
        < WATER_THRESHOLD
    )
)


# ======================================================
# 4. SUMMARY
# ======================================================

total_pixels = int(
    agricultural.size
)

driver_valid_pixels = int(
    driver_valid.sum()
)

agricultural_pixels = int(
    agricultural.sum()
)


agricultural_pct_grid = (
    100.0
    * agricultural_pixels
    / total_pixels
)


agricultural_pct_driver = (
    100.0
    * agricultural_pixels
    / driver_valid_pixels
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
    "\nGrid:",
    width,
    "x",
    height,
)

print(
    "Driver-valid pixels:",
    driver_valid_pixels,
)

print(
    "Agricultural pixels:",
    agricultural_pixels,
)

print(
    f"Agricultural grid coverage: "
    f"{agricultural_pct_grid:.4f}%"
)

print(
    f"Agricultural area: "
    f"{agricultural_area_km2:.3f} km²"
)


# ======================================================
# 5. WRITE MASK
# ======================================================

output = np.where(
    driver_valid,
    agricultural.astype(
        np.uint8
    ),
    NODATA_VALUE,
).astype(
    np.uint8
)


profile.update(
    driver="GTiff",
    dtype="uint8",
    count=1,
    nodata=NODATA_VALUE,
    compress="DEFLATE",
    tiled=True,
)


if OUTPUT_PATH.exists():

    OUTPUT_PATH.unlink()


with rasterio.open(
    OUTPUT_PATH,
    "w",
    **profile,
) as dst:

    dst.write(
        output,
        1,
    )

    dst.set_band_description(
        1,
        "agricultural_mask"
    )

    dst.update_tags(
        crop_frequency_threshold=CROP_THRESHOLD,
        seasonal_max_ndvi_threshold=NDVI_THRESHOLD,
        built_frequency_threshold=BUILT_THRESHOLD,
        water_frequency_threshold=WATER_THRESHOLD,
        mask_candidate="C25-N40",
    )


# ======================================================
# 6. REOPEN VALIDATION
# ======================================================

with rasterio.open(
    OUTPUT_PATH
) as src:

    mask_data = src.read(
        1,
        masked=True,
    )


    valid_values = (
        mask_data
        .compressed()
    )


    unique = np.unique(
        valid_values
    )


    print(
        "\nOutput CRS:",
        src.crs,
    )

    print(
        "Resolution:",
        src.res,
    )

    print(
        "Unique valid values:",
        unique,
    )


    if not set(
        unique.tolist()
    ).issubset(
        {0, 1}
    ):

        raise RuntimeError(
            "Final mask contains values "
            "other than 0/1."
        )


# ======================================================
# 7. MANIFEST
# ======================================================

manifest = {

    "mask_name":
        "C25-N40",

    "status":
        "FROZEN_PRIMARY_ANALYSIS_MASK",

    "driver_file":
        str(DRIVER_PATH),

    "output_file":
        str(OUTPUT_PATH),

    "thresholds": {

        "crop_frequency_gte":
            CROP_THRESHOLD,

        "seasonal_max_ndvi_gte":
            NDVI_THRESHOLD,

        "built_frequency_lt":
            BUILT_THRESHOLD,

        "water_frequency_lt":
            WATER_THRESHOLD,
    },

    "grid": {

        "crs":
            str(crs),

        "resolution_m":
            20,

        "width":
            width,

        "height":
            height,

        "bounds": [
            bounds.left,
            bounds.bottom,
            bounds.right,
            bounds.top,
        ],
    },

    "driver_valid_pixels":
        driver_valid_pixels,

    "agricultural_pixels":
        agricultural_pixels,

    "agricultural_grid_percent":
        agricultural_pct_grid,

    "agricultural_driver_valid_percent":
        agricultural_pct_driver,

    "agricultural_area_km2":
        agricultural_area_km2,

    "sensitivity_test": {

        "crop_thresholds":
            [
                0.20,
                0.25,
                0.30,
            ],

        "ndvi_thresholds":
            [
                0.35,
                0.40,
                0.45,
            ],

        "candidate_area_range_percent":
            [
                88.54,
                89.70,
            ],

        "maximum_normalized_MAD_percent":
            0.39,

        "minimum_seasonal_pearson_r":
            1.0,

        "conclusion":
            (
                "Seasonal median trajectories "
                "were insensitive to reasonable "
                "threshold perturbations."
            ),
    },

    "interpolation":
        False,
}


with open(
    MANIFEST_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        manifest,
        f,
        indent=2,
    )


print(
    "\nFinal mask:"
)

print(
    OUTPUT_PATH
)

print(
    "\nManifest:"
)

print(
    MANIFEST_PATH
)


print("\n" + "=" * 88)
print("✅ STEP 16C COMPLETE — AGRICULTURAL MASK FROZEN")
print("=" * 88)