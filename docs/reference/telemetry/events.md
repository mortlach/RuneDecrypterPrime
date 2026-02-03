# `telemetry/events.py`

> Purpose: emit canonical telemetry events (`telemetry.run`, `telemetry.solver_start`, `telemetry.solver_progress`, `telemetry.solver_end`). Engine/solvers call these helpers so every run logs the same schema regardless of solver or device.

## Helpers
- `_ensure_tel_dict(problem)` - Lazily initialises `problem.telemetry` as a dict, ensuring subsequent events have a place to live.
- `run_start(problem, seed, solver, device, scorer, pipeline, params)` - Envelope emitted by `core/engine/engine.solve` before any solver work begins. Overwrites the `telemetry.run` envelope to avoid stale data from earlier phases.
- `run_end(problem, seed, solver, device, scorer, pipeline, result)` - Envelope emitted after solver completion (success or failure). Uses `perf_counter` timings and then copies the run envelope into solution metadata.
- Additional functions in the file cover `solver_start`, `solver_progress`, `solver_end`, and progress aggregation (see source for full list).

## Usage
Called internally by the engine and solvers; downstream consumers read these JSONL events under `output/<kind>/<run>/logs/app.jsonl`.

## Tests
- `tests/telemetry/test_solver_pipeline_block.py`, `tests/telemetry/test_progress_events.py`, `tests/telemetry/test_telemetry_vars.py` - assert that events contain the required keys and bucketisation logic.
- `tests/smoke/test_runapi_determinism.py` - ensures identical seeds produce identical telemetry payloads.

## Related Docs
- `docs/reference/telemetry/pipeline.md` - describes the pipeline block inserted into each event.
- `docs/guides/telemetry.md` - Hands-on explanation of the event structure for troubleshooting.

