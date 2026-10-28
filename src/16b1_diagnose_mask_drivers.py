from pathlib import Path

import numpy as np
import rasterio


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DRIVER_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "mask"
    / "agricultural_mask_drivers_20251115_20260415_v2.tif"
)

EXPECTED_BANDS = [
    "crop_frequency",
    "built_frequency",
    "water_frequency",
    "seasonal_max_ndvi",
]


print("=" * 90)
print("STEP 16B.1 — MASK-DRIVER DIAGNOSTIC")
print("=" * 90)


if not DRIVER_PATH.exists():
    raise FileNotFoundError(DRIVER_PATH)


# ======================================================
# 1. READ RASTER
# ======================================================

with rasterio.open(DRIVER_PATH) as src:

    print("\nMetadata")
    print("CRS:", src.crs)
    print("Dimensions:", src.width, "x", src.height)
    print("Resolution:", src.res)
    print("NoData:", src.nodata)
    print("Bands:", src.descriptions)

    if list(src.descriptions) != EXPECTED_BANDS:
        raise RuntimeError(
            f"Unexpected band descriptions: {src.descriptions}"
        )

    data = src.read(masked=False).astype(float)

    nodata = src.nodata


# ======================================================
# 2. RAW INVALID PIXELS
# ======================================================

if nodata is not None:
    nodata_mask = np.isclose(
        data,
        nodata,
        atol=1e-6,
        rtol=0,
    )
else:
    nodata_mask = np.zeros_like(
        data,
        dtype=bool,
    )


nonfinite = ~np.isfinite(data)

invalid = (
    nodata_mask
    | nonfinite
)


print("\n" + "=" * 90)
print("INVALID PIXELS BY BAND")
print("=" * 90)


for i, name in enumerate(EXPECTED_BANDS):

    count = int(
        invalid[i].sum()
    )

    pct = (
        100
        * count
        / invalid[i].size
    )

    print(
        f"{name}: "
        f"{count} "
        f"({pct:.4f}%)"
    )


# ======================================================
# 3. COMMON DRIVER-VALID DOMAIN
# ======================================================

driver_valid = (
    ~np.any(
        invalid,
        axis=0,
    )
)


total_pixels = int(
    driver_valid.size
)

valid_pixels = int(
    driver_valid.sum()
)

valid_pct = (
    100
    * valid_pixels
    / total_pixels
)


print("\n" + "=" * 90)
print("DRIVER-VALID DOMAIN")
print("=" * 90)

print(
    "Total pixels:",
    total_pixels,
)

print(
    "Driver-valid pixels:",
    valid_pixels,
)

print(
    f"Driver-valid percentage: "
    f"{valid_pct:.4f}%"
)


# ======================================================
# 4. EXTRACT BANDS
# ======================================================

crop = data[0]
built = data[1]
water = data[2]
max_ndvi = data[3]


# ======================================================
# 5. DISTRIBUTION HELPER
# ======================================================

def print_distribution(
    name,
    array,
):

    values = array[
        driver_valid
    ]

    values = values[
        np.isfinite(values)
    ]

    p = np.percentile(
        values,
        [0, 1, 5, 25, 50, 75, 95, 99, 100],
    )

    print(
        f"\n{name}"
    )

    for label, value in zip(
        [
            "MIN",
            "P1",
            "P5",
            "P25",
            "P50",
            "P75",
            "P95",
            "P99",
            "MAX",
        ],
        p,
    ):

        print(
            f"  {label}: "
            f"{value:.6f}"
        )

    print(
        "  Mean:",
        f"{np.mean(values):.6f}"
    )

    print(
        "  Std:",
        f"{np.std(values):.6f}"
    )


print("\n" + "=" * 90)
print("DRIVER DISTRIBUTIONS")
print("=" * 90)

print_distribution(
    "crop_frequency",
    crop,
)

print_distribution(
    "built_frequency",
    built,
)

print_distribution(
    "water_frequency",
    water,
)

print_distribution(
    "seasonal_max_ndvi",
    max_ndvi,
)


# ======================================================
# 6. BASIC RANGE CHECKS
# ======================================================

print("\n" + "=" * 90)
print("EXPECTED-RANGE CHECK")
print("=" * 90)


for name, array in [
    ("crop_frequency", crop),
    ("built_frequency", built),
    ("water_frequency", water),
]:

    values = array[
        driver_valid
    ]

    outside = int(
        (
            (values < -1e-6)
            | (values > 1.000001)
        ).sum()
    )

    print(
        f"{name} outside [0,1]: "
        f"{outside}"
    )


ndvi_values = max_ndvi[
    driver_valid
]

ndvi_outside = int(
    (
        (ndvi_values < -1.000001)
        | (ndvi_values > 1.000001)
    ).sum()
)

print(
    "seasonal_max_ndvi outside [-1,1]:",
    ndvi_outside,
)


# ======================================================
# 7. INDIVIDUAL THRESHOLD PASS RATES
# ======================================================

print("\n" + "=" * 90)
print("INDIVIDUAL THRESHOLD PASS RATES")
print("=" * 90)


def print_pass(
    label,
    condition,
):

    passed = int(
        (
            condition
            & driver_valid
        ).sum()
    )

    pct = (
        100
        * passed
        / valid_pixels
    )

    failed = (
        valid_pixels
        - passed
    )

    print(
        f"{label}: "
        f"{passed} pass, "
        f"{failed} fail "
        f"({pct:.4f}% pass)"
    )


for threshold in [
    0.20,
    0.25,
    0.30,
    0.40,
    0.50,
    0.70,
    0.90,
]:

    print_pass(
        f"crop >= {threshold:.2f}",
        crop >= threshold,
    )


print()


for threshold in [
    0.35,
    0.40,
    0.45,
    0.50,
    0.60,
    0.70,
    0.80,
]:

    print_pass(
        f"max NDVI >= {threshold:.2f}",
        max_ndvi >= threshold,
    )


print()

print_pass(
    "built < 0.20",
    built < 0.20,
)

print_pass(
    "built < 0.10",
    built < 0.10,
)

print_pass(
    "water < 0.20",
    water < 0.20,
)

print_pass(
    "water < 0.10",
    water < 0.10,
)


# ======================================================
# 8. EXACT CANDIDATE MASK COUNTS
# ======================================================

print("\n" + "=" * 90)
print("CANDIDATE MASK COUNTS")
print("=" * 90)


for crop_threshold in [
    0.20,
    0.25,
    0.30,
]:

    for ndvi_threshold in [
        0.35,
        0.40,
        0.45,
    ]:

        mask = (

            driver_valid

            & (
                crop
                >= crop_threshold
            )

            & (
                max_ndvi
                >= ndvi_threshold
            )

            & (
                built
                < 0.20
            )

            & (
                water
                < 0.20
            )
        )


        pixels = int(
            mask.sum()
        )

        pct_valid = (
            100
            * pixels
            / valid_pixels
        )

        pct_grid = (
            100
            * pixels
            / total_pixels
        )


        print(
            f"C{int(crop_threshold * 100):02d}"
            f"-N{int(ndvi_threshold * 100):02d}: "
            f"{pixels} pixels"
            f" | {pct_valid:.4f}% driver-valid"
            f" | {pct_grid:.4f}% full grid"
        )


print("\n" + "=" * 90)
print("✅ STEP 16B.1 DIAGNOSTIC COMPLETE")
print("=" * 90)