# Final figure and table captions

All EO summaries use the retrieval-supported agricultural domain for GOOD windows (223,600 pixels; 89.44 km²), unless explicitly stated otherwise. The threshold-defined C25-N40 mask is larger: 229,729 pixels; 91.8916 km². W03 is MISSING without interpolation; W09 is LIMITED and excluded from primary temporal correlations. Lines connecting observed windows are visual guides, not additional observations.

## Window key

Intervals are start-inclusive and end-exclusive. The nominal season ends on 15 April; the ten complete production windows end on 14 April.

| Window | Start | End (exclusive) | Status |
|---|---|---|---|
| W01 | 2025-11-15 | 2025-11-30 | GOOD |
| W02 | 2025-11-30 | 2025-12-15 | GOOD |
| W03 | 2025-12-15 | 2025-12-30 | MISSING |
| W04 | 2025-12-30 | 2026-01-14 | GOOD |
| W05 | 2026-01-14 | 2026-01-29 | GOOD |
| W06 | 2026-01-29 | 2026-02-13 | GOOD |
| W07 | 2026-02-13 | 2026-02-28 | GOOD |
| W08 | 2026-02-28 | 2026-03-15 | GOOD |
| W09 | 2026-03-15 | 2026-03-30 | LIMITED |
| W10 | 2026-03-30 | 2026-04-14 | GOOD |

## Figure 1

Seasonal PyEOGPR vegetation traits. Lines show spatial medians of Cw (cm), laiCw (g m⁻²) and LAI (m² m⁻²); shading shows spatial interquartile ranges. W03 is blank, and the open diamond marks W09 on its reduced valid footprint. The shading is spatial variation, not model uncertainty or a confidence interval for the median.

[Full-resolution figure](../figures/final_core/Figure_01_PyEOGPR_traits_final.png)

## Figure 2

Seasonal Sentinel-2 NDVI and NDMI (dimensionless). Lines and shading show agricultural-domain medians and spatial interquartile ranges. W03 remains missing; the open diamond marks limited W09. These indices share Sentinel-2 inputs with PyEOGPR and provide comparison rather than independent validation.

[Full-resolution figure](../figures/final_core/Figure_02_indices_final.png)

## Figure 3

Broad hydroclimatic context: CHIRPS within-window and antecedent 30-day rainfall totals (mm), ERA5-Land upper-soil-water proxy (m³ m⁻³), and 2-m temperature (°C). Climate observations remain available during missing EO window W03. Values describe the study-area context at the source datasets’ coarse support; they are neither field irrigation measurements nor retrieval validation.

[Full-resolution figure](../figures/final_core/Figure_03_hydroclimate_final.png)

## Figure 4

Selection effects of hard relative-uncertainty filtering. The upper panel shows median percentage of the threshold-defined agricultural domain retained; the lower panel shows median absolute percentage shift in the trait median, summarized over eight GOOD windows. RU <20%, <30% and <40% are sensitivity treatments only. W03 and W09 do not enter these GOOD-window summaries. The plotted median shift differs from the maximum shift reported in Table 4; these thresholds do not identify validated retrievals.

[Full-resolution figure](../figures/final_core/Figure_04_RU_selection_effect_final.png)

## Figure 5

Standardized seasonal medians of Cw, laiCw, LAI, NDVI and NDMI (dimensionless z-scores). Means and standard deviations are estimated from the eight GOOD windows only. W09, identified by open diamonds, is transformed using those parameters; W03 remains missing. Common trajectory shape indicates correspondence among shared-input EO products, not independent accuracy.

[Full-resolution figure](../figures/final_core/Figure_05_standardized_EO_final.png)

## Figure 6

Native absolute GPR uncertainty in Cw (cm), laiCw (g m⁻²) and LAI (m² m⁻²). Lines show the spatial median of the uncertainty output; shading shows its spatial IQR. W03 is missing and W09 is marked as limited. Neither the uncertainty output nor its IQR is a confidence interval for the seasonal trait median; independent uncertainty calibration is unavailable here.

[Full-resolution figure](../figures/final_core/Figure_06_PyEOGPR_uncertainty_final.png)

## Figure 7

Threshold-defined C25-N40 agricultural mask, comprising 229,729 20 m pixels (91.8916 km²). Green denotes pixels meeting crop-frequency ≥0.25, seasonal-maximum-NDVI ≥0.40, built-up-frequency <0.20 and water-frequency <0.20 criteria. Coordinates use EPSG:32643. This map displays the larger mask, not the common retrieval-supported GOOD-window domain of 223,600 pixels (89.44 km²).

[Full-resolution figure](../figures/spatial_final/Figure_07_agricultural_domain_final.png)

## Figure 8

Spatial PyEOGPR Cw (cm), laiCw (g m⁻²) and LAI (m² m⁻²) for W02 (early season), W07 (high-canopy stage; peak trait medians) and W10 (late season). All are GOOD windows. Per-variable scales are shared across dates and set from the 2nd–98th percentiles across GOOD windows. White pixels lie outside the threshold mask or lack valid retrievals. Axes show UTM coordinates in km; the grid is 20 m. Values outside the display limits may saturate in color; scales are not new validity thresholds.

[Full-resolution figure](../figures/spatial_final/Figure_08_trait_maps_final.png)

## Figure 9

Native absolute PyEOGPR uncertainty for Cw (cm), laiCw (g m⁻²) and LAI (m² m⁻²) in GOOD windows W02, W07 and W10. Each variable uses the same 2nd–98th percentile display limits across dates, calculated over GOOD windows. White pixels are outside the mask or lack valid retrievals. UTM axes are in km on a 20 m grid. These model uncertainty maps are not field-validated error maps or confidence intervals for spatial medians.

[Full-resolution figure](../figures/spatial_final/Figure_09_uncertainty_maps_final.png)

## Figure 10

Study-area location within Pakistan, Punjab and Faisalabad, with a detailed panel of the threshold-defined C25-N40 mask. The detailed mask covers 91.8916 km²; the primary retrieval-supported domain is 89.44 km² (97.33% of this mask). Geographic panels use longitude/latitude and the detail uses EPSG:32643 UTM coordinates. Administrative boundaries are FAO GAUL simplified 2025, as specified in the generating script. The map locates the study; it does not map irrigation deliveries or validate land cover.

[Full-resolution figure](../figures/locator/Figure_10_study_area_locator.png)

## Table 1 — Final seasonal summary

Window-level EO status, common agricultural coverage, spatial median traits (Cw, cm; laiCw, g m⁻²; LAI, m² m⁻²), dimensionless NDVI/NDMI, rainfall totals (mm), upper-soil-water proxy (m³ m⁻³) and temperature (°C). Coverage is expressed against the threshold-defined mask: GOOD windows 97.33%, W09 53.55%. W09's equivalent stable-core coverage is 55.0215%. W03 has blank EO fields and retained climate context; it is not interpolated. Median values do not include a confidence interval.

## Table 2 — GOOD-window temporal correspondence

Pearson and Spearman correlations between trait and index spatial-median trajectories across exactly eight GOOD windows. Correlations are dimensionless. W03 and W09 are excluded. These shared-Sentinel-2 comparisons quantify correspondence rather than independent validation; n is windows, not pixels.

## Table 3 — GOOD-window spatial correspondence

Minimum, median and maximum within-window spatial Pearson and Spearman coefficients for each trait–index pair across eight GOOD windows, with the windows attaining Pearson extrema. Spatial coefficients use up to 10,000 valid pixels per window under the frozen random sampling scheme. Coefficients are dimensionless; extrema summarize windows, not confidence limits. Comparisons use common valid agricultural support and are not independent accuracy tests.

## Table 4 — Relative-uncertainty sensitivity

Retention percentages, trait-median percentage shifts and filtered spatial Pearson coefficients for RU <20%, <30% and <40%, summarized across GOOD windows. `retention_*` is relative to the valid trait/index baseline, whereas `median_agricultural_domain_retained_pct` is relative to the full threshold mask. Maximum and median absolute shifts are different summaries; the largest reported shift is laiCw at RU <20%. Some summaries omit non-finite values where a filtered sample is insufficient. Thresholds are sensitivity treatments, not validated quality cutoffs. W03 and W09 are excluded.

## Table 5 — Robustness checks

Summary of mask-threshold sensitivity, fixed spatial support, W09 coverage and RU selection effects. Mask area percentages use the driver-valid grid; supported-footprint percentages use the threshold mask; W09 coverage uses the stable core. Normalized MAD is the mean absolute trajectory difference divided by the baseline seasonal range, multiplied by 100. Small rounded values (including 0.0000%) do not imply exact zero; the register preserves precision. Robustness is limited to the tested treatments.

## Table 6 — EO–hydroclimate associations

Pearson and Spearman correlations across eight GOOD windows between EO spatial-median trajectories and P15 (window rainfall, mm), Pprior30 (antecedent 30-day rainfall, mm), SM0_28 (upper-soil-water proxy, m³ m⁻³) and T2m (2-m temperature, °C). Coefficients are dimensionless. W03 and W09 are excluded. These raw environmental associations are confounded by seasonal crop development and do not measure irrigation or establish causation.

All six CSVs are in [the locked evidence directory](../outputs/final_evidence/step20a/). Numerical precision differs between rounded presentation tables and the full-precision evidence register.
