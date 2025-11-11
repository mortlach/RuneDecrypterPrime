# Telemetry - Essentials

> Tracks: Hands-on sections explain how to read tutorial/test logs; Expert sections describe schema rules, contracts, and validation tests.

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Read telemetry.run and solver_progress in logs and know required fields
Prereqs: Completed one tutorial run

## What Telemetry Records
- telemetry.run - seed, solver, device, scorer metadata, pipeline block, params, and start/end timestamps.
- telemetry.solver_progress - percentage buckets with {step, pct, best_score, evals, reason} plus timing counters.
- telemetry.solver_spans - per-solver start/end payloads (beam/GA/SA/Hybrid stages).
- solution.meta["work"] - aggregate decrypt_time_s, score_time_s, eval counts, and tokens for the solved run.

## Hands-on Guide - Reading Logs
1. After running a tutorial, open output/tutorials/<run>/logs/app.jsonl.
2. Search for telemetry.run to confirm direction, device, and pipeline hashes match your expectations or another solver's run.
3. Scroll to telemetry.solver_progress entries (printed at 1% increments) to see how best_score evolved.
4. Use the troubleshooting appendix if telemetry blocks are missing or the JSON looks corrupt.

## Expert Guide - Producing and Validating Telemetry
- telemetry/events.py attaches solver spans and progress records; call these helpers when adding solvers.
- telemetry/pipeline.py computes the pipeline block (direction + permutation hash). Always pass canonical direction enums and permutation indices.
- io/run_logger.py mirrors telemetry into JSONL logs under output/<kind>/<run_id>/logs/.
- Schema contract: tests/telemetry/test_schema_contract.py enforces the required fields (device, seed, decrypt_time_s, score_time_s, evaluation counts, etc.).
- Solver base classes (solvers/solver_base.py) populate solution.meta["work"] so higher-level consumers can compare decrypt vs. scoring cost.

### Required Fields
| Field | Source | Notes |
| --- | --- | --- |
| telemetry.run.seed | core/engine/engine.py | Field must exist even if the solver chooses the default seed. |
| telemetry.run.pipeline | telemetry/pipeline.make_pipeline_block | Includes direction and permutation hash. |
| telemetry.run.scorer | scoring/scoring_adapter.py | Must expose implementation, device, dtype. |
| telemetry.solver_spans | telemetry/events.solver_start/end | Capture solver params plus the final best_score. |
| telemetry.solver_progress | telemetry/events.progress_event | Buckets are emitted whenever progress_pct thresholds are crossed. |
| solution.meta["work"] | solvers/solver_base.py | Contains decrypt_time_s, score_time_s, total evals, and token counts. |

### Dumping Telemetry Separately
```python
from rune_decrypter_prime.telemetry.pipeline import dump_telemetry

dump_path = dump_telemetry(solution, base_dir="output/telemetry/logs")
print(f"Saved telemetry to {dump_path}")
```

## FAQ
- Can I disable telemetry? Set telemetry_on=False only for local experiments. Tutorials, docs, and CI must keep telemetry enabled.
- Where do progress buckets come from? solvers/solver_base.py emits solver_progress records as soon as each percentage bucket is met.
- How do I add a new field? Update telemetry/events.py, extend the schema tests, and document the field in this guide (plus the reference doc if appropriate).

## Related Docs
- guides/outputs.md - explains where telemetry logs live inside the output/ tree.
- guides/scoring_deep.md - shows how scorer metadata flows into telemetry.
- appendices/high_school_troubleshooting.md - steps for recovering missing telemetry or unexpected run directories.

## Related tests
- `tests/telemetry/test_schema_contract.py`
- `tests/telemetry/test_progress_events.py`

