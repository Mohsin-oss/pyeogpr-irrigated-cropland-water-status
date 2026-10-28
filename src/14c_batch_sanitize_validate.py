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
    / "production"
    / "raw"
)

FINAL_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "production"
    / "final"
)

QA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "production"
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
    "Cw",
    "Cw_UNCERTAINTY",
    "laiCw",
    "laiCw_UNCERTAINTY",
    "LAI",
    "LAI_UNCERTAINTY",
]

EXPECTED_CRS = "EPSG:32643"

EXPECTED_RESOLUTION = 20.0

NODATA_VALUE = -9999.0


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
        f"pyeogpr_{window_id}_"
        f"{metadata['start'].replace('-', '')}_"
        f"{metadata['end'].replace('-', '')}_raw.tif"
    )

    for window_id, metadata
    in WINDOWS.items()

    if metadata["status"] != "MISSING"
}


print("=" * 90)
print("STEP 14C — FULL-SEASON SANITIZATION + VALIDATION")
print("=" * 90)


# ======================================================
# 1. CHECK RAW INPUT FILES
# ======================================================

print("\nChecking raw production files...")


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

    print(
        "\n❌ Missing production files:"
    )

    for path in missing_files:

        print(
            path
        )

    raise FileNotFoundError(
        "Download all nine raw GeoTIFFs "
        "before running Step 14C."
    )


print(
    "\n✅ All 9 expected raw files found."
)


# ======================================================
# 2. HELPER — PERCENTILES
# ======================================================

def calculate_stats(values):

    values = np.asarray(
        values,
        dtype=float,
    )

    percentiles = np.percentile(
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
            float(
                np.min(values)
            ),

        "p5":
            float(
                percentiles[0]
            ),

        "p25":
            float(
                percentiles[1]
            ),

        "p50":
            float(
                percentiles[2]
            ),

        "p75":
            float(
                percentiles[3]
            ),

        "p95":
            float(
                percentiles[4]
            ),

        "max":
            float(
                np.max(values)
            ),
    }


# ======================================================
# 3. OUTPUT STORAGE
# ======================================================

qa_rows = []

season_json = {

    "product":
        "PyEOGPR Sentinel-2 L1C seasonal production",

    "nodata":
        NODATA_VALUE,

    "bands":
        EXPECTED_BANDS,

    "crs":
        EXPECTED_CRS,

    "resolution_m":
        EXPECTED_RESOLUTION,

    "windows": {},
}


# ======================================================
# 4. PROCESS EACH WINDOW
# ======================================================

for window_id in [
    "W01",
    "W02",
    "W04",
    "W05",
    "W06",
    "W07",
    "W08",
    "W09",
    "W10",
]:

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
    # 4A. READ RAW PRODUCT
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


        # ----------------------------------------------
        # Structural checks
        # ----------------------------------------------

        if src.count != 6:

            errors.append(
                f"Expected 6 bands, "
                f"found {src.count}"
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


        raw_descriptions = list(
            src.descriptions
        )


        if raw_descriptions != EXPECTED_BANDS:

            errors.append(
                "Unexpected band descriptions: "
                f"{raw_descriptions}"
            )


        # ----------------------------------------------
        # Read original numerical values
        # ----------------------------------------------

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

            index:
                src.tags(index)

            for index in range(
                1,
                src.count + 1,
            )
        }


        source_nodata = (
            src.nodata
        )


    # ==================================================
    # 4B. RAW INVALID-PIXEL AUDIT
    # ==================================================

    nonfinite_masks = (
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
        nonfinite_masks
        | existing_nodata
    )


    raw_nonfinite_counts = {}


    print(
        "\nRaw non-finite pixels:"
    )


    for index, band_name in enumerate(
        EXPECTED_BANDS
    ):

        count = int(
            nonfinite_masks[
                index
            ].sum()
        )


        raw_nonfinite_counts[
            band_name
        ] = count


        print(
            f"  {band_name}: "
            f"{count}"
        )


    # ==================================================
    # 4C. CHECK INVALID-MASK AGREEMENT
    # ==================================================

    reference_invalid = (
        invalid_by_band[0]
    )


    raw_mask_mismatches = {}


    print(
        "\nRaw invalid-mask mismatches "
        "vs Cw:"
    )


    for index in range(
        1,
        6,
    ):

        mismatch = int(
            np.count_nonzero(
                invalid_by_band[
                    index
                ]
                != reference_invalid
            )
        )


        band_name = (
            EXPECTED_BANDS[
                index
            ]
        )


        raw_mask_mismatches[
            band_name
        ] = mismatch


        print(
            f"  {band_name}: "
            f"{mismatch}"
        )


    # ==================================================
    # 4D. COMMON SIX-BAND VALIDITY
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


    common_invalid_pixels = int(
        common_invalid.sum()
    )


    common_valid_pixels = (
        total_pixels
        - common_invalid_pixels
    )


    common_valid_pct = (
        100
        * common_valid_pixels
        / total_pixels
    )


    print(
        "\nCommon invalid pixels:",
        common_invalid_pixels,
    )

    print(
        f"Raster-grid valid percentage: "
        f"{common_valid_pct:.4f}%"
    )


    # ==================================================
    # 4E. SANITIZE
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
        count=6,
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


            tags = (
                band_tags.get(
                    index,
                    {}
                )
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
    # 4G. REOPEN AND VALIDATE FINAL PRODUCT
    # ==================================================

    band_stats = {}

    final_masks = []

    negative_uncertainty = {}


    with rasterio.open(
        final_path
    ) as src:

        # ----------------------------------------------
        # Structural validation
        # ----------------------------------------------

        if src.count != 6:

            errors.append(
                "Final file band count "
                "is not 6."
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
            20,
            atol=0.01,
        ):

            errors.append(
                "Final X resolution incorrect."
            )


        if not np.isclose(
            abs(src.res[1]),
            20,
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
        # Numerical QA
        # ----------------------------------------------

        for band_index, band_name in enumerate(
            EXPECTED_BANDS,
            start=1,
        ):

            band = src.read(
                band_index,
                masked=True,
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


            valid_pixels = int(
                (
                    ~mask
                ).sum()
            )


            valid_pct = (
                100
                * valid_pixels
                / total_pixels
            )


            stats[
                "valid_pixels"
            ] = valid_pixels


            stats[
                "valid_percent"
            ] = float(
                valid_pct
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
        # Final mask agreement
        # ----------------------------------------------

        final_mask_mismatch = {}


        reference_mask = (
            final_masks[0]
        )


        for index in range(
            1,
            6,
        ):

            mismatch = int(
                np.count_nonzero(
                    final_masks[
                        index
                    ]
                    != reference_mask
                )
            )


            final_mask_mismatch[
                EXPECTED_BANDS[
                    index
                ]
            ] = mismatch


            if mismatch != 0:

                errors.append(
                    f"Final mask mismatch "
                    f"for "
                    f"{EXPECTED_BANDS[index]}"
                )


        # ----------------------------------------------
        # Negative uncertainty
        # ----------------------------------------------

        for band_name in [
            "Cw_UNCERTAINTY",
            "laiCw_UNCERTAINTY",
            "LAI_UNCERTAINTY",
        ]:

            band_index = (
                EXPECTED_BANDS
                .index(
                    band_name
                )
                + 1
            )


            band = src.read(
                band_index,
                masked=True,
            )


            values = (
                band
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


            if count != 0:

                errors.append(
                    f"{band_name}: "
                    f"{count} negative values."
                )


    # ==================================================
    # 4H. WINDOW QA RESULT
    # ==================================================

    passed = (
        len(errors) == 0
    )


    print(
        "\nFinal validation:"
    )

    print(
        "  Cw P5/P50/P95:",
        f"{band_stats['Cw']['p5']:.6f}",
        "/",
        f"{band_stats['Cw']['p50']:.6f}",
        "/",
        f"{band_stats['Cw']['p95']:.6f}",
    )


    print(
        "  laiCw P5/P50/P95:",
        f"{band_stats['laiCw']['p5']:.3f}",
        "/",
        f"{band_stats['laiCw']['p50']:.3f}",
        "/",
        f"{band_stats['laiCw']['p95']:.3f}",
    )


    print(
        "  LAI P5/P50/P95:",
        f"{band_stats['LAI']['p5']:.3f}",
        "/",
        f"{band_stats['LAI']['p50']:.3f}",
        "/",
        f"{band_stats['LAI']['p95']:.3f}",
    )


    print(
        "  Negative uncertainty:",
        negative_uncertainty,
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

    window_result = {

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
            common_invalid_pixels,

        "raster_grid_valid_percent":
            common_valid_pct,

        "raw_nonfinite_counts":
            raw_nonfinite_counts,

        "raw_mask_mismatch_vs_Cw":
            raw_mask_mismatches,

        "final_mask_mismatch_vs_Cw":
            final_mask_mismatch,

        "negative_uncertainty":
            negative_uncertainty,

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
    ] = window_result


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

        "total_pixels":
            total_pixels,

        "invalid_pixels":
            common_invalid_pixels,

        "valid_percent":
            round(
                common_valid_pct,
                4,
            ),

        "Cw_p5":
            band_stats[
                "Cw"
            ]["p5"],

        "Cw_p50":
            band_stats[
                "Cw"
            ]["p50"],

        "Cw_p95":
            band_stats[
                "Cw"
            ]["p95"],

        "Cw_unc_p50":
            band_stats[
                "Cw_UNCERTAINTY"
            ]["p50"],

        "laiCw_p5":
            band_stats[
                "laiCw"
            ]["p5"],

        "laiCw_p50":
            band_stats[
                "laiCw"
            ]["p50"],

        "laiCw_p95":
            band_stats[
                "laiCw"
            ]["p95"],

        "laiCw_unc_p50":
            band_stats[
                "laiCw_UNCERTAINTY"
            ]["p50"],

        "LAI_p5":
            band_stats[
                "LAI"
            ]["p5"],

        "LAI_p50":
            band_stats[
                "LAI"
            ]["p50"],

        "LAI_p95":
            band_stats[
                "LAI"
            ]["p95"],

        "LAI_unc_p50":
            band_stats[
                "LAI_UNCERTAINTY"
            ]["p50"],
    })


# ======================================================
# 5. ADD EXPLICIT MISSING W03 RECORD
# ======================================================

qa_rows.insert(
    2,
    {

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

        "total_pixels":
            "",

        "invalid_pixels":
            "",

        "valid_percent":
            "",

        "Cw_p5":
            "",

        "Cw_p50":
            "",

        "Cw_p95":
            "",

        "Cw_unc_p50":
            "",

        "laiCw_p5":
            "",

        "laiCw_p50":
            "",

        "laiCw_p95":
            "",

        "laiCw_unc_p50":
            "",

        "LAI_p5":
            "",

        "LAI_p50":
            "",

        "LAI_p95":
            "",

        "LAI_unc_p50":
            "",
    }
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
            "observations. No interpolation "
            "or synthetic filling applied."
        ),

    "validation_passed":
        "N/A",
}


# ======================================================
# 6. SAVE SEASONAL QA CSV
# ======================================================

csv_path = (
    QA_DIR
    / "pyeogpr_seasonal_production_qa.csv"
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
# 7. SAVE FULL JSON QA
# ======================================================

json_path = (
    QA_DIR
    / "pyeogpr_seasonal_production_qa.json"
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
# 8. FINAL SEASON SUMMARY
# ======================================================

print("\n" + "=" * 90)
print("SEASONAL PRODUCTION QA SUMMARY")
print("=" * 90)


all_passed = True


for row in qa_rows:

    window_id = (
        row["window_id"]
    )


    status = (
        row["status"]
    )


    if status == "MISSING":

        print(
            f"{window_id}: "
            "MISSING / NA"
        )

        continue


    passed = (
        row[
            "validation_passed"
        ]
    )


    valid_pct = (
        row[
            "valid_percent"
        ]
    )


    print(
        f"{window_id}: "
        f"{'PASS' if passed else 'FAIL'}"
        f" | status={status}"
        f" | valid={valid_pct}%"
    )


    if not passed:

        all_passed = False


print("\nSeasonal QA CSV:")

print(
    csv_path
)


print("\nSeasonal QA JSON:")

print(
    json_path
)


if all_passed:

    print(
        "\n✅ ALL 9 AVAILABLE "
        "PRODUCTION WINDOWS PASSED."
    )

else:

    print(
        "\n❌ ONE OR MORE PRODUCTION "
        "WINDOWS FAILED QA."
    )


print(
    "\nW03 remains MISSING / NA."
)

print(
    "No spatial or temporal "
    "interpolation was performed."
)


print("\n" + "=" * 90)
print("STEP 14C COMPLETE")
print("=" * 90)