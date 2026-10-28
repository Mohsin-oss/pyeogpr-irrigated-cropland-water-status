from pathlib import Path
import sys
import numpy as np

# ======================================================
# PROJECT ROOT
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ======================================================
# IMPORTS
# ======================================================

import ee

from pyeogpr import EarthEngine

from config.project_config import GEE_PROJECT_ID
from config.study_config import (
    STUDY_BBOX,
    SPATIAL_RESOLUTION,
)


print("=" * 82)
print("STEP 13C — THREE-TRAIT PyEOGPR PRODUCTION SMOKE TEST")
print("=" * 82)


# ======================================================
# 1. SETTINGS
# ======================================================

WINDOW_START = "2026-01-29"
WINDOW_END = "2026-02-13"

SCENE_CLOUD_THRESHOLD = 80

TRAITS = [
    "Cw",
    "laiCw",
    "LAI",
]

TRAIT_UNITS = {
    "Cw": "cm",
    "laiCw": "g/m²",
    "LAI": "m²/m²",
}


# ======================================================
# 2. INITIALIZE EARTH ENGINE
# ======================================================

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")

print(
    "\nTest window:",
    WINDOW_START,
    "to",
    WINDOW_END,
)

print(
    "Scene cloud threshold:",
    f"<{SCENE_CLOUD_THRESHOLD}%",
)


# ======================================================
# 3. AOI
# ======================================================

aoi = ee.Geometry.Rectangle(
    STUDY_BBOX
)


# ======================================================
# 4. QA60 MASK
# ======================================================

def mask_qa60(image):

    qa = image.select("QA60")

    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11

    clear = (
        qa
        .bitwiseAnd(cloud_bit)
        .eq(0)
        .And(
            qa
            .bitwiseAnd(cirrus_bit)
            .eq(0)
        )
    )

    return image.updateMask(clear)


def add_ndvi(image):

    ndvi = (
        image
        .normalizedDifference(
            ["B8", "B4"]
        )
        .rename("NDVI")
    )

    return image.addBands(ndvi)


# ======================================================
# 5. RECREATE AGRICULTURAL DOMAIN
# ======================================================

SEASON_START = "2025-11-15"
SEASON_END = "2026-04-15"


dw = (
    ee.ImageCollection(
        "GOOGLE/DYNAMICWORLD/V1"
    )
    .filterBounds(aoi)
    .filterDate(
        SEASON_START,
        SEASON_END,
    )
)


crop_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(4)
        .rename("crop")
    )
    .mean()
)


built_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(6)
        .rename("built")
    )
    .mean()
)


water_frequency = (
    dw
    .map(
        lambda image:
        image
        .select("label")
        .eq(0)
        .rename("water")
    )
    .mean()
)


season_s2 = (
    ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )
    .filterBounds(aoi)
    .filterDate(
        SEASON_START,
        SEASON_END,
    )
    .filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            40,
        )
    )
    .map(mask_qa60)
    .map(add_ndvi)
)


seasonal_max_ndvi = (
    season_s2
    .select("NDVI")
    .max()
)


agricultural_mask = (
    crop_frequency
    .gte(0.25)

    .And(
        seasonal_max_ndvi
        .gte(0.40)
    )

    .And(
        built_frequency
        .lt(0.20)
    )

    .And(
        water_frequency
        .lt(0.20)
    )
)


print(
    "✅ Agricultural analysis domain recreated."
)


# ======================================================
# 6. COMMON RANDOM QA POINTS
# ======================================================

QA_POINT_COUNT = 600
QA_SCALE = 60
QA_TILE_SCALE = 16
QA_SEED = 42


random_points = (
    ee.FeatureCollection.randomPoints(
        region=aoi,
        points=QA_POINT_COUNT,
        seed=QA_SEED,
        maxError=1,
    )
)


# ======================================================
# 7. HELPER — VALID AREA
# ======================================================

def valid_area_percent(
    image,
    geometry,
):

    valid_area = (
        ee.Image.pixelArea()
        .updateMask(
            image.mask()
        )
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=60,
            maxPixels=1e8,
            tileScale=8,
        )
        .get("area")
    )

    total_area = (
        geometry
        .area(maxError=1)
    )

    return (
        ee.Number(valid_area)
        .divide(total_area)
        .multiply(100)
        .getInfo()
    )


# ======================================================
# 8. LOCAL PERCENTILE HELPER
# ======================================================

PERCENTILES = [
    5,
    25,
    50,
    75,
    95,
]


def local_percentiles(values):

    values = np.asarray(
        values,
        dtype=float,
    )

    return np.percentile(
        values,
        PERCENTILES,
    )


def print_percentiles(
    label,
    values,
    unit="",
):

    stats = local_percentiles(
        values
    )

    print(f"\n{label}")

    for p, value in zip(
        PERCENTILES,
        stats,
    ):

        print(
            f"p{p}: "
            f"{value:.6f} "
            f"{unit}"
        )

    return stats


# ======================================================
# 9. RESULT STORAGE
# ======================================================

results = {}


# ======================================================
# 10. RUN EACH TRAIT SEPARATELY
# ======================================================

for trait in TRAITS:

    print("\n" + "=" * 82)

    print(
        f"TRAIT: {trait}"
    )

    print("=" * 82)


    # --------------------------------------------------
    # Create job
    # --------------------------------------------------

    job = EarthEngine(
        projectID=GEE_PROJECT_ID,
        sensor="SENTINEL2_L1C",
        biovar=trait,
        bounding_box=STUDY_BBOX,
        temporal_extent=[
            WINDOW_START,
            WINDOW_END,
        ],
        spatial_resolution=SPATIAL_RESOLUTION,
        cloudmask=True,
        scene_cloud_threshold=SCENE_CLOUD_THRESHOLD,
    )


    # --------------------------------------------------
    # Scene count
    # --------------------------------------------------

    scenes = (
        job.imcol
        .filterBounds(job.bbox)
        .filterDate(
            WINDOW_START,
            WINDOW_END,
        )
        .filterMetadata(
            "CLOUDY_PIXEL_PERCENTAGE",
            "less_than",
            SCENE_CLOUD_THRESHOLD,
        )
    )


    scene_count = (
        scenes
        .size()
        .getInfo()
    )


    print(
        "Source L1C scenes:",
        scene_count,
    )


    if scene_count == 0:

        raise RuntimeError(
            f"No scenes for trait {trait}"
        )


    # --------------------------------------------------
    # Retrieval
    # --------------------------------------------------

    print(
        f"Running {trait} retrieval..."
    )


    retrieval = (
        job
        .calculate_GREEN(
            ee.Date(WINDOW_START),
            ee.Date(WINDOW_END),
            trait,
        )
    )


    bands = (
        retrieval
        .bandNames()
        .getInfo()
    )


    print(
        "Output bands:",
        bands,
    )


    expected_prediction = trait

    expected_uncertainty = (
        trait
        + "_UNCERTAINTY"
    )


    if (
        expected_prediction not in bands
        or expected_uncertainty not in bands
    ):

        raise RuntimeError(
            f"Unexpected bands for "
            f"{trait}: {bands}"
        )


    prediction = (
        retrieval
        .select(
            expected_prediction
        )
        .updateMask(
            agricultural_mask
        )
    )


    uncertainty = (
        retrieval
        .select(
            expected_uncertainty
        )
        .updateMask(
            agricultural_mask
        )
    )


    # --------------------------------------------------
    # Coverage
    # --------------------------------------------------

    coverage = (
        valid_area_percent(
            prediction,
            aoi,
        )
    )


    print(
        f"Valid agricultural-masked "
        f"AOI coverage: "
        f"{coverage:.2f}%"
    )


    # --------------------------------------------------
    # Sample prediction + uncertainty
    # --------------------------------------------------

    qa_image = (
        prediction
        .rename("prediction")

        .addBands(
            uncertainty
            .rename(
                "uncertainty"
            )
        )
    )


    sample = (
        qa_image
        .sampleRegions(
            collection=random_points,
            scale=QA_SCALE,
            geometries=False,
            tileScale=QA_TILE_SCALE,
        )
        .filter(
            ee.Filter.notNull(
                [
                    "prediction",
                    "uncertainty",
                ]
            )
        )
    )


    sample_count = (
        sample
        .size()
        .getInfo()
    )


    print(
        "Valid QA points:",
        sample_count,
        "/",
        QA_POINT_COUNT,
    )


    if sample_count == 0:

        raise RuntimeError(
            f"No valid samples for {trait}"
        )


    # --------------------------------------------------
    # Pull small QA vectors locally
    # --------------------------------------------------

    prediction_values = np.asarray(
        sample
        .aggregate_array(
            "prediction"
        )
        .getInfo(),
        dtype=float,
    )


    uncertainty_values = np.asarray(
        sample
        .aggregate_array(
            "uncertainty"
        )
        .getInfo(),
        dtype=float,
    )


    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------

    prediction_stats = (
        print_percentiles(
            f"{trait} prediction",
            prediction_values,
            TRAIT_UNITS[trait],
        )
    )


    uncertainty_stats = (
        print_percentiles(
            f"{trait} absolute uncertainty",
            uncertainty_values,
            TRAIT_UNITS[trait],
        )
    )


    # --------------------------------------------------
    # Basic numerical integrity checks
    # --------------------------------------------------

    nonfinite_prediction = (
        ~np.isfinite(
            prediction_values
        )
    ).sum()


    nonfinite_uncertainty = (
        ~np.isfinite(
            uncertainty_values
        )
    ).sum()


    negative_uncertainty = (
        uncertainty_values < 0
    ).sum()


    print(
        "\nNumerical integrity:"
    )

    print(
        "Non-finite predictions:",
        int(
            nonfinite_prediction
        ),
    )

    print(
        "Non-finite uncertainties:",
        int(
            nonfinite_uncertainty
        ),
    )

    print(
        "Negative uncertainties:",
        int(
            negative_uncertainty
        ),
    )


    if (
        nonfinite_prediction > 0
        or nonfinite_uncertainty > 0
        or negative_uncertainty > 0
    ):

        raise RuntimeError(
            f"Numerical integrity problem "
            f"detected for {trait}."
        )


    results[trait] = {

        "scene_count":
            scene_count,

        "coverage":
            coverage,

        "sample_count":
            sample_count,

        "prediction_stats":
            prediction_stats,

        "uncertainty_stats":
            uncertainty_stats,
    }


    print(
        f"\n✅ {trait} smoke test completed."
    )


# ======================================================
# 11. CROSS-TRAIT SUMMARY
# ======================================================

print("\n" + "=" * 82)
print("THREE-TRAIT SUMMARY")
print("=" * 82)


for trait in TRAITS:

    result = results[
        trait
    ]

    prediction_stats = (
        result[
            "prediction_stats"
        ]
    )

    uncertainty_stats = (
        result[
            "uncertainty_stats"
        ]
    )


    print(
        f"\n{trait} "
        f"[{TRAIT_UNITS[trait]}]"
    )

    print(
        "Scenes:",
        result[
            "scene_count"
        ],
    )

    print(
        f"Coverage: "
        f"{result['coverage']:.2f}%"
    )

    print(
        "QA points:",
        result[
            "sample_count"
        ],
    )

    print(
        f"Prediction "
        f"P5/P50/P95: "
        f"{prediction_stats[0]:.6f} / "
        f"{prediction_stats[2]:.6f} / "
        f"{prediction_stats[4]:.6f}"
    )

    print(
        f"Uncertainty "
        f"P5/P50/P95: "
        f"{uncertainty_stats[0]:.6f} / "
        f"{uncertainty_stats[2]:.6f} / "
        f"{uncertainty_stats[4]:.6f}"
    )


# ======================================================
# 12. FINAL STATUS
# ======================================================

print("\n" + "=" * 82)
print("✅ STEP 13C THREE-TRAIT SMOKE TEST COMPLETE")
print("=" * 82)

print(
    "No seasonal production run was performed."
)

print(
    "No Earth Engine assets or GeoTIFFs were exported."
)

print(
    "Production design remains provisional "
    "until these three trait outputs are reviewed."
)