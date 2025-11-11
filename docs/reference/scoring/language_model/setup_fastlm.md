# `scoring/language_model/setup_fastlm.py`

> Purpose: developer utility script used to build/install the optional `_fastlm` C++ extension. Copies the compiled `.pyd`/`.so` into the package so scorers can import the accelerated routines.

## Workflow
- `find_repo_root(start)` - Walks up the filesystem to locate the repo root (used when the script is run from arbitrary directories).
- `_ensure_default_args()` - Populates setuptools command arguments if not provided.
- `_dest_ext_suffix()` - Determines the platform-specific extension suffix.
- `_copy_built()` - Copies the built `_fastlm` binary into `scoring/language_model/` next to the source.
- `_try_import()` - Verifies the module can now be imported.
- `main()` - Orchestrates the steps above; invoked when running `python setup_fastlm.py`.

Not part of the runtime API; only relevant for contributors building local wheels.

