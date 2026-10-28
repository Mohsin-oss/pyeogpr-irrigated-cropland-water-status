# Portfolio materials

## Short project description

I developed a reproducible Python and Google Earth Engine workflow to examine seasonal vegetation-water dynamics in irrigated cropland near South Jaranwala, Punjab, Pakistan. The project used Sentinel-2 and PyEOGPR to retrieve leaf water content, canopy water content and leaf area index, retaining native model uncertainty. It compared these traits with NDVI and NDMI and added CHIRPS rainfall and ERA5-Land environmental context. The analysis explicitly separated missing and limited observations, tested agricultural-mask thresholds and checked stable spatial support. A central finding was that hard relative-uncertainty filtering could retain very little agricultural area and substantially shift trait medians. The project therefore emphasizes transparent uncertainty reporting and reproducible evidence, while recognizing that satellite agreement does not constitute field validation of water stress.

## CV entry

**Uncertainty-aware Sentinel-2 cropland monitoring — independent research project, 2026**

- Developed a Python/GEE workflow for PyEOGPR vegetation water-related traits, native uncertainty, NDVI/NDMI and hydroclimatic context over an 89.44 km² retrieval-supported agricultural domain.
- Audited observation coverage, preserving a missing window and excluding limited coverage from eight-window primary temporal comparisons.
- Evaluated agricultural-mask thresholds and stable spatial support; documented strong seasonal canopy-trait/index correspondence without claiming independent validation.
- Quantified severe selection effects from hard relative-uncertainty filtering and produced traceable evidence tables, reproducibility documentation and scientific figures.

## Erasmus/WAVES application description

My research project on irrigated cropland in Punjab connects spatial water science with Earth observation and hydroinformatics. I developed a Python and Google Earth Engine workflow to retrieve vegetation water-related traits from Sentinel-2 using PyEOGPR, compare their seasonal behavior with conventional vegetation indices, and place the observations alongside rainfall, temperature and a broad soil-water proxy. The work required attention to spatial reference systems, agricultural-domain definition, temporal compositing and incomplete satellite coverage.

The most instructive part was uncertainty analysis. Rather than assuming that a relative-uncertainty threshold identifies reliable observations, I evaluated its consequences for retained area and trait distributions. Hard filtering could substantially change the seasonal sample, which led me to retain native absolute model uncertainty as a continuous output. I also tested nearby mask thresholds and common spatial support to distinguish changes in vegetation trajectories from changes in the sampled domain.

This project strengthened my ability to build reproducible geospatial analyses and communicate their limits. It is a completed research-project analysis with documented evidence, not a claim of field-validated water stress or a peer-reviewed publication. It motivates further training in spatial water processes, uncertainty assessment and integration of satellite observations with field hydrology.

## GitHub repository description

Reproducible Sentinel-2/PyEOGPR analysis of seasonal vegetation water-related traits in Punjab cropland, including native uncertainty, mask and spatial-support checks, index comparisons and hydroclimatic context; no field-validation claim.

## Suggested LinkedIn project description

Built an uncertainty-aware Sentinel-2/PyEOGPR workflow for seasonal cropland monitoring in Punjab, Pakistan. The project combines vegetation-trait retrievals, NDVI/NDMI comparisons, observation-coverage checks and broad hydroclimatic context. A key result was that hard relative-uncertainty filtering can substantially alter the retained sample and trait medians. The research archive documents the evidence, methods and limits; independent field validation remains future work.

## Recommended portfolio figures

- **Figure 10 — study-area locator:** establishes geographic relevance immediately. Its detailed panel shows the 91.89 km² threshold mask; explain that the analysis footprint is 89.44 km².
- **Figure 1 — seasonal traits:** communicates the scientific observations, spatial variation, missing window and limited coverage in one view. Shading is spatial IQR.
- **Figure 4 — RU selection effects:** shows the project's methodological contribution through retention loss and median shifts. Thresholds are sensitivity treatments, not validation criteria.

Use the full captions from [captions.md](captions.md). Keep the project status as research project/manuscript in preparation; no submission or acceptance is asserted.
