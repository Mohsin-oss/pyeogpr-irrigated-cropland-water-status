# Final scientific consistency audit — 28 October 2026

## Result

PASS for the archived numerical evidence and finalization checks. No scientific thresholds, pretrained models, retrieval results, window statuses or original evidence files were changed. This is a reproducibility/consistency assessment, not independent physical validation.

## Evidence verification

- Reran the existing Step 20A audit against local inputs with only its output directory redirected to `tmp/finalization/audit_recheck`.
- The audit reported **no errors**. Its existing warning about 6,129 threshold-mask pixels outside the retrieval footprint remains applicable.
- All eight regenerated evidence files (six tables, register, audit) matched the original files **byte for byte**.
- The additional read-only verifier passed 77 checks covering hashes, window status, area arithmetic, correlation values recalculated from rounded medians, source syntax and local documentation links.
- Original evidence hashes are in `evidence_checksums.json`; Git attributes preserve those bytes across platforms.

## Claim review

Reviewed the report, README, executive summary, portfolio text and captions against the locked tables/register and source scripts. Verified areas and denominator distinctions, all quoted trait medians and correlation values, W03 missingness, W09 exclusion from temporal correlations, eight GOOD windows, RU threshold treatment and units, spatial-IQR interpretation, non-causal hydroclimate wording, dates and figure paths. Table 1's W09 coverage of 53.55% uses the threshold mask; 55.0215% uses the stable core. Table 4's maximum median shift and Figure 4's median shift are distinct statistics. Spatial correlations use the established sampling scheme, not every pixel.

The nominal April 15 boundary and implemented April 14 end-exclusive final production window are disclosed. No additional date or interpolation was introduced. Historical early scripts/logs are retained and explicitly excluded from the reproduction sequence. The obsolete mask-driver v1 is not a source for final results.

## Figures and dependency patch

Visually inspected all ten final figures and reinspected the four redrawn spatial/locator figures. Figures 7 and 10 now identify the threshold-defined mask; Figures 8 and 9 clarify that white pixels may lack valid retrievals. Shared 2nd–98th percentile color limits remain unchanged. W07 uses the high-canopy label. The stale saved PyEOGPR diff was regenerated from the actual working checkout and applied to a clean copy of the pinned upstream file; it reproduced the working source exactly after line-ending normalization and passed syntax parsing.

## Repository and privacy

The root had no Git metadata. An existing matching private GitHub repository was discovered, containing an initial Apache-2.0 license commit. The finalization branch preserves that history and license. No duplicate repository was created and no visibility change was requested. The staged payload was reviewed for private keys, token patterns, credential JSON fields, local project identifier, unnecessary user paths and excluded file types. It contains about 14.8 MB, with no rasters, environments, credentials or caches. The nested upstream repository is documented and ignored.

## Remaining limits

Fresh environment installation and new cloud retrieval/export runs were not performed. Pixel-level reproduction requires the locally retained rasters or authorized cloud exports. A clean Git archive was extracted separately: its verification passed all 77 checks and its core-figure script regenerated all six figures successfully from the included supporting CSVs using the existing Python environment. The study remains unvalidated against field measurements, and no journal publication status is claimed. External data and software retain their own licenses.
