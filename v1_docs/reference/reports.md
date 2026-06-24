# Reports Reference

Status: staged V1 draft

Owners:

```text
src/rune_decrypter_prime/api/solver_report.py
src/rune_decrypter_prime/scoring/scorer_report.py
src/rune_decrypter_prime/api/display.py
```

## RunResult

Owner:

```text
src/rune_decrypter_prime/api/run_result.py
```

`RunResult` contains:

| Field | Meaning |
| --- | --- |
| `solution` | The solver solution object. |
| `solver_report` | A `SolverReport`. |

It is intentionally small.

## SolverReport

`SolverReport` records solver behavior.

| Field | Meaning |
| --- | --- |
| `solver_name` | Solver used. |
| `requested_seed` | Seed requested by the caller. |
| `effective_seed` | Seed actually used. |
| `normalized_params` | Solver parameters after normalization. |
| `stop_reason` | Why the solver stopped. |
| `best_score` | Best score found. |
| `best_key` | Best key found, when available. |
| `step` | Solver step count. |
| `evals` | Evaluation count. |
| `tokens_processed` | Token count. |
| `wall_time_s` | Wall-clock timing. |
| `decrypt_time_s` | Decrypt timing. |
| `score_time_s` | Score timing. |
| `details` | JSON-safe detail mapping. |

Generated detail sections include:

```text
report_contract
oracle_use
truth_data_policy
reproducibility
```

Callers cannot overwrite these generated sections.

## ScorerReport

`ScorerReport` records a scoring result.

| Field | Meaning |
| --- | --- |
| `objective_str` | Human-readable objective. |
| `objective_spec` | Structured objective. |
| `score` | Final score. |
| `raw_score` | Optional raw score. |
| `telemetry` | JSON-safe telemetry mapping. |
| `metrics` | Numeric metric mapping. |
| `cost_ms` | Scoring cost in milliseconds. |
| `details` | JSON-safe detail mapping. |

The report rejects unsafe JSON values such as non-finite floats.

## Display Summary

The display summary schema is:

```text
api_display_summary.v1
```

The display summary can include problem, cipher, key, solver, scoring, result,
solver report, scorer report, telemetry, stop, oracle, tutorial, LP evidence,
artifacts, and warnings.

It is a display/share layer, not a resume format for solver state.
