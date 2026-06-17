# How-To: Read Telemetry

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Locate and inspect `telemetry.run` and `solver_progress` events
Prereqs: Completed any tutorial run

## Hands-on
1. After running a tutorial, open `output/tutorials/<run>/logs/app.jsonl`.
2. Look for `telemetry.run` (seed, solver, device) and `solver_progress` buckets.
3. Match the `pipeline` block (direction, permutation hash) with other solvers to confirm everyone used the same inputs.

## Expert
1. Programmatically inspect telemetry:
   ```python
   tel = sol.meta.get("telemetry", {})
   print(tel.get("run", {}))
   print(tel.get("solver_progress", [])[:3])
   ```
2. Use `telemetry/pipeline.dump_telemetry(sol)` to mirror runs under `output/telemetry/logs/` for post-processing.
3. Schema tests (`tests/telemetry/test_schema_contract.py`) ensure required fields exist; run them after changing telemetry code.

## Tips
- Never disable telemetry in shared/tutorial code; only experiments should toggle it off.
- Reference `docs/guides/telemetry.md` for a full field breakdown.

