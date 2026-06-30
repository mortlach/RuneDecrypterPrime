# Telemetry And Reports

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/api/run_result.py`
- `src/rune_decrypter_prime/api/solver_report.py`
- `src/rune_decrypter_prime/api/display.py`
- `src/rune_decrypter_prime/api/printer.py`
- `src/rune_decrypter_prime/api/artifact_agreement.py`
- `src/rune_decrypter_prime/api/run_artifact_manifest.py`
- `src/rune_decrypter_prime/scoring/scorer_report.py`
- `src/rune_decrypter_prime/scoring/scorer_report_builder.py`
- `src/rune_decrypter_prime/telemetry/`

Related tests:
- `tests/api/`
- `tests/contracts/`
- `tests/scoring/`
- `tests/telemetry/`
- `tests/docs/test_v1_coder_docs_contract.py`

Stability:
- Public V1 surface for API reports and known artifact paths.
- Semi-stable contributor surface for telemetry payload shape.
- Internal helper surface for report-builder diagnostics.

## Purpose

This page explains the runtime evidence surfaces: returned reports, scorer
reports, display summaries, telemetry blocks, and written artifact manifests.

The key rule is that evidence surfaces explain what happened. They must not
quietly change ranking, stopping, tie-breaks, or candidate selection.

## Evidence Surfaces

| Surface | Owner | Purpose | Contract notes |
| --- | --- | --- | --- |
| `RunResult` | `api/run_result.py` | Pairs a solution with its `SolverReport`. | The `solver_report` field must be a `SolverReport`. |
| `SolverReport` | `api/solver_report.py` | Records solver identity, seeds, normalized params, stop reason, best score/key, counters, timings, and details. | `build_solver_report` adds generated contract sections. |
| `ScorerReport` | `scoring/scorer_report.py` | Records scoring objective, score, raw score, telemetry, metrics, cost, and scorer details. | JSON conversion rejects non-finite floats and absolute `Path` values. |
| `RdpDisplaySummary` | `api/display.py` | Builds a stable-readable display/share summary. | This is not a resume or persistence format. |
| `RunArtifactManifestRow` | `api/run_artifact_manifest.py` | States which known run artifacts were present for a run. | Rows are validated against the V1 artifact agreement. |
| Telemetry blocks | `telemetry/` | Capture run, solver, scorer, and pipeline evidence. | Best-effort evidence, not a control plane. |

## Known Artifact Paths

The V1 artifact agreement currently knows these run-relative paths:

| Relpath | Kind | Required |
| --- | --- | --- |
| `META.json` | `run_meta` | Yes. |
| `config/logging.json` | `logging_config` | Yes. |
| `artifacts/solver_report.json` | `solver_report` | Optional. |
| `artifacts/rdp_display_summary.json` | `rdp_display_summary` | Optional. |
| `artifacts/run_artifacts_manifest.json` | `run_artifacts_manifest` | Yes, written after known artifacts are checked. |

Generated run artifacts belong under the configured run output directory. Do
not place generated reports, logs, caches, or benchmark outputs in `v1_docs/`.

## SolverReport Details

`SolverReport` is the main solver-side evidence object. It records:

- `solver_name`
- `requested_seed`
- `effective_seed`
- `normalized_params`
- `stop_reason`
- `best_score`
- `best_key`
- `step`
- `evals`
- `tokens_processed`
- `wall_time_s`
- `decrypt_time_s`
- `score_time_s`
- `details`

`build_solver_report` generates these detail sections:

| Detail key | Meaning |
| --- | --- |
| `report_contract` | Solver report detail schema marker. |
| `oracle_use` | Whether oracle or known-answer information was used. |
| `truth_data_policy` | Whether truth/test/tutorial data is present only as reported evidence. |
| `reproducibility` | Deterministic seed policy, requested seed, effective seed, and solver name. |

Contributor-supplied details may add sections such as `execution_route` or
`scorer_lanes`, but they must not overwrite generated contract sections.

## ScorerReport Details

`ScorerReport` is the scoring-side evidence object. It records:

- `objective_str`
- `objective_spec`
- `score`
- `raw_score`
- `telemetry`
- `metrics`
- `cost_ms`
- `details`

`scoring/scorer_report_builder.py` can derive these known detail sections:

| Detail key | Meaning |
| --- | --- |
| `hamming_dictionary` | Dictionary policy evidence from hamming telemetry. |
| `span_hamming` | Span-hamming telemetry grouped for report readability. |
| `span_lm` | Span language-model telemetry grouped for report readability. |
| `word_ngrams` | Word n-gram telemetry grouped for report readability. |
| `scorer_lanes` | Requested or active scorer lane evidence. |
| `stop_reason` | Reported stop reason evidence. |
| `stop_category` | Reported stop category evidence. |
| `oracle_use` | Reported oracle-use evidence. |
| `truth_data_policy` | Reported truth-data policy evidence. |
| `report_contract` | Scorer report detail schema marker when supplied. |
| `report_builder_diagnostics` | Builder errors captured without crashing report creation. |

Report-only scorer details can explain a decision. They must not become hidden
ranking, stopping, tie-break, or candidate-selection inputs.

## Report-Only And Oracle Boundary

Runtime scoring must be explicit about which signals affect production ranking.

Report-only fields can:

- explain a score
- expose diagnostics
- preserve stop reasons
- record requested lanes
- show whether oracle or truth data was present

Report-only fields must not:

- alter ranking
- alter stopping
- alter tie-breaks
- alter candidate selection
- make truth data influence production scoring

If oracle or truth data is used for a known-key fast path, test-key path, or
tutorial demonstration, the report must say so through `oracle_use` and
`truth_data_policy`.

## Telemetry Blocks

Telemetry is best-effort runtime evidence. The current helpers record:

- `run_start` and `run_end` in `telemetry/events.py`
- `solver_start`, `solver_progress`, and `solver_end` in `telemetry/events.py`
- `attach_telemetry_to_meta` in `telemetry/events.py`
- `make_pipeline_block` in `telemetry/pipeline.py`
- `finalize_run_meta` in `telemetry/pipeline.py`
- optional JSONL mirroring through `dump_telemetry`

Telemetry can be copied into solution metadata and can feed display/report
summaries. It is not a stable persistence format and should not be required for
solver correctness.

## Artifact Manifest Rules

`write_run_artifacts_manifest` writes `artifacts/run_artifacts_manifest.json`
for a run directory. It requires the run metadata and logging snapshot to
already exist:

- `META.json`
- `config/logging.json`

The manifest may list optional artifacts when present:

- `artifacts/solver_report.json`
- `artifacts/rdp_display_summary.json`

Manifest rows use run-relative POSIX paths. Absolute paths, backslash paths, and
paths that escape the run directory are invalid.

## Extension Checklist

When adding a new report, telemetry block, or artifact:

1. Decide whether it is a returned report, file artifact, telemetry field, or
   display-only summary.
2. If it is a file artifact, add it to the artifact agreement before relying on
   it in review/export code.
3. Keep paths run-relative and portable.
4. Keep report payloads JSON-safe and reject absolute local paths.
5. State whether each new signal affects ranking, stopping, tie-breaks, or
   candidate selection.
6. Add focused contract tests.
7. Update this page and `reference/public_api_allowlist.md` when the surface is
   public or semi-stable.

## What Not To Rely On

- Exact console text as a machine contract.
- Local absolute paths in reports or manifests.
- Telemetry as a resume format.
- Report-only fields as scoring controls.
- Unknown output files being portable or exportable by default.
