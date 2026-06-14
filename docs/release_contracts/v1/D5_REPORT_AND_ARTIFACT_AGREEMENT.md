# D5 report and artifact agreement contract

D5 closes the V1 review and export contract for run outputs. It does not add solver features, cipher modes, scorer lanes, assets, or ranking behaviour.

The V1 output contract has two layers: an artifact agreement, which says which artifacts V1 can review and export, and a run artifact manifest, which says which known artifacts were written in a particular run.

Required agreement rows are `META.json`, `config/logging.json`, `artifacts/solver_report.json`, and `artifacts/run_artifacts_manifest.json`.

Paths must be run-relative and use POSIX separators. Absolute paths, parent-directory escapes, duplicate relpaths, duplicate artifact kinds, logs, traces, caches, raw assets, output trees, and large binary or index files are not V1 export candidates by default.

Solver report details include `report_contract`, `oracle_use`, `truth_data_policy`, `reproducibility`, `scorer_lanes` when available, and V1 stop-reason details. Known-key, tutorial, and test-key routes must be visible and must not look like ordinary oracle-free production solves.

The reproducibility block is compact: deterministic seed policy, requested seed, effective seed, and solver name. It does not include local paths, hashes, mtimes, byte sizes, or environment dumps.

Report-only scorer lanes are diagnostic. They may appear in reports, but they must not affect score, raw score, ordering, or tie-breaks.

D5 is acceptable only when the focused D5 tests and full-proof CI pass on the final branch head.
