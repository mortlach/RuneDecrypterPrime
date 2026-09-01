# V1 review pack contract

`tools/release_review_pack.py` builds the standard lightweight ZIP used for external and cross-chat review of the V1 repository state.

The review pack is not a release artifact and is not intended for installation. Its purpose is to make code, tests, docs, workflow gates, and small import-critical files visible without copying generated output or large data assets.

## Included by default

The pack includes small files from:

- `src/`
- `tests/`
- `docs/`
- `tutorials/`
- `solving/`
- `cipher_development/`
- `tools/`
- `.github/workflows/`

It also includes only allow-listed root files:

- `AGENTS.md`
- `README.md`
- `CHANGELOG.md` if present
- `LICENSE` / `LICENSE.txt` if present
- `pyproject.toml`
- `pytest.ini`
- `setup.py`
- `MANIFEST.in`
- `requirements.txt`
- `install.py` and platform launcher scripts
- `assets_manifest_v1.json`
- `.gitignore`

Root repair/apply/patch/temp scripts are not included just because they are small text files. If a new root file is review-critical, add it deliberately to the allowlist and update the tests.

The manifest field `root_file_selection` must be:

```text
strict_root_allowlist_filtered_by_review_pack_rules
```

Tracked small tooling is included so reviewers can inspect release, install,
robustness and evidence-generation behaviour. The pack generator itself,
`tools/release_review_pack.py`, is therefore also visible.

Small `src/.../data/...` files are allowed when they pass the suffix and size filters. This is deliberate: small import-critical files such as baseline registries should not disappear from review packs just because they live below a `data` directory.

## Excluded by default

The pack excludes bulky or generated material, including:

- `output/`
- `assets/`
- `planning/`
- caches such as `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- build/dist/virtualenv directories
- archives, compressed files, binary/native files, images, NumPy blobs, and wheel files
- files larger than the configured size cap, currently 256 KiB by default

## Manifest and summary

Every pack contains:

- `REVIEW_PACK_README.md`
- `REVIEW_PACK_MANIFEST.json`

The manifest lists included files, excluded entries, roots, suffix filters, and the size cap.

When run as a script, the tool writes the ZIP under:

`output/tools/release_review_pack/`

and writes a sibling `.summary.json` file with counts and output paths.

## Contract

A V1 review pack must be small enough to share and inspect, but complete enough to review the active V1 source, contract docs, tests, workflow gates, and tutorial entry points.

If a future hardening stage adds a new review-critical small-file area, this tool and its tests should be updated rather than falling back to ad hoc source-only ZIPs.
