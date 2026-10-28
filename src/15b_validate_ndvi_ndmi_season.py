from pathlib import Path
import csv
import json

import numpy as np
import rasterio


# ======================================================
# PROJECT PATHS
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "indices"
    / "raw"
)

FINAL_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "indices"
    / "final"
)

QA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "indices"
    / "qa"
)

FINAL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

QA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ======================================================
# FROZEN PRODUCT SPECIFICATION
# ======================================================

EXPECTED_BANDS = [
    "NDVI",
    "NDMI",
]

EXPECTED_CRS = "EPSG:32643"

EXPECTED_RESOLUTION = 20.0

NODATA_VALUE = -9999.0

INDEX_MIN = -1.0
INDEX_MAX = 1.0

# Small tolerance only for floating-point precision.
RANGE_TOLERANCE = 1e-6


# ======================================================
# WINDOW METADATA
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


# ======================================================
# EXPECTED RAW FILES
# ======================================================

EXPECTED_RAW_FILES = {

    window_id: (
        f"indices_{window_id}_"
        f"{metadata['start'].replace('-', '')}_"
        f"{metadata['end'].replace('-', '')}_raw.tif"
    )

    for window_id, metadata
    in WINDOWS.items()

    if metadata["status"] != "MISSING"
}


print("=" * 90)
print("STEP 15B — SEASONAL NDVI + NDMI SANITIZATION AND QA")
print("=" * 90)


# ======================================================
# 1. CHECK INPUT FILES
# ======================================================

print("\nChecking raw index files...")


missing_files = []


for window_id, filename in EXPECTED_RAW_FILES.items():

    path = RAW_DIR / filename

    if not path.exists():

        missing_files.append(
            str(path)
        )

    else:

        print(
            f"✅ {window_id}: {filename}"
        )


if missing_files:

    print("\n❌ Missing files:")

    for path in missing_files:

        print(path)

    raise FileNotFoundError(
        "All nine raw NDVI/NDMI GeoTIFFs "
        "must be downloaded before Step 15B."
    )


print(
    "\n✅ All 9 expected index files found."
)


# ======================================================
# 2. STATISTICS HELPER
# ======================================================

def calculate_stats(values):

    values = np.asarray(
        values,
        dtype=float,
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

        "min":
            float(np.min(values)),

        "p5":
            float(p[0]),

        "p25":
            float(p[1]),

        "p50":
            float(p[2]),

        "p75":
            float(p[3]),

        "p95":
            float(p[4]),

        "max":
            float(np.max(values)),
    }


# ======================================================
# 3. RESULT STORAGE
# ======================================================

qa_rows = []


season_json = {

    "product":
        "Sentinel-2 L2A seasonal NDVI + NDMI",

    "source":
        "COPERNICUS/S2_SR_HARMONIZED",

    "bands":
        EXPECTED_BANDS,

    "crs":
        EXPECTED_CRS,

    "resolution_m":
        EXPECTED_RESOLUTION,

    "nodata":
        NODATA_VALUE,

    "temporal_processing":
        (
            "Mean surface-reflectance composite "
            "followed by index calculation"
        ),

    "windows": {},
}


# ======================================================
# 4. PROCESS AVAILABLE WINDOWS
# ======================================================

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


for window_id in AVAILABLE_WINDOWS:

    metadata = WINDOWS[
        window_id
    ]

    raw_filename = (
        EXPECTED_RAW_FILES[
            window_id
        ]
    )

    raw_path = (
        RAW_DIR
        / raw_filename
    )


    final_filename = (
        raw_filename
        .replace(
            "_raw.tif",
            "_final.tif",
        )
    )

    final_path = (
        FINAL_DIR
        / final_filename
    )


    print("\n" + "=" * 90)

    print(
        f"{window_id}: "
        f"{metadata['start']} → "
        f"{metadata['end']}"
    )

    print(
        "Declared status:",
        metadata["status"],
    )

    print("=" * 90)


    errors = []


    # ==================================================
    # 4A. READ RAW RASTER
    # ==================================================

    with rasterio.open(
        raw_path
    ) as src:

        print(
            "Raw raster:",
            raw_filename,
        )

        print(
            "Dimensions:",
            src.width,
            "x",
            src.height,
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
            "Bands:",
            src.descriptions,
        )


        if src.count != 2:

            errors.append(
                f"Expected 2 bands; "
                f"found {src.count}."
            )


        if (
            src.crs is None
            or src.crs.to_string()
            != EXPECTED_CRS
        ):

            errors.append(
                f"Unexpected CRS: "
                f"{src.crs}"
            )


        if not np.isclose(
            abs(src.res[0]),
            EXPECTED_RESOLUTION,
            atol=0.01,
        ):

            errors.append(
                f"Unexpected X resolution: "
                f"{src.res[0]}"
            )


        if not np.isclose(
            abs(src.res[1]),
            EXPECTED_RESOLUTION,
            atol=0.01,
        ):

            errors.append(
                f"Unexpected Y resolution: "
                f"{src.res[1]}"
            )


        descriptions = list(
            src.descriptions
        )


        if descriptions != EXPECTED_BANDS:

            errors.append(
                f"Unexpected bands: "
                f"{descriptions}"
            )


        data = (
            src
            .read(
                masked=False
            )
            .astype(
                np.float32,
                copy=False,
            )
        )


        profile = (
            src.profile.copy()
        )


        dataset_tags = (
            src.tags()
        )


        band_tags = {

            i:
                src.tags(i)

            for i in range(
                1,
                src.count + 1
            )
        }


        source_nodata = (
            src.nodata
        )


    # ==================================================
    # 4B. INVALID PIXEL DETECTION
    # ==================================================

    nonfinite = (
        ~np.isfinite(
            data
        )
    )


    if source_nodata is not None:

        existing_nodata = (
            np.isclose(
                data,
                source_nodata,
                rtol=0,
                atol=1e-6,
            )
        )

    else:

        existing_nodata = (
            np.zeros_like(
                data,
                dtype=bool,
            )
        )


    invalid_by_band = (
        nonfinite
        | existing_nodata
    )


    raw_nonfinite = {}


    print(
        "\nRaw non-finite pixels:"
    )


    for index, band_name in enumerate(
        EXPECTED_BANDS
    ):

        count = int(
            nonfinite[
                index
            ].sum()
        )

        raw_nonfinite[
            band_name
        ] = count


        print(
            f"  {band_name}: "
            f"{count}"
        )


    # ==================================================
    # 4C. INVALID MASK AGREEMENT
    # ==================================================

    invalid_mismatch = int(
        np.count_nonzero(
            invalid_by_band[0]
            != invalid_by_band[1]
        )
    )


    print(
        "\nNDMI invalid-mask mismatch "
        "vs NDVI:",
        invalid_mismatch,
    )


    # ==================================================
    # 4D. CREATE COMMON TWO-BAND MASK
    # ==================================================

    common_invalid = (
        np.any(
            invalid_by_band,
            axis=0,
        )
    )


    total_pixels = int(
        common_invalid.size
    )


    invalid_pixels = int(
        common_invalid.sum()
    )


    valid_pixels = (
        total_pixels
        - invalid_pixels
    )


    valid_percent = (
        100.0
        * valid_pixels
        / total_pixels
    )


    print(
        "\nCommon invalid pixels:",
        invalid_pixels,
    )

    print(
        f"Common valid percentage: "
        f"{valid_percent:.4f}%"
    )


    # ==================================================
    # 4E. SANITIZE NON-FINITE VALUES
    # ==================================================

    sanitized = (
        data.copy()
    )


    sanitized[
        :,
        common_invalid
    ] = NODATA_VALUE


    remaining_nonfinite = int(
        (
            ~np.isfinite(
                sanitized
            )
        ).sum()
    )


    if remaining_nonfinite != 0:

        errors.append(
            "Non-finite values remain "
            "after sanitization."
        )


    # ==================================================
    # 4F. WRITE FINAL PRODUCT
    # ==================================================

    profile.update(
        driver="GTiff",
        dtype="float32",
        count=2,
        nodata=NODATA_VALUE,
        compress="DEFLATE",
        tiled=True,
        predictor=3,
        BIGTIFF="IF_SAFER",
    )


    if final_path.exists():

        final_path.unlink()


    with rasterio.open(
        final_path,
        "w",
        **profile,
    ) as dst:

        dst.write(
            sanitized
        )


        if dataset_tags:

            dst.update_tags(
                **dataset_tags
            )


        for index, band_name in enumerate(
            EXPECTED_BANDS,
            start=1,
        ):

            dst.set_band_description(
                index,
                band_name,
            )


            tags = band_tags.get(
                index,
                {}
            )


            if tags:

                dst.update_tags(
                    index,
                    **tags,
                )


    print(
        "\nFinal raster written:"
    )

    print(
        final_path
    )


    # ==================================================
    # 4G. FINAL VALIDATION
    # ==================================================

    band_stats = {}

    final_masks = []

    out_of_range = {}


    with rasterio.open(
        final_path
    ) as src:


        if src.count != 2:

            errors.append(
                "Final raster does not "
                "contain two bands."
            )


        if (
            src.crs is None
            or src.crs.to_string()
            != EXPECTED_CRS
        ):

            errors.append(
                "Final CRS incorrect."
            )


        if not np.isclose(
            abs(src.res[0]),
            EXPECTED_RESOLUTION,
            atol=0.01,
        ):

            errors.append(
                "Final X resolution incorrect."
            )


        if not np.isclose(
            abs(src.res[1]),
            EXPECTED_RESOLUTION,
            atol=0.01,
        ):

            errors.append(
                "Final Y resolution incorrect."
            )


        if src.nodata is None:

            errors.append(
                "Final NoData metadata missing."
            )

        elif not np.isclose(
            src.nodata,
            NODATA_VALUE,
        ):

            errors.append(
                "Final NoData value incorrect."
            )


        if list(
            src.descriptions
        ) != EXPECTED_BANDS:

            errors.append(
                "Final band descriptions incorrect."
            )


        # ----------------------------------------------
        # Band-level statistics
        # ----------------------------------------------

        for band_index, band_name in enumerate(
            EXPECTED_BANDS,
            start=1,
        ):

            band = (
                src.read(
                    band_index,
                    masked=True,
                )
            )


            mask = (
                np.ma.getmaskarray(
                    band
                )
            )


            final_masks.append(
                mask
            )


            values = (
                band
                .compressed()
                .astype(float)
            )


            if len(values) == 0:

                errors.append(
                    f"{band_name}: "
                    "no valid pixels."
                )

                continue


            nonfinite_valid = int(
                (
                    ~np.isfinite(
                        values
                    )
                ).sum()
            )


            if nonfinite_valid != 0:

                errors.append(
                    f"{band_name}: "
                    f"{nonfinite_valid} "
                    "non-finite valid values."
                )


            stats = (
                calculate_stats(
                    values
                )
            )


            band_valid_pixels = int(
                (
                    ~mask
                ).sum()
            )


            band_valid_percent = (
                100.0
                * band_valid_pixels
                / total_pixels
            )


            # ------------------------------------------
            # Physical index range check
            # ------------------------------------------

            low_count = int(
                (
                    values
                    < (
                        INDEX_MIN
                        - RANGE_TOLERANCE
                    )
                ).sum()
            )


            high_count = int(
                (
                    values
                    > (
                        INDEX_MAX
                        + RANGE_TOLERANCE
                    )
                ).sum()
            )


            range_count = (
                low_count
                + high_count
            )


            out_of_range[
                band_name
            ] = {

                "below_minus_one":
                    low_count,

                "above_plus_one":
                    high_count,

                "total":
                    range_count,
            }


            if range_count != 0:

                errors.append(
                    f"{band_name}: "
                    f"{range_count} values "
                    "outside [-1, 1]."
                )


            stats[
                "valid_pixels"
            ] = (
                band_valid_pixels
            )


            stats[
                "valid_percent"
            ] = float(
                band_valid_percent
            )


            stats[
                "nonfinite_valid"
            ] = (
                nonfinite_valid
            )


            band_stats[
                band_name
            ] = stats


        # ----------------------------------------------
        # Final mask consistency
        # ----------------------------------------------

        final_mask_mismatch = int(
            np.count_nonzero(
                final_masks[0]
                != final_masks[1]
            )
        )


        if final_mask_mismatch != 0:

            errors.append(
                f"Final NDVI/NDMI mask "
                f"mismatch: "
                f"{final_mask_mismatch}"
            )


    # ==================================================
    # 4H. PRINT QA RESULT
    # ==================================================

    passed = (
        len(errors) == 0
    )


    print(
        "\nFinal index QA:"
    )


    print(
        "  NDVI P5/P50/P95:",
        f"{band_stats['NDVI']['p5']:.4f}",
        "/",
        f"{band_stats['NDVI']['p50']:.4f}",
        "/",
        f"{band_stats['NDVI']['p95']:.4f}",
    )


    print(
        "  NDMI P5/P50/P95:",
        f"{band_stats['NDMI']['p5']:.4f}",
        "/",
        f"{band_stats['NDMI']['p50']:.4f}",
        "/",
        f"{band_stats['NDMI']['p95']:.4f}",
    )


    print(
        "  Values outside [-1, 1]:",
        out_of_range,
    )


    print(
        "  Final mask mismatch:",
        final_mask_mismatch,
    )


    if passed:

        print(
            f"✅ {window_id} PASSED"
        )

    else:

        print(
            f"❌ {window_id} FAILED"
        )

        for error in errors:

            print(
                "   -",
                error,
            )


    # ==================================================
    # 4I. SAVE WINDOW RESULT
    # ==================================================

    result = {

        "window_id":
            window_id,

        "start":
            metadata["start"],

        "end_exclusive":
            metadata["end"],

        "declared_status":
            metadata["status"],

        "raw_file":
            str(raw_path),

        "final_file":
            str(final_path),

        "total_pixels":
            total_pixels,

        "common_invalid_pixels":
            invalid_pixels,

        "valid_percent":
            valid_percent,

        "raw_nonfinite":
            raw_nonfinite,

        "raw_invalid_mask_mismatch":
            invalid_mismatch,

        "final_mask_mismatch":
            final_mask_mismatch,

        "out_of_range":
            out_of_range,

        "band_stats":
            band_stats,

        "validation_passed":
            passed,

        "errors":
            errors,
    }


    season_json[
        "windows"
    ][
        window_id
    ] = result


    qa_rows.append({

        "window_id":
            window_id,

        "start":
            metadata["start"],

        "end_exclusive":
            metadata["end"],

        "status":
            metadata["status"],

        "validation_passed":
            passed,

        "valid_percent":
            round(
                valid_percent,
                4,
            ),

        "NDVI_p5":
            band_stats[
                "NDVI"
            ]["p5"],

        "NDVI_p25":
            band_stats[
                "NDVI"
            ]["p25"],

        "NDVI_p50":
            band_stats[
                "NDVI"
            ]["p50"],

        "NDVI_p75":
            band_stats[
                "NDVI"
            ]["p75"],

        "NDVI_p95":
            band_stats[
                "NDVI"
            ]["p95"],

        "NDMI_p5":
            band_stats[
                "NDMI"
            ]["p5"],

        "NDMI_p25":
            band_stats[
                "NDMI"
            ]["p25"],

        "NDMI_p50":
            band_stats[
                "NDMI"
            ]["p50"],

        "NDMI_p75":
            band_stats[
                "NDMI"
            ]["p75"],

        "NDMI_p95":
            band_stats[
                "NDMI"
            ]["p95"],

        "NDVI_out_of_range":
            out_of_range[
                "NDVI"
            ]["total"],

        "NDMI_out_of_range":
            out_of_range[
                "NDMI"
            ]["total"],
    })


# ======================================================
# 5. ADD W03 EXPLICITLY
# ======================================================

w03_row = {

    "window_id":
        "W03",

    "start":
        WINDOWS["W03"]["start"],

    "end_exclusive":
        WINDOWS["W03"]["end"],

    "status":
        "MISSING",

    "validation_passed":
        "N/A",

    "valid_percent":
        "",

    "NDVI_p5":
        "",

    "NDVI_p25":
        "",

    "NDVI_p50":
        "",

    "NDVI_p75":
        "",

    "NDVI_p95":
        "",

    "NDMI_p5":
        "",

    "NDMI_p25":
        "",

    "NDMI_p50":
        "",

    "NDMI_p75":
        "",

    "NDMI_p95":
        "",

    "NDVI_out_of_range":
        "",

    "NDMI_out_of_range":
        "",
}


qa_rows.insert(
    2,
    w03_row,
)


season_json[
    "windows"
][
    "W03"
] = {

    "window_id":
        "W03",

    "start":
        WINDOWS["W03"]["start"],

    "end_exclusive":
        WINDOWS["W03"]["end"],

    "declared_status":
        "MISSING",

    "reason":
        (
            "No adequate clear Sentinel-2 "
            "observations. No interpolation."
        ),

    "validation_passed":
        "N/A",
}


# ======================================================
# 6. SAVE SEASONAL QA CSV
# ======================================================

csv_path = (
    QA_DIR
    / "indices_seasonal_qa.csv"
)


fieldnames = list(
    qa_rows[0].keys()
)


with open(
    csv_path,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
    )

    writer.writeheader()

    writer.writerows(
        qa_rows
    )


# ======================================================
# 7. SAVE FULL JSON
# ======================================================

json_path = (
    QA_DIR
    / "indices_seasonal_qa.json"
)


with open(
    json_path,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        season_json,
        f,
        indent=2,
    )


# ======================================================
# 8. SEASON SUMMARY
# ======================================================

print("\n" + "=" * 90)
print("SEASONAL INDEX QA SUMMARY")
print("=" * 90)


all_passed = True


for row in qa_rows:

    if (
        row["status"]
        == "MISSING"
    ):

        print(
            f"{row['window_id']}: "
            "MISSING / NA"
        )

        continue


    print(
        f"{row['window_id']}: "
        f"{'PASS' if row['validation_passed'] else 'FAIL'}"
        f" | status={row['status']}"
        f" | valid={row['valid_percent']}%"
        f" | NDVI50={row['NDVI_p50']:.4f}"
        f" | NDMI50={row['NDMI_p50']:.4f}"
    )


    if not row[
        "validation_passed"
    ]:

        all_passed = False


print(
    "\nSeasonal index QA CSV:"
)

print(
    csv_path
)


print(
    "\nSeasonal index QA JSON:"
)

print(
    json_path
)


if all_passed:

    print(
        "\n✅ ALL 9 AVAILABLE "
        "INDEX WINDOWS PASSED."
    )

else:

    print(
        "\n❌ ONE OR MORE INDEX "
        "WINDOWS FAILED."
    )


print(
    "\nW03 remains MISSING / NA."
)

print(
    "W09 remains LIMITED."
)

print(
    "No interpolation was performed."
)


print("\n" + "=" * 90)
print("STEP 15B COMPLETE")
print("=" * 90)