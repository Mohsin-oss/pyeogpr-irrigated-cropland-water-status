# Repository audit — 28 October 2026

The root was not a Git repository. The nested external/pyeogpr checkout is a dependency, not an intended project remote; its history remains untouched. Inventory: 338 non-environment/non-cache files, 245.17 MB before finalization. No credential-pattern or personal-user-path hits were found in the scanned project text files. This scan is a bounded check, not a guarantee about arbitrary binary content.

Final evidence: outputs/final_evidence/step20a (six tables, register, original audit). Final figures: figures/final_core, figures/spatial_final, figures/locator. Supporting numerical tables: outputs/analysis and outputs/hydroclimate. Source: numbered src scripts, with config/study_config.py holding study settings. Original evidence hashes were recorded before edits; original scientific files are preserved.

Intermediate and diagnostic material: early smoke/coverage/cloud tests, production/raw, indices/raw, QA/manifests, figures/core and figures/spatial. Failed mask-driver v1 is obsolete: src/16a_export_agricultural_mask_drivers.py and outputs/mask/agricultural_mask_drivers_20251115_20260415.tif. Use the v2 driver export and the current 16b/16c pathway. Historical logs and experimental scripts must not be read as final methods.

Excluded from publication: .venv, caches, local config/project_config.py, generated model_imported.py, nested upstream checkout, rasters, archives, unrelated CV/application files, local publisher PDF, diagnostic outputs and temporary backups. All remain locally available. Public example config contains no project identifier. The matching existing private GitHub repository was found and its Apache-2.0 license and initial history are retained.

Corrections: Figure 7 and Figure 10 show the threshold-defined 91.89 km² mask, so their labels were corrected without changing the mask. Maps retain existing color scales. The saved dependency patch had stale constructor indentation; it was regenerated from the actual working checkout, without changing dependency code. Previous versions are preserved under ignored tmp/finalization/originals.

Temporal disclosure: the nominal study boundary is 15 April 2026, but the ten production windows end at 14 April (exclusive). The final one-day remainder is not analyzed. No new window or experiment was introduced.
