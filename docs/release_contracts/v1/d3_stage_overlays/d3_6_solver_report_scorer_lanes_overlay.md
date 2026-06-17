# D3.6 solver-report scorer-lanes overlay

Scope: propagate scorer capability reports into solver-report details.

Changed files:

- `src/rune_decrypter_prime/api/pipeline_helpers.py`
- `src/rune_decrypter_prime/api/run.py`
- `tests/api/test_solver_report_scorer_lanes.py`

Locked behaviour:

- `finalize_solution(...)` copies `scorer.capability_report().to_json_dict()` into `solution.meta["scorer_lanes"]` when available.
- solver-report construction copies `solution.meta["scorer_lanes"]` into `solver_report.details["scorer_lanes"]`.
- missing scorer-lane metadata is omitted and remains non-fatal.
- no scoring, ranking, solver, Torch, or ScheduledStreamLookup behaviour is changed.
