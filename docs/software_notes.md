# PyEOGPR implementation and provenance

Upstream: https://github.com/emmadcle/pyeogpr, commit `7c470644f33cc08ca934e0e44f3808b17aaf07f5`. The local editable checkout is `external/pyeogpr`; it is not vendored in this repository. The original environment records remain locally preserved.

Three reproducibility changes in `pyeogpr/gee_processing.py` are captured in [the exact patch](pyeogpr_local_patch.diff):

1. Download models from the pinned active repository instead of the unavailable former URL, and call `raise_for_status()`.
2. Replace Sentinel-2 per-band `.max()` temporal compositing with `.mean()`.
3. Expose `scene_cloud_threshold` (default 40); production scripts explicitly use 80 with a strict less-than filter.

No model coefficients, training data, GPR algorithm, trait definitions, uncertainty equations, spectral bands or pretrained hyperparameters were changed. The Sentinel-3 pathway was not changed. PyEOGPR's package imports openEO modules even when using Earth Engine, which explains the openEO/scipy/xarray dependencies.

During finalization the earlier saved diff was found to have stale constructor indentation. The diff was regenerated directly from the working checkout. This repairs the reproduction artifact, not the scientific implementation. The previous diff is retained locally in `tmp/finalization/originals`.

Python 3.14.6 was observed in the working environment. `requirements.txt` records installed versions of direct workflow and package-import dependencies, including matplotlib, which was absent from the older production freeze. This is an observed environment specification; a fresh installation has not been tested. Version availability and compiled geospatial wheels may differ across platforms.
