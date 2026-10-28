# Reproducing the archived analysis

## Scope

The repository contains code, small supporting tables, locked final evidence and figures. Large raw and processed rasters, credentials and the nested upstream repository remain local. The tables can be inspected without Earth Engine. Full pixel-level reproduction requires the raster inputs or authorized Earth Engine/Drive exports. No new retrieval experiments were run during finalization.

## Setup (PowerShell, project root)

```powershell
$env:PYTHONIOENCODING='utf-8'
py -3.14 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
git clone https://github.com/emmadcle/pyeogpr.git external/pyeogpr
git -C external/pyeogpr checkout 7c470644f33cc08ca934e0e44f3808b17aaf07f5
git -C external/pyeogpr apply --check ../../docs/pyeogpr_local_patch.diff
git -C external/pyeogpr apply ../../docs/pyeogpr_local_patch.diff
.venv/Scripts/python.exe -m pip install -e external/pyeogpr
Copy-Item config/project_config.example.py config/project_config.py
```

Set your own Earth Engine-enabled project in the ignored local config. Authenticate through the normal Earth Engine login flow (`.venv/Scripts/earthengine.exe authenticate`). Never place tokens in source files. Existing local users should not reclone or reapply an already-applied patch.

## Review the archived evidence without cloud access

```powershell
.venv/Scripts/python.exe scripts/verify_finalization.py
.venv/Scripts/python.exe src/19b_refine_core_figures.py
```

The second command redraws Figures 1–6 from the published supporting CSVs. The verification script is read-only for scientific evidence. `docs/evidence_checksums.json` identifies the locked original evidence bytes.

## Rebuild from existing local rasters

Run only in a separate reproduction copy if preserving original output bytes is required. Numbered scripts write their outputs in place.

```powershell
.venv/Scripts/python.exe src/17a_integrated_seasonal_analysis.py
.venv/Scripts/python.exe src/17b_uncertainty_sensitivity.py
.venv/Scripts/python.exe src/17c_stable_spatial_support.py
.venv/Scripts/python.exe src/18b_integrated_hydroclimate_analysis.py
.venv/Scripts/python.exe src/19b_refine_core_figures.py
.venv/Scripts/python.exe src/19c_v2_create_spatial_figures.py
.venv/Scripts/python.exe src/20a_final_evidence_audit.py
```

Required local inputs are the corrected mask at `outputs/mask/agricultural_mask_C25_N40_final.tif`, cleaned six-band retrievals in `outputs/production/final/`, aligned indices in `outputs/indices/final/`, mask QA CSVs/manifest and hydroclimate tables. The source register contains original absolute paths for provenance; scripts resolve paths relative to the project root.

## Cloud/export pathway (documented, not rerun)

1. `14b_export_full_season.py`: submit retrieval exports with the frozen window statuses; download completed Drive GeoTIFFs into `outputs/production/raw/` with the expected filenames.
2. `14c_batch_sanitize_validate.py`: sanitize/validate the production exports.
3. `15a_export_ndvi_ndmi_season.py`: export aligned indices; download to `outputs/indices/raw/`; run `15b_validate_ndvi_ndmi_season.py`.
4. `16a_v2_export_agricultural_mask_drivers.py`: export corrected drivers, retaining their source projection and aggregating 10 m to 20 m; download the `_v2.tif` driver to `outputs/mask/`.
5. `16b_agricultural_mask_sensitivity.py`, then `16c_create_final_agricultural_mask.py`: reproduce the frozen threshold selection. Never use v1 drivers.
6. `18a_extract_hydroclimate.py`: extract contextual time series; then run local analysis in the order above.
7. `19d_create_study_area_locator.py`: regenerate the locator using Earth Engine FAO GAUL simplified 2025 boundaries; requires cloud access.

See each script's filename patterns and export folders before downloading. Export submission is asynchronous and is not equivalent to completed download. The early scripts 01–13, pilot 14a scripts, 16b1, and original 19a/19c are historical diagnostics, not an alternative final workflow.

## Temporal boundary and status

Production windows are start-inclusive, end-exclusive. The nominal study extent is 2025-11-15 to 2026-04-15. Ten complete 15-day windows end at 2026-04-14; the remaining one-day interval is not analyzed. W03 is missing and never filled. W09 is limited and descriptive only. This boundary disclosure does not change the frozen design.

## Licensing and availability

Preserve the existing GitHub repository's license. Upstream software and data retain their own licenses; the project's license does not relicense them. A public raster archive and DOI have not been established. Exact pixel-level reproduction from this small repository alone is therefore not available. The source and evidence are a research-project archive, not a peer-reviewed publication.
