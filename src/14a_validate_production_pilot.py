from pathlib import Path
import json

import numpy as np
import rasterio


# ======================================================
# PROJECT PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RASTER_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "pyeogpr_W06_20260129_20260213_final.tif"
)
VALIDATION_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "pyeogpr_W06_20260129_20260213_final_validation.json"
)

# ======================================================
# EXPECTATIONS
# ======================================================

EXPECTED_BAND_COUNT = 6

EXPECTED_BANDS = [
    "Cw",
    "Cw_UNCERTAINTY",
    "laiCw",
    "laiCw_UNCERTAINTY",
    "LAI",
    "LAI_UNCERTAINTY",
]

EXPECTED_CRS = "EPSG:32643"

EXPECTED_RESOLUTION = 20.0

EXPECTED_NODATA = -9999.0


print("=" * 84)
print("STEP 14A — PRODUCTION GeoTIFF VALIDATION")
print("=" * 84)


# ======================================================
# 1. CHECK FILE
# ======================================================

if not RASTER_PATH.exists():

    raise FileNotFoundError(
        f"GeoTIFF not found:\n{RASTER_PATH}"
    )


print(
    "File:",
    RASTER_PATH
)

print(
    "Size:",
    f"{RASTER_PATH.stat().st_size / 1e6:.2f} MB",
)


# ======================================================
# 2. OPEN RASTER
# ======================================================

with rasterio.open(
    RASTER_PATH
) as src:

    print("\n" + "=" * 84)
    print("RASTER METADATA")
    print("=" * 84)

    print(
        "Driver:",
        src.driver,
    )

    print(
        "Width:",
        src.width,
    )

    print(
        "Height:",
        src.height,
    )

    print(
        "Band count:",
        src.count,
    )

    print(
        "CRS:",
        src.crs,
    )

    print(
        "Resolution:",
        src.res,
    )

    print(
        "Transform:",
        src.transform,
    )

    print(
        "Bounds:",
        src.bounds,
    )

    print(
        "NoData:",
        src.nodata,
    )

    print(
        "Dtypes:",
        src.dtypes,
    )

    print(
        "Band descriptions:",
        src.descriptions,
    )


    # ==================================================
    # 3. STRUCTURAL CHECKS
    # ==================================================

    errors = []


    if src.count != EXPECTED_BAND_COUNT:

        errors.append(
            f"Expected {EXPECTED_BAND_COUNT} bands, "
            f"found {src.count}."
        )


    if src.crs is None:

        errors.append(
            "Raster has no CRS."
        )

    else:

        if src.crs.to_string() != EXPECTED_CRS:

            errors.append(
                f"Expected CRS {EXPECTED_CRS}, "
                f"found {src.crs}."
            )


    xres = abs(
        src.res[0]
    )

    yres = abs(
        src.res[1]
    )


    if not np.isclose(
        xres,
        EXPECTED_RESOLUTION,
        atol=0.01,
    ):

        errors.append(
            f"Unexpected X resolution: {xres}"
        )


    if not np.isclose(
        yres,
        EXPECTED_RESOLUTION,
        atol=0.01,
    ):

        errors.append(
            f"Unexpected Y resolution: {yres}"
        )


    if src.nodata is None:

        errors.append(
            "NoData metadata is missing."
        )

    elif not np.isclose(
        src.nodata,
        EXPECTED_NODATA,
    ):

        errors.append(
            f"Unexpected NoData: {src.nodata}"
        )


    # ==================================================
    # 4. BAND STATISTICS
    # ==================================================

    band_results = {}

    validity_masks = []


    print("\n" + "=" * 84)
    print("BAND QA")
    print("=" * 84)


    for band_index, band_name in enumerate(
        EXPECTED_BANDS,
        start=1,
    ):

        data = src.read(
            band_index,
            masked=True,
        )


        valid = (
            ~np.ma.getmaskarray(data)
        )


        validity_masks.append(
            valid
        )


        values = (
            data
            .compressed()
            .astype(float)
        )


        if len(values) == 0:

            errors.append(
                f"{band_name} has no valid pixels."
            )

            continue


        nonfinite = int(
            (
                ~np.isfinite(values)
            ).sum()
        )


        if nonfinite > 0:

            errors.append(
                f"{band_name} contains "
                f"{nonfinite} non-finite values."
            )


        stats = np.percentile(
            values,
            [
                5,
                25,
                50,
                75,
                95,
            ],
        )


        valid_pixels = int(
            valid.sum()
        )


        total_pixels = int(
            valid.size
        )


        valid_pct = (
            100
            * valid_pixels
            / total_pixels
        )


        result = {

            "band_index":
                band_index,

            "band_name":
                band_name,

            "valid_pixels":
                valid_pixels,

            "total_pixels":
                total_pixels,

            "valid_percent":
                float(valid_pct),

            "minimum":
                float(
                    np.min(values)
                ),

            "p5":
                float(stats[0]),

            "p25":
                float(stats[1]),

            "p50":
                float(stats[2]),

            "p75":
                float(stats[3]),

            "p95":
                float(stats[4]),

            "maximum":
                float(
                    np.max(values)
                ),

            "nonfinite":
                nonfinite,
        }


        band_results[
            band_name
        ] = result


        print(
            f"\nBand {band_index}: "
            f"{band_name}"
        )

        print(
            f"  Valid: "
            f"{valid_pct:.2f}%"
        )

        print(
            f"  Min: "
            f"{result['minimum']}"
        )

        print(
            f"  P5: "
            f"{result['p5']}"
        )

        print(
            f"  P50: "
            f"{result['p50']}"
        )

        print(
            f"  P95: "
            f"{result['p95']}"
        )

        print(
            f"  Max: "
            f"{result['maximum']}"
        )

        print(
            f"  Non-finite: "
            f"{nonfinite}"
        )


    # ==================================================
    # 5. CHECK BAND MASK CONSISTENCY
    # ==================================================

    print("\n" + "=" * 84)
    print("BAND MASK CONSISTENCY")
    print("=" * 84)


    reference_mask = (
        validity_masks[0]
    )


    mask_mismatch = {}


    for i in range(
        1,
        len(validity_masks),
    ):

        mismatch_count = int(
            np.count_nonzero(
                validity_masks[i]
                != reference_mask
            )
        )


        mask_mismatch[
            EXPECTED_BANDS[i]
        ] = mismatch_count


        print(
            f"{EXPECTED_BANDS[i]} "
            f"vs Cw mismatch pixels: "
            f"{mismatch_count}"
        )


    # ==================================================
    # 6. NEGATIVE UNCERTAINTY CHECK
    # ==================================================

    print("\n" + "=" * 84)
    print("UNCERTAINTY INTEGRITY")
    print("=" * 84)


    uncertainty_bands = [
        "Cw_UNCERTAINTY",
        "laiCw_UNCERTAINTY",
        "LAI_UNCERTAINTY",
    ]


    negative_uncertainty = {}


    for band_name in uncertainty_bands:

        band_index = (
            EXPECTED_BANDS
            .index(band_name)
            + 1
        )


        data = src.read(
            band_index,
            masked=True,
        )


        values = (
            data
            .compressed()
            .astype(float)
        )


        count = int(
            (
                values < 0
            ).sum()
        )


        negative_uncertainty[
            band_name
        ] = count


        print(
            f"{band_name}: "
            f"{count} negative pixels"
        )


        if count > 0:

            errors.append(
                f"{band_name} contains "
                f"{count} negative values."
            )


    # ==================================================
    # 7. BUILD VALIDATION RECORD
    # ==================================================

    validation = {

        "file":
            str(RASTER_PATH),

        "driver":
            src.driver,

        "width":
            src.width,

        "height":
            src.height,

        "band_count":
            src.count,

        "expected_band_order":
            EXPECTED_BANDS,

        "band_descriptions":
            list(src.descriptions),

        "crs":
            str(src.crs),

        "resolution":
            [
                float(src.res[0]),
                float(src.res[1]),
            ],

        "nodata":
            src.nodata,

        "bounds":
            [
                src.bounds.left,
                src.bounds.bottom,
                src.bounds.right,
                src.bounds.top,
            ],

        "band_results":
            band_results,

        "mask_mismatch_vs_Cw":
            mask_mismatch,

        "negative_uncertainty":
            negative_uncertainty,

        "errors":
            errors,
    }


# ======================================================
# 8. SAVE VALIDATION JSON
# ======================================================

with open(
    VALIDATION_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        validation,
        f,
        indent=2,
    )


print("\n" + "=" * 84)
print("VALIDATION RESULT")
print("=" * 84)


if errors:

    print(
        "❌ PILOT PRODUCT FAILED VALIDATION"
    )

    for error in errors:

        print(
            "-",
            error,
        )

else:

    print(
        "✅ PILOT PRODUCT PASSED "
        "STRUCTURAL VALIDATION"
    )


print(
    "\nValidation record:"
)

print(
    VALIDATION_PATH
)


print("\n" + "=" * 84)
print("STEP 14A COMPLETE")
print("=" * 84)