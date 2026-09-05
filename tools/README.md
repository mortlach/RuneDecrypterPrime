# Repository tools

[`run_validation.py`](run_validation.py) runs tests, ordinary tutorials/examples,
and solved LP workbooks from one entry point. It supports smoke and full selections;
see [selection and logging](run_validation.md) for the full run.

These utilities maintain assets, prepare evidence and support release work. `assets/`
handles asset profiles and bundles; `ci/` contains installed-package checks; `data/`
builds corpus fixtures; `get_src_zip/` prepares source archives; `robustness/` runs
explicit campaigns. The root `release_review_pack.py` prepares review evidence and
`refresh_two_period_fixture_manifest.py` maintains its named fixture record. These tools
are repository utilities, not part of the installed public API.

Continue with the [related guide](../docs/README.md).

Run `python tools/run_gpu_validation.py` for CUDA provisioning and strict GPU verification.
