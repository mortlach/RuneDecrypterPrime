# V1 stop-reason contract

Solver reports expose a stable stop schema in `SolverReport.details`.

Required fields:

- `stop_category`
- `stop_reason`
- `stop_detail`
- `blocked_before_run`
- `error_type`

Stable categories:

- `success`
- `budget`
- `blocked_before_run`
- `error`
- `manual`
- `not_started`

`stop_reason` remains the precise solver/runtime reason string. `stop_category` is the coarse contract field for downstream reports and dashboards.

Examples:

- `done` -> `success`
- `patience` -> `budget`
- `all_rejected_by_hard_crib` -> `blocked_before_run`
- `error` -> `error`

Blocked-before-run cases should set `blocked_before_run` to true. Unknown non-empty reasons are categorised conservatively rather than dropped.
