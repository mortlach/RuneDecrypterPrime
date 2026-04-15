# Benchmarks Folder

Benchmark runners, fixtures, solve-proof logs, and community harness tools.

## Current benchmark structure

- `tools/benchmarks/periodic_sub_trans/` active periodic substitution + transposition runners.
- `tools/benchmarks/solve_proof/` shared fixture/profile files and append-only solved history.
- `tools/benchmarks/community/` campaign validation/manifest/sharding/aggregation tools (including tamper-evident run-bundle integrity chain checks).
- `tools/benchmarks/config/` shared benchmark config resources.

## Canonical periodic_sub_trans entrypoints

- `python tools/benchmarks/bench_solve_periodic_columnar_pipeline_no_wli.py`
- `python tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
- `python tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py`

## Utility entrypoints

- `python tools/benchmarks/zip_src_nobloat.py`
  - Creates a lightweight zip of `src/` preserving structure while excluding noise:
    `data/`, `__pycache__/`, compiled extension artifacts, and large split/binary blobs.
- `python tools/get_src_extended_review_bundle.py`
  - Creates a reviewer bundle with source, benchmark pipeline code,
    `planning/projects/no_wli/`, and No-WLI output artifacts, while excluding caches,
    large binary blobs, and old nested review-pack folders.
- `python tools/benchmarks/tidy_output_root.py`
  - Moves loose root-level timestamped benchmark output folders into canonical output homes,
    writes `output/tools/benchmarks/root_tidy_manifest.json`, and updates
    `output/tools/benchmarks/ROOT_LAYOUT.md`

## Flavor-local implementations (advanced)

- `python tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `python tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
- `python tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`

## Output roots

Canonical top-level output roots under `output/tools/benchmarks/` are:

- `community/`
- `periodic_sub_trans/`
- `scoring/`
- `zip_src_nobloat/`
- `solve_proof/`
- `analysis/`

Loose timestamped root-level folders should be tidied into those roots rather than left directly under `output/tools/benchmarks/`.

