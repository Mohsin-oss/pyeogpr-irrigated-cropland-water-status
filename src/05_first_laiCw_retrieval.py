from pathlib import Path
import sys

# ------------------------------------------------------
# Project root
# ------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ------------------------------------------------------
# Imports
# ------------------------------------------------------

import ee

from pyeogpr import EarthEngine

from config.project_config import GEE_PROJECT_ID
from config.study_config import (
    SMOKE_BBOX,
    SMOKE_START,
    SMOKE_END,
    SMOKE_COMPOSITE_DAYS,
    SPATIAL_RESOLUTION,
)


print("=" * 70)
print("FIRST PyEOGPR laiCw RETRIEVAL")
print("=" * 70)


# ------------------------------------------------------
# 1. Initialize Earth Engine
# ------------------------------------------------------

ee.Initialize(project=GEE_PROJECT_ID)

print("✅ Earth Engine initialized.")


# ------------------------------------------------------
# 2. Create PyEOGPR object
# ------------------------------------------------------

job = EarthEngine(
    projectID=GEE_PROJECT_ID,
    sensor="SENTINEL2_L1C",
    biovar="laiCw",
    bounding_box=SMOKE_BBOX,
    temporal_extent=[
        SMOKE_START,
        SMOKE_END,
    ],
    spatial_resolution=SPATIAL_RESOLUTION,
    cloudmask=True,
)

print("✅ PyEOGPR object created.")


# ------------------------------------------------------
# 3. Set temporal composite
# ------------------------------------------------------

job.construct_datacube(
    composite=SMOKE_COMPOSITE_DAYS
)

print(
    "Composite interval:",
    job.timeWindows,
    "days"
)


# ------------------------------------------------------
# 4. First processing window
# ------------------------------------------------------

dates = job.getInputDates(0)

start = dates["fecha_inicio"]
end = dates["fecha_fin"]

start_text = start.format("YYYY-MM-dd").getInfo()
end_text = end.format("YYYY-MM-dd").getInfo()

print("\nProcessing window:")
print("Start:", start_text)
print("End:  ", end_text)


# ------------------------------------------------------
# 5. Count source Sentinel-2 scenes
#    using the same metadata cloud threshold as PyEOGPR
# ------------------------------------------------------

source_collection = (
    job.imcol
    .filterDate(start, end)
    .filterBounds(job.bbox)
    .filterMetadata(
        "CLOUDY_PIXEL_PERCENTAGE",
        "less_than",
        40,
    )
)

scene_count = source_collection.size().getInfo()

print(
    "\nSentinel-2 scenes after <40% scene-cloud filter:",
    scene_count
)

if scene_count == 0:
    raise RuntimeError(
        "No Sentinel-2 scenes available for this processing window."
    )


# ------------------------------------------------------
# 6. Run GPR retrieval
# ------------------------------------------------------

print("\nRunning PyEOGPR GPR retrieval...")

retrieval = job.calculate_GREEN(
    start,
    end,
    "laiCw",
)

print("✅ Retrieval computed successfully.")


# ------------------------------------------------------
# 7. Inspect output bands
# ------------------------------------------------------

bands = retrieval.bandNames().getInfo()

print("\nOutput bands:")
for band in bands:
    print(" -", band)


expected_bands = {
    "laiCw",
    "laiCw_UNCERTAINTY",
}

if set(bands) != expected_bands:
    raise RuntimeError(
        f"Unexpected output bands: {bands}"
    )


print(
    "\n✅ Expected prediction and uncertainty bands are present."
)


# ------------------------------------------------------
# ------------------------------------------------------
# 8. Lightweight QA statistics
# ------------------------------------------------------

print("\n" + "=" * 70)
print("LIGHTWEIGHT RETRIEVAL QA")
print("=" * 70)

# For this initial QA we deliberately use 60 m rather
# than 20 m. This does NOT alter the retrieval itself.
# It only reduces the computational cost of summary statistics.

QA_SCALE = 60
QA_TILE_SCALE = 4


for band_name in [
    "laiCw",
    "laiCw_UNCERTAINTY",
]:

    band = retrieval.select(band_name)

    print(f"\nCalculating statistics for: {band_name}")

    stats = band.reduceRegion(
        reducer=(
            ee.Reducer.minMax()
            .combine(
                reducer2=ee.Reducer.mean(),
                sharedInputs=True,
            )
        ),
        geometry=job.bbox,
        scale=QA_SCALE,
        maxPixels=1e7,
        tileScale=QA_TILE_SCALE,
    ).getInfo()

    print(
        "Minimum:",
        stats.get(f"{band_name}_min")
    )

    print(
        "Mean:",
        stats.get(f"{band_name}_mean")
    )

    print(
        "Maximum:",
        stats.get(f"{band_name}_max")
    )


# ------------------------------------------------------
# 9. Valid-data fraction
# ------------------------------------------------------

print("\n" + "=" * 70)
print("VALID-DATA FRACTION")
print("=" * 70)


for band_name in [
    "laiCw",
    "laiCw_UNCERTAINTY",
]:

    band = retrieval.select(band_name)

    # Area represented by valid pixels
    valid_area = (
        ee.Image.pixelArea()
        .updateMask(band.mask())
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=job.bbox,
            scale=QA_SCALE,
            maxPixels=1e7,
            tileScale=QA_TILE_SCALE,
        )
        .get("area")
    )

    # Total smoke-test AOI area
    total_area = job.bbox.area(maxError=1)
    valid_fraction = (
        ee.Number(valid_area)
        .divide(total_area)
        .multiply(100)
        .getInfo()
    )

    print(
        f"{band_name}: "
        f"{valid_fraction:.2f}% valid area"
    )


print("\n" + "=" * 70)
print("✅ STEP 6 RETRIEVAL QA PASSED")
print("=" * 70)

print("Prediction band:  laiCw")
print("Uncertainty band: laiCw_UNCERTAINTY")
print(f"QA statistics scale: {QA_SCALE} m")
print(f"QA tileScale: {QA_TILE_SCALE}")

print(
    "\nImportant: the PyEOGPR retrieval itself remains "
    "at 20 m. Only these diagnostic summaries were "
    "computed at 60 m."
)

print("\nNo export has been performed.")

# ------------------------------------------------------
# STEP 7 — SCIENTIFIC QA
# Relative uncertainty and prediction plausibility
# ------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 7 — UNCERTAINTY AND PLAUSIBILITY QA")
print("=" * 70)


prediction = retrieval.select("laiCw")
uncertainty = retrieval.select("laiCw_UNCERTAINTY")


# ------------------------------------------------------
# 1. Relative uncertainty
# ------------------------------------------------------

relative_uncertainty = (
    uncertainty
    .divide(prediction)
    .multiply(100)
    .rename("relative_uncertainty_pct")
)


qa_image = (
    prediction
    .addBands(uncertainty)
    .addBands(relative_uncertainty)
)


# ------------------------------------------------------
# 2. Reproducible sample
# ------------------------------------------------------

QA_SAMPLE_SIZE = 3000
QA_SCALE = 60
QA_TILE_SCALE = 4


sample = qa_image.sample(
    region=job.bbox,
    scale=QA_SCALE,
    numPixels=QA_SAMPLE_SIZE,
    seed=42,
    geometries=False,
    tileScale=QA_TILE_SCALE,
)


sample_count = sample.size().getInfo()

print("\nSample size:", sample_count)
print("QA scale:", QA_SCALE, "m")
print("Random seed: 42")


if sample_count == 0:
    raise RuntimeError(
        "No valid pixels available for Step 7 QA."
    )


# ------------------------------------------------------
# 3. Helper for percentiles
# ------------------------------------------------------

def percentiles(collection, property_name):

    reducer = ee.Reducer.percentile(
        [5, 25, 50, 75, 95]
    )

    result = collection.reduceColumns(
        reducer=reducer,
        selectors=[property_name],
    ).getInfo()

    return result


# ------------------------------------------------------
# 4. laiCw distribution
# ------------------------------------------------------

lai_stats = percentiles(
    sample,
    "laiCw",
)

print("\n" + "-" * 70)
print("laiCw SAMPLE DISTRIBUTION [g/m²]")
print("-" * 70)

for key, value in lai_stats.items():
    print(f"{key}: {value}")


# ------------------------------------------------------
# 5. Absolute uncertainty distribution
# ------------------------------------------------------

unc_stats = percentiles(
    sample,
    "laiCw_UNCERTAINTY",
)

print("\n" + "-" * 70)
print("ABSOLUTE GPR UNCERTAINTY [g/m²]")
print("-" * 70)

for key, value in unc_stats.items():
    print(f"{key}: {value}")


# ------------------------------------------------------
# 6. Relative uncertainty distribution
# ------------------------------------------------------

rel_stats = percentiles(
    sample,
    "relative_uncertainty_pct",
)

print("\n" + "-" * 70)
print("RELATIVE UNCERTAINTY [%]")
print("-" * 70)

for key, value in rel_stats.items():
    print(f"{key}: {value}")


# ------------------------------------------------------
# 7. Uncertainty-threshold retention
# ------------------------------------------------------

print("\n" + "-" * 70)
print("UNCERTAINTY THRESHOLD RETENTION")
print("-" * 70)


for threshold in [20, 30, 40]:

    retained = sample.filter(
        ee.Filter.lt(
            "relative_uncertainty_pct",
            threshold,
        )
    ).size().getInfo()

    retained_pct = (
        retained / sample_count
    ) * 100

    print(
        f"< {threshold}% uncertainty: "
        f"{retained_pct:.2f}% of sampled pixels"
    )


# ------------------------------------------------------
# 8. Reference field-range comparison
# ------------------------------------------------------

# Approximate observed range reported for the
# original Sentinel-2 L1C crop-model field dataset.
#
# IMPORTANT:
# This is a reference envelope, NOT a hard validity mask.

REFERENCE_MIN = 32.1
REFERENCE_MAX = 887.9


below_reference = sample.filter(
    ee.Filter.lt(
        "laiCw",
        REFERENCE_MIN,
    )
).size().getInfo()


above_reference = sample.filter(
    ee.Filter.gt(
        "laiCw",
        REFERENCE_MAX,
    )
).size().getInfo()


within_reference = sample.filter(
    ee.Filter.gte(
        "laiCw",
        REFERENCE_MIN,
    )
).filter(
    ee.Filter.lte(
        "laiCw",
        REFERENCE_MAX,
    )
).size().getInfo()


print("\n" + "-" * 70)
print("REFERENCE-RANGE COMPARISON")
print("-" * 70)

print(
    f"Below {REFERENCE_MIN} g/m²: "
    f"{100 * below_reference / sample_count:.2f}%"
)

print(
    f"Within {REFERENCE_MIN}–{REFERENCE_MAX} g/m²: "
    f"{100 * within_reference / sample_count:.2f}%"
)

print(
    f"Above {REFERENCE_MAX} g/m²: "
    f"{100 * above_reference / sample_count:.2f}%"
)


print("\n" + "=" * 70)
print("✅ STEP 7 QA COMPLETE")
print("=" * 70)