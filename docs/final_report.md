# Uncertainty-Aware Retrieval of Vegetation Water Traits from Sentinel-2 for Irrigated Cropland Monitoring in Punjab, Pakistan

Mohsin Ahmad · Research-project manuscript · 28 October 2026

## Abstract

Satellite-derived vegetation traits can describe seasonal agricultural dynamics, but their interpretation requires attention to observation coverage and model uncertainty. This study examined Sentinel-2/PyEOGPR retrievals of leaf equivalent water content (Cw), canopy water content (laiCw) and leaf area index (LAI) over South Jaranwala / Buchiana, Faisalabad District, Pakistan. Ten fixed 15-day windows were defined within the nominal November 2025–April 2026 season; eight were GOOD, one was MISSING and one had LIMITED coverage. The primary domain comprised 223,600 retrieval-supported agricultural pixels (89.44 km²), or 97.33% of the threshold-defined C25-N40 mask. Across GOOD windows, laiCw corresponded strongly with NDVI and NDMI (Pearson r = 0.9833 and 0.9617), while Cw–NDMI spatial correlations varied from 0.2810 to 0.8646. Nearby mask thresholds and fixed spatial support produced small changes in seasonal trajectories. Conversely, hard relative-uncertainty filtering strongly reduced retained area and shifted trait medians, with a maximum absolute shift of 1427.70% for laiCw under RU <20%. These findings support reporting native absolute uncertainty continuously rather than using a universal RU threshold. Index comparisons reflect shared Sentinel-2 information, and hydroclimate provides context rather than independent validation. No field-validated crop water stress or irrigation deficit is inferred.

**Keywords:** Sentinel-2; PyEOGPR; vegetation water traits; Gaussian process regression; uncertainty; irrigated cropland; Punjab.

## 1. Introduction

Seasonal vegetation development changes both canopy structure and water-related optical properties. For irrigated agricultural landscapes, satellite observations offer repeated spatial coverage, but an observed vegetation signal cannot by itself identify irrigation supply, physiological stress or a causal water deficit. A defensible monitoring workflow must distinguish retrieval behavior from field validation and make cloud-related observation gaps visible.

PyEOGPR makes pretrained Gaussian process regression models available for mapping vegetation traits using Earth observation cloud platforms [1]. Its native uncertainty outputs provide an opportunity to examine the reliability information accompanying trait estimates. They also raise a practical question: does a simple relative-uncertainty cutoff improve interpretability, or does it select a different subset of the seasonal vegetation distribution?

This study asks whether PyEOGPR water-related traits characterize seasonal cropland dynamics, how their temporal and spatial patterns correspond with NDVI and NDMI, and whether conclusions are sensitive to agricultural-mask thresholds, spatial support and RU filtering. It is an observational case study. It does not test retrieval accuracy against independent field measurements.

## 2. Study area and temporal extent

The study covers the South Jaranwala / Buchiana agricultural landscape in Faisalabad District, Punjab, Pakistan, within 73.408–73.513° E and 31.205–31.295° N. The approximate center is 31.250° N, 73.4605° E. Figure 10 locates the area within Pakistan, Punjab and Faisalabad; its detailed panel depicts the threshold-defined agricultural mask.

The nominal study season is 15 November 2025–15 April 2026. The implemented production design uses ten complete 15-day windows. Their final end-exclusive boundary is 14 April 2026, so the final one-day remainder of the nominal extent is not included. This distinction is retained rather than extending the frozen analysis retrospectively. Windows and observation status are recorded in the accompanying captions and final evidence tables.

## 3. Data

Sentinel-2 harmonized Level-1C top-of-atmosphere reflectance (`COPERNICUS/S2_HARMONIZED`) supplies the PyEOGPR pathway and comparison indices [2]. The traits are Cw (cm), laiCw (g m⁻²) and LAI (m² m⁻²), each with native absolute GPR uncertainty in the corresponding trait unit. The outputs are represented on a 20 m grid in UTM zone 43N (EPSG:32643).

Dynamic World (`GOOGLE/DYNAMICWORLD/V1`) supplies repeated land-cover classifications for agricultural-mask drivers [3]. CHIRPS daily precipitation (`UCSB-CHG/CHIRPS/DAILY`) supplies rainfall context [4]. ERA5-Land daily aggregates (`ECMWF/ERA5_LAND/DAILY_AGGR`) supply upper-soil-water and temperature context [5]. The latter datasets have much coarser spatial support than the EO grid; they do not provide field irrigation records.

## 4. Methods

### 4.1 Reflectance processing and retrieval

The production scene filter is `CLOUDY_PIXEL_PERCENTAGE < 80`. QA60 bits 10 and 11 are used for pixel cloud masking. Mean reflectance is composited within each fixed window before retrieval. The primary analysis uses no spatial or temporal interpolation. Mean composites reduce within-window observations to one spectral representation; the resulting retrieval is not necessarily the mean of individually retrieved scene traits.

The local PyEOGPR checkout uses upstream commit `7c470644f33cc08ca934e0e44f3808b17aaf07f5`. Three transparent reproducibility patches update the model-download location and HTTP error handling, replace Sentinel-2 maximum compositing with mean compositing, and expose a configurable scene-cloud threshold. Model coefficients, GPR algorithms, trait definitions, uncertainty equations, spectral bands and pretrained parameters were not modified. The exact working diff is archived in `docs/pyeogpr_local_patch.diff`.

### 4.2 Agricultural domain and spatial support

C25-N40 requires Dynamic World crop frequency ≥0.25, seasonal maximum NDVI ≥0.40, built-up frequency <0.20 and water frequency <0.20. The threshold-defined mask contains 229,729 pixels (91.8916 km²). The primary analysis uses **223,600 retrieval-supported agricultural pixels (89.44 km²), representing 97.33% of the 91.89 km² threshold-defined C25-N40 agricultural mask**. The remaining 6,129 mask pixels are outside the common GOOD-window retrieval footprint.

The first driver export was invalid because an ImageCollection reduction lost the intended projection and produced spatially constant driver values. It is obsolete. The corrected v2 workflow restores the source projection, uses `reduceResolution` for 10 m to 20 m aggregation, and avoids inappropriate composite resampling. The final mask sensitivity script points explicitly to this v2 driver.

Nine nearby threshold combinations assess local sensitivity of seasonal trajectories. Normalized MAD is the mean absolute trajectory difference divided by the baseline seasonal range, expressed as a percentage. A separate stable-support analysis intersects valid observations across GOOD windows to assess whether changing pixel support explains the seasonal patterns. These checks assess robustness within the tested design, not agricultural-classification accuracy.

### 4.3 Observation status and statistical summaries

W01, W02, W04, W05, W06, W07, W08 and W10 are GOOD. W03 is MISSING and contains no interpolated EO values. W09 is LIMITED and covers 55.0215% of the stable GOOD-window core. It is displayed descriptively but excluded from primary temporal correlations. Its coverage against the larger threshold-defined mask is 53.55%, as reported in Table 1.

Within-window spatial medians and interquartile ranges summarize the agricultural domain. Pearson and Spearman coefficients describe temporal correspondence across the eight GOOD-window medians and spatial correspondence within GOOD windows. Spatial correlations use up to 10,000 sampled valid pixels per window, with the established seed schedule (base seed 42); RU comparisons use up to 10,000 pixels with base seed 1702 and the existing window/trait/threshold offsets. Neither sampling scheme was changed. Spatial summaries of correlation coefficients across windows are distinct from a pooled pixel correlation. Standardized trajectories use means and standard deviations calculated from GOOD windows only; W09 is transformed using those parameters without influencing them.

### 4.4 Uncertainty sensitivity

Native absolute GPR uncertainty is the primary uncertainty representation. It is a model output, not a confidence interval for an area-wide seasonal median. Spatial IQR describes variation among pixels and must not be labeled model uncertainty.

Relative uncertainty divides native uncertainty by predicted trait magnitude; the sensitivity code requires positive predictions and non-negative uncertainty. Hard RU thresholds of <20%, <30% and <40% were tested only as sensitivity treatments. The analysis compares retained fractions, trait-median shifts and correlations under these selections. No threshold is designated a validated retrieval-quality criterion, and none is imposed on the primary analysis. Because the denominator varies with trait magnitude, a relative cutoff may preferentially exclude low-magnitude retrievals even where absolute uncertainty changes little.

### 4.5 Environmental context

CHIRPS provides within-window rainfall totals and preceding 30-day rainfall totals, summarized spatially over the study area. ERA5-Land provides mean 2-m temperature and a depth-weighted upper-soil-water proxy from its first two layers. Contextual hydroclimate remains available during W03 even though EO is missing. Concurrent correlations use only the eight GOOD EO windows. These raw correlations do not adjust for seasonal crop development or establish causal relationships.

## 5. Results

### 5.1 Seasonal behavior

Final Table 1 shows strong seasonal development in the retrieved canopy variables. W01 medians were 48.97 g m⁻² for laiCw and 0.275 m² m⁻² for LAI. Both reached their highest observed GOOD-window median in W07: 504.65 g m⁻² and 2.075 m² m⁻². Cw also reached its maximum reported median in W07, at 0.016005 cm. By W10, laiCw and LAI medians were 54.90 g m⁻² and 0.345 m² m⁻². These observations describe retrieved seasonal trajectories; they do not measure crop water stress.

NDVI and NDMI medians were highest in W08 (0.7811 and 0.3954), slightly later than the maximum PyEOGPR trait medians. W07 is therefore termed a high-canopy stage or the peak PyEOGPR-trait window, rather than an undifferentiated peak of all vegetation measures. W09's reduced spatial coverage prevents treating its descriptive decline as directly equivalent to the full-domain GOOD windows.

### 5.2 Trait–index correspondence

Across eight GOOD windows, temporal Pearson r was 0.9833 for laiCw–NDVI, 0.9617 for laiCw–NDMI and 0.9861 for LAI–NDVI (Table 2). Cw temporal correspondence was weaker, with r = 0.9110 for NDVI and 0.7819 for NDMI. The common seasonal development of canopy traits and vegetation indices is evident in Figure 5.

Spatial correspondence varied by trait and window. Cw–NDMI Pearson r ranged from 0.2810 in W04 to 0.8646 in W08 (Table 3). This variability indicates that leaf-level and canopy-level products do not have interchangeable spatial behavior. It does not demonstrate superior water-stress sensitivity or independent retrieval accuracy.

### 5.3 Robustness to mask and support

The nine mask combinations occupied approximately 88.54–89.70% of the driver-valid grid. Maximum normalized trajectory MAD was 0.3870%, and minimum trajectory Pearson correlation was approximately 1.0. Within this tested neighborhood, threshold changes did not materially alter the seasonal conclusions.

All eight GOOD windows shared the same effective retrieval-supported agricultural footprint. The maximum stable-support normalized MAD was approximately 0.000002% (the evidence register retains the more precise value). This supports the conclusion that the observed GOOD-window seasonal trajectories are not artifacts of changing spatial support. It does not remove selection introduced by cloud screening or the initial domain definition.

### 5.4 Relative-uncertainty selection effects

Table 4 shows severe retention loss and large shifts in trait medians. At RU <20%, median retained agricultural-domain fractions were 0.00% for Cw, 0.33% for laiCw and 0.04% for LAI (rounded). The largest absolute trait-median shift was 1427.70% for laiCw at RU <20%. This is a maximum across windows, not the median shift shown in the lower panel of Figure 4.

Even RU <40% retained median domain fractions of only 6.75% for Cw, 18.00% for laiCw and 7.14% for LAI. Thus a hard cutoff substantially changes which vegetation conditions contribute to the summary. Retention expressed against the threshold-defined agricultural domain differs from retention among valid baseline retrievals; Table 4 includes both denominators.

### 5.5 Hydroclimatic context

Concurrent rainfall correlations with the EO seasonal trajectories were weak in the final table. The strongest absolute raw environmental Pearson association was laiCw with the upper-soil-water proxy (r = −0.7476). Negative associations were also present for the other EO variables. These descriptive coefficients combine seasonal climate variation and crop development; no causal effect of soil wetness on vegetation water content is identified.

## 6. Discussion

The correspondence of laiCw and LAI with conventional indices indicates consistent seasonal information across Sentinel-2-derived products. Because the inputs are shared, high correlations cannot serve as independent validation. Canopy water content also combines canopy amount with leaf water-related properties, which helps explain why canopy variables can track greenness strongly without uniquely diagnosing water limitation. Cw's variable spatial association offers a different descriptive perspective, but its practical physiological meaning would require independent observations.

The RU experiment is a central methodological result. Dividing by a seasonal trait magnitude can make a fixed threshold select very different portions of the landscape at different times. The observed retention loss and median shifts demonstrate this selection effect in the present data. They do not show that every rejected pixel is inaccurate, nor that every retained pixel is valid. Continuous native absolute uncertainty, presented alongside trait magnitude and observation coverage, makes these distinctions more visible.

Mask and support tests strengthen the interpretation of the seasonal curves within the selected domain. Their scope is limited: nearby thresholds do not explore every plausible cropland definition, and stable coverage does not establish the correctness of the retrievals. The missing window remains a genuine information gap. Likewise, broad hydroclimate helps situate the season but cannot reconstruct canal deliveries or field irrigation schedules. Seasonal phenology is a plausible confounder of the raw negative soil-water associations; it was not causally isolated by this analysis.

## 7. Limitations

The analysis covers one landscape and one season, with only eight GOOD temporal observations. Temporal autocorrelation, spatial dependence and shared satellite inputs limit inferential independence. No field measurements of leaf water, canopy water, soil moisture, irrigation or physiological stress were used. Native uncertainty calibration and out-of-domain model performance were not independently assessed. QA60 cloud masking and mean compositing can retain residual contamination or smooth short-lived changes. The mask is threshold-defined rather than field-verified. Hydroclimate is coarse relative to fields, and W09 has incomplete support. Full reproduction requires excluded raster inputs or renewed cloud exports; the archived tables alone cannot validate every pixel-level calculation.

## 8. Conclusions

The retrieved canopy traits showed strong seasonal correspondence with Sentinel-2 indices, while Cw displayed more variable spatial relationships. Tested mask thresholds and fixed support had little effect on seasonal trajectories. Hard RU filtering caused substantial retention loss and magnitude-dependent shifts, supporting transparent continuous reporting of native absolute model uncertainty in this case. The study provides a reproducible framework for examining vegetation-water dynamics, with explicit boundaries on validation, causality and irrigation interpretation.

## 9. Reproducibility and data/code availability

The six locked tables, evidence register and original audit are in `outputs/final_evidence/step20a/`. Checksums preserve their original bytes. The report's numerical claims derive from these files and the source tables identified by the register. Source scripts, exact dependency patch, observed environment specification, captions and small supporting tables accompany this manuscript. Rasters, credentials and historical debug outputs remain local. See [reproduction instructions](reproducibility.md). This is a research-project manuscript with no claimed journal submission, acceptance or DOI.

## References

1. Kovács, D. G., De Clerck, E., & Verrelst, J. (2025). PyEOGPR: A Python package for vegetation trait mapping with Gaussian Process Regression on Earth observation cloud platforms. *Ecological Informatics*, 92, 103497. https://doi.org/10.1016/j.ecoinf.2025.103497. Bibliographic details verified against the [TU Wien repository record](https://repositum.tuwien.at/handle/20.500.12708/221119?mode=full).
2. Google Earth Engine Data Catalog. [Harmonized Sentinel-2 MSI, Level-1C (TOA)](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_HARMONIZED). Dataset documentation; accessed 28 October 2026.
3. Google Earth Engine Data Catalog. [Dynamic World V1](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1). Dataset documentation; accessed 28 October 2026.
4. Google Earth Engine Data Catalog. [CHIRPS Precipitation Daily](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY). Dataset documentation; accessed 28 October 2026.
5. Google Earth Engine Data Catalog. [ERA5-Land Daily Aggregated](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR). Dataset documentation; accessed 28 October 2026.

Dataset entries are documentation references, not fabricated journal citations. The locator credits FAO GAUL simplified 2025 administrative boundaries as specified by its generating script.
