# D5 report and artifact agreement contract

D5 closes the V1 review and export contract for run outputs. It does not add solver features, cipher modes, scorer lanes, assets, or ranking behaviour.

## Contract boundary

The V1 output contract has two layers:

- **Artifact agreement**: the source-backed list of artifacts V1 knows how to review and export.
- **Run artifact manifest**: the small per-run record of which known artifacts were actually written.

The agreement is intentionally not a filesystem crawler. Logs, traces, raw assets, caches, output trees, and bulky runtime indexes are outside the V1 export candidate set unless a later release explicitly adds and tests them.

## V1 agreement rows

The V1 agreement names these run-relative POSIX paths:

| Path | Kind | Required by agreement | Listed in manifest | Review required |
| --- | --- | --- | --- | --- |
| `META.json` | `run_meta` | yes | yes | yes |
| `config/logging.json` | `logging_config` | yes | yes | yes |
| `artifacts/solver_report.json` | `solver_report` | no | yes, when present/requested | yes |
| `artifacts/run_artifacts_manifest.json` | `run_artifacts_manifest` | yes once manifest writing is requested | no, because the manifest is the output document | yes |

The manifest does not list itself as an input row. It lists only agreement rows that can exist before the manifest is written.

## Path and export policy

D5 keeps the export surface small and reviewable:

- paths must be run-relative;
- paths must use POSIX separators;
- absolute paths are rejected;
- parent-directory escapes are rejected;
- duplicate paths and duplicate artifact kinds are rejected;
- logs, traces, caches, assets, output trees, and large binary or index formats are not V1 export candidates by default.

## Solver report detail contract

Solver reports remain JSON-safe review artifacts. D5 adds explicit detail sections for:

- `report_contract`;
- `oracle_use`;
- `truth_data_policy`;
- `reproducibility`;
- `scorer_lanes`, when emitted by solver/scorer capability reporting;
- stop-reason details from the V1 stop-reason contract.

Known-key, tutorial, and test-key routes must not look like ordinary oracle-free production solves. They are reported with `oracle_use` and `truth_data_policy` details.

## Reproducibility metadata

The D5 reproducibility block is deliberately compact:

- deterministic seed policy;
- requested seed;
- effective seed;
- solver name.

It does not include local absolute paths, hashes, mtimes, byte sizes, or environment dumps.

## Report-only scorer contract

Report-only scorer lanes are diagnostic. They may appear in reports, but they must not affect score, raw score, ordering, or tie-breaks.

## D5 acceptance gate

D5 is acceptable only when:

- artifact agreement tests pass;
- manifest/agreement alignment tests pass;
- solver-report truth-data and reproducibility tests pass;
- scorer report reserved-detail tests pass;
- report-only no-rank-effect tests pass;
- D5 docs and handoff tests pass;
- full-proof CI passes on the final branch head.

## Generated solver-report details

`report_contract`, `oracle_use`, `truth_data_policy` and `reproducibility` are
reserved generated sections. Caller-provided details must not overwrite or pre-seed
these sections. Ordinary additional details remain supported.
