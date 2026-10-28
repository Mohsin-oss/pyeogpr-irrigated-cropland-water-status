# Executive project summary

**Uncertainty-Aware Retrieval of Vegetation Water Traits from Sentinel-2 for Irrigated Cropland Monitoring in Punjab, Pakistan**  
Mohsin Ahmad · Research project · 28 October 2026

## Problem

Satellite observations can describe seasonal vegetation development over irrigated cropland, but their water-related interpretation is limited by clouds, incomplete spatial coverage and uncertain model retrievals. A high correlation with a conventional vegetation index does not establish field accuracy, and an apparently simple uncertainty threshold can change which pixels are retained. This project examined those issues for South Jaranwala / Buchiana in Faisalabad District, Punjab.

## Method

The workflow used Sentinel-2 harmonized Level-1C mean-reflectance composites and pretrained PyEOGPR models to retrieve leaf equivalent water content (Cw), canopy water content (laiCw) and leaf area index (LAI), together with native absolute model uncertainty. NDVI and NDMI provided satellite-index comparisons. CHIRPS rainfall and ERA5-Land soil-water/temperature variables supplied broad environmental context.

The nominal study season was 15 November 2025–15 April 2026. Ten complete 15-day production windows end on 14 April (exclusive); the remaining day was not analyzed. Eight windows were GOOD, W03 was MISSING, and W09 was LIMITED. Missing EO was not interpolated. W09 was retained descriptively and excluded from primary temporal correlations.

The primary analysis used **223,600 retrieval-supported agricultural pixels (89.44 km²), representing 97.33% of the 91.89 km² threshold-defined C25-N40 agricultural mask**. Nine nearby mask-threshold combinations and a stable-support comparison assessed whether domain choices changed the seasonal conclusions. Three relative-uncertainty cutoffs were tested as sensitivity treatments only.

## Main results

Canopy traits showed strong seasonal correspondence with conventional indices. Across eight GOOD windows, temporal Pearson correlations were 0.9833 for laiCw–NDVI, 0.9617 for laiCw–NDMI and 0.9861 for LAI–NDVI. Cw had a more variable spatial relationship with NDMI, ranging from 0.2810 to 0.8646 across GOOD windows.

The seasonal trajectories were insensitive to the tested nearby mask thresholds: maximum normalized MAD was 0.3870%. The stable-support maximum was approximately 0.000002%, indicating that changes in spatial support did not explain the GOOD-window trajectories. W09 covered only 55.0215% of the stable core, supporting its LIMITED designation.

## Central uncertainty finding

Hard relative-uncertainty filtering caused severe retention loss and large shifts in trait medians. The maximum absolute shift was 1427.70% for laiCw at RU <20%. This does not mean that the unfiltered retrieval was wrong by that amount; it means that selecting a small subset greatly changed the median. Because RU divides uncertainty by trait magnitude, it can favor higher-magnitude retrievals and distort seasonal comparisons.

The primary analysis therefore retains native absolute uncertainty continuously. Spatial IQR is reported as spatial variability, and native GPR uncertainty is not presented as a confidence interval for the seasonal median. No universal RU threshold is treated as a validation rule.

## Limits and significance

All trait/index comparisons share Sentinel-2 information, so correspondence is not independent validation. Hydroclimate is coarse environmental context rather than field-level irrigation observation. The strongest raw environmental association, laiCw versus the upper-soil-water proxy (r = −0.7476), is descriptive and strongly confounded by seasonal development; it does not show that wetter soil caused lower canopy water content.

The study is limited to one landscape, one season and eight primary temporal samples, with no independent field observations or local calibration of model uncertainty. It cannot establish validated crop water stress, irrigation deficit or drought stress. The archive provides code, evidence tables, figures and documentation; raw and processed rasters are retained locally and are needed for full pixel-level reproduction.

The contribution is an explicit, reproducible account of vegetation-water dynamics and the consequences of uncertainty-based selection. It demonstrates practical spatial water science and hydroinformatics skills while preserving the distinction between measured output, interpretation and validation. The work is a research project with potential for manuscript development, not a claimed peer-reviewed publication.

See [the report](final_report.md), [captions](captions.md), and [reproduction guide](reproducibility.md) for evidence and implementation details.
