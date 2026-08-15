# V1 stop-reason contract

A4 extends the existing June `rdp.run_status_contract.v1` schema. Solver reports retain the established flat stop fields for compatibility and expose the canonical typed status under `details.run_status`.

Legacy flat fields remain:

- `stop_category`
- `stop_reason`
- `stop_detail`
- `blocked_before_run`
- `error_type`

Stable coarse categories remain:

- `success`
- `budget`
- `blocked_before_run`
- `error`
- `manual`
- `not_started`

A4 adds precise producer-owned canonical reasons while retaining `legacy_stop_reason` where applicable.

Examples:

- natural Beam limit -> `max_rounds_reached` / `budget`
- natural GA limit -> `max_generations_reached` / `budget`
- natural SA limit -> `max_iterations_reached` / `budget`
- natural Kaeding limit -> `max_steps_reached` / `budget`
- configured Hybrid/two-period work completed -> `configured_work_limit_reached` / `budget`
- target score -> `target_score_reached` / `success`
- `no_improve_25` -> `no_improvement_budget_reached` / `budget`
- hard crib rejects all candidates -> `all_candidates_rejected_by_hard_crib` / `blocked_before_run`
- exception -> `unexpected_exception` / `error`

Historical `done` and `success` are ambiguous. A4 does not reinterpret them as success; without a precise producer reason they map to `unknown_runtime_reason` / `error`.

`success` is a termination category, not proof of scientific recovery. Recovery is a separate status and defaults to `not_assessed` unless legitimate reference/truth data is explicitly available.
