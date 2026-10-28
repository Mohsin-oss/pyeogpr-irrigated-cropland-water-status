from pathlib import Path
import json
import shutil

import numpy as np
import rasterio


# ======================================================
# PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "pyeogpr_W06_20260129_20260213_clean.tif"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "pyeogpr_W06_20260129_20260213_final.tif"
)

REPORT_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "pyeogpr_W06_20260129_20260213_sanitization.json"
)


NODATA_VALUE = -9999.0


EXPECTED_BANDS = [
    "Cw",
    "Cw_UNCERTAINTY",
    "laiCw",
    "laiCw_UNCERTAINTY",
    "LAI",
    "LAI_UNCERTAINTY",
]


print("=" * 84)
print("STEP 14A — LOCAL NaN/INF SANITIZATION")
print("=" * 84)


# ======================================================
# 1. CHECK INPUT
# ======================================================

if not INPUT_PATH.exists():

    raise FileNotFoundError(
        f"Input raster not found:\n{INPUT_PATH}"
    )


print("Input:")
print(INPUT_PATH)


# ======================================================
# 2. READ RAW EXPORT
# ======================================================

with rasterio.open(INPUT_PATH) as src:

    if src.count != 6:

        raise RuntimeError(
            f"Expected 6 bands, found {src.count}"
        )

    descriptions = list(
        src.descriptions
    )

    print(
        "\nBand descriptions:",
        descriptions,
    )


    # Read WITHOUT masking so we can explicitly detect
    # NaN, Inf, -Inf and existing NoData values.
    data = src.read(
        masked=False
    ).astype(
        np.float32,
        copy=False,
    )


    profile = (
        src.profile.copy()
    )

    dataset_tags = (
        src.tags()
    )

    band_tags = {
        i: src.tags(i)
        for i in range(
            1,
            src.count + 1
        )
    }


# ======================================================
# 3. IDENTIFY INVALID NUMERICAL PIXELS
# ======================================================

nonfinite_masks = (
    ~np.isfinite(data)
)


existing_nodata_mask = (
    data == NODATA_VALUE
)


invalid_by_band = (
    nonfinite_masks
    | existing_nodata_mask
)


print("\n" + "=" * 84)
print("RAW INVALID-PIXEL DIAGNOSTIC")
print("=" * 84)


nonfinite_counts = {}


for index, band_name in enumerate(
    EXPECTED_BANDS
):

    count = int(
        nonfinite_masks[
            index
        ].sum()
    )

    nonfinite_counts[
        band_name
    ] = count

    print(
        f"{band_name}: "
        f"{count} non-finite pixels"
    )


# ======================================================
# 4. CHECK WHETHER NON-FINITE LOCATIONS MATCH
# ======================================================

reference_nonfinite = (
    nonfinite_masks[0]
)


print("\nNon-finite mask mismatch vs Cw:")


nonfinite_mismatches = {}


for index in range(
    1,
    len(EXPECTED_BANDS)
):

    mismatch = int(
        np.count_nonzero(
            nonfinite_masks[index]
            != reference_nonfinite
        )
    )

    band_name = (
        EXPECTED_BANDS[index]
    )

    nonfinite_mismatches[
        band_name
    ] = mismatch

    print(
        f"{band_name}: "
        f"{mismatch}"
    )


# ======================================================
# 5. BUILD COMMON SIX-BAND INVALID MASK
# ======================================================

# If ANY of the six bands is non-finite / NoData,
# mark that pixel NoData in ALL six bands.
#
# This preserves one common spatial support for the
# integrated multi-trait analysis.

common_invalid = (
    np.any(
        invalid_by_band,
        axis=0,
    )
)


common_invalid_count = int(
    common_invalid.sum()
)


total_pixels = int(
    common_invalid.size
)


common_valid_count = (
    total_pixels
    - common_invalid_count
)


common_valid_pct = (
    100.0
    * common_valid_count
    / total_pixels
)


print("\n" + "=" * 84)
print("COMMON SIX-BAND VALIDITY")
print("=" * 84)

print(
    "Total pixels:",
    total_pixels,
)

print(
    "Common invalid pixels:",
    common_invalid_count,
)

print(
    "Common valid pixels:",
    common_valid_count,
)

print(
    f"Common valid percentage: "
    f"{common_valid_pct:.4f}%"
)


# ======================================================
# 6. SANITIZE
# ======================================================

sanitized = (
    data.copy()
)


sanitized[
    :,
    common_invalid
] = NODATA_VALUE


# Final safety check in memory.

remaining_nonfinite = int(
    (
        ~np.isfinite(
            sanitized
        )
    ).sum()
)


print(
    "\nRemaining non-finite values "
    "after sanitization:",
    remaining_nonfinite,
)


if remaining_nonfinite != 0:

    raise RuntimeError(
        "Sanitization failed: "
        "non-finite values remain."
    )


# ======================================================
# 7. PREPARE OUTPUT PROFILE
# ======================================================

profile.update(
    driver="GTiff",
    dtype="float32",
    count=6,
    nodata=NODATA_VALUE,
    compress="DEFLATE",
    tiled=True,
    predictor=3,
    BIGTIFF="IF_SAFER",
)


# ======================================================
# 8. WRITE FINAL SANITIZED GEOTIFF
# ======================================================

if OUTPUT_PATH.exists():

    OUTPUT_PATH.unlink()


with rasterio.open(
    OUTPUT_PATH,
    "w",
    **profile,
) as dst:

    dst.write(
        sanitized
    )


    # Preserve dataset metadata.

    if dataset_tags:

        dst.update_tags(
            **dataset_tags
        )


    # Preserve band names/descriptions.

    for index, description in enumerate(
        descriptions,
        start=1,
    ):

        if description is not None:

            dst.set_band_description(
                index,
                description,
            )


    # Preserve per-band tags.

    for index, tags in band_tags.items():

        if tags:

            dst.update_tags(
                index,
                **tags,
            )


print("\nSanitized GeoTIFF written:")

print(
    OUTPUT_PATH
)


# ======================================================
# 9. IMMEDIATE REOPEN CHECK
# ======================================================

with rasterio.open(
    OUTPUT_PATH
) as src:

    check_data = src.read(
        masked=True
    )


    check_values = (
        check_data.compressed()
    )


    post_nonfinite = int(
        (
            ~np.isfinite(
                check_values
            )
        ).sum()
    )


    valid_pixels = int(
        (
            ~np.ma.getmaskarray(
                check_data[0]
            )
        ).sum()
    )


    valid_pct = (
        100
        * valid_pixels
        / total_pixels
    )


    print("\n" + "=" * 84)
    print("POST-WRITE CHECK")
    print("=" * 84)

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
        "NoData:",
        src.nodata,
    )

    print(
        "Descriptions:",
        src.descriptions,
    )

    print(
        f"Valid area on band 1: "
        f"{valid_pct:.4f}%"
    )

    print(
        "Remaining non-finite "
        "valid values:",
        post_nonfinite,
    )


    if post_nonfinite != 0:

        raise RuntimeError(
            "Final raster still contains "
            "non-finite valid values."
        )


# ======================================================
# 10. WRITE SANITIZATION REPORT
# ======================================================

report = {

    "input_file":
        str(INPUT_PATH),

    "output_file":
        str(OUTPUT_PATH),

    "operation":
        (
            "Convert NaN/Inf/-Inf and existing "
            "NoData to common six-band NoData mask"
        ),

    "nodata_value":
        NODATA_VALUE,

    "bands":
        EXPECTED_BANDS,

    "nonfinite_pixels_before":
        nonfinite_counts,

    "nonfinite_mask_mismatch_vs_Cw":
        nonfinite_mismatches,

    "common_invalid_pixels":
        common_invalid_count,

    "total_pixels":
        total_pixels,

    "common_valid_pixels":
        common_valid_count,

    "common_valid_percent":
        common_valid_pct,

    "remaining_nonfinite_after":
        remaining_nonfinite,

    "scientific_values_modified":
        False,

    "invalid_values_reclassified_as_nodata":
        True,
}


with open(
    REPORT_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        report,
        f,
        indent=2,
    )


print(
    "\nSanitization report:"
)

print(
    REPORT_PATH
)


print("\n" + "=" * 84)
print("✅ LOCAL SANITIZATION COMPLETE")
print("=" * 84)