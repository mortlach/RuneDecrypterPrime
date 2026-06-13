# Telemetry – Essentials

Audience: Hands-on / Expert  
Time: 3–5 minutes  
Outcome: Read `telemetry.run`, `telemetry.solver_progress`, and `solution.meta["work"]` entries in logs and know the required fields/contracts.  
Prereqs: Completed one tutorial run.

> Tracks: Hands-on sections show how to inspect logs; Expert sections describe schema rules, contracts, and validation tests.

---

## 1. What telemetry records
- **`telemetry.run`** – seed, solver name, device, scorer metadata (impl/device/dtype), pipeline block (direction + permutation hash), parameters, start/end timestamps.
- **`telemetry.solver_progress`** – percentage buckets with `{pct, iter, evals, best_score, since_improve}` plus optional reasons (patience, stop_score met).
- **`telemetry.solver_spans`** – per-solver or per-phase envelopes (Beam/GA/SA/Hybrid) with parameters and final results.
- **`solution.meta["work"]`** – timing and throughput counters (decrypt_time_s, score_time_s, candidates evaluated, tokens processed) harvested from `solvers/solver_base.py`.

Use these together to answer “what did we run?” and “how did it progress?” for any tutorial/test.

---

## 2. Hands-on guide: reading logs
1. Run a tutorial (e.g., `python tutorials/v1/Start_Here.py`).
2. Open `output/tutorials/<run_id>/logs/app.jsonl`.
3. Find the latest `telemetry.run` block to confirm `text_encoding_direction`, `solver`, `seed`, and scorer backend. Comparing two runs? Diff this block.
4. Scroll to `telemetry.solver_progress` entries (emitted at `progress_pct` increments, default 1%) to see how `best_score` evolved.
5. If blocks are missing or malformed, follow `docs/guides/troubleshooting.md` (usually a venv/working-dir issue).

---

## 3. Expert guide: emitting telemetry correctly
- Use `telemetry/events.py` helpers (`run_start`, `progress_event`, `solver_start/solver_end`) when building solvers so spans stay consistent.
- Build the pipeline block via `telemetry/pipeline.make_pipeline_block` — it hashes direction + permutation so pipelines remain traceable.
- `io/run_logger.py` mirrors telemetry into JSONL under `output/<kind>/<run_id>/logs/app.jsonl`. Always initialise logging via `LoggingConfig`.
- Schema enforcement lives in `tests/telemetry/test_schema_contract.py`. Extend that test if you add fields so CI catches regressions.
- Solver bases keep `solution.meta["work"]` up to date; rely on those counters when building dashboards or analysing runs.

### Required fields (contract checks)
| Field | Source | Notes |
| --- | --- | --- |
| `telemetry.run.seed` | `core/engine/engine.py` | Must exist even when the seed defaults to 0. |
| `telemetry.run.pipeline` | `telemetry/pipeline.make_pipeline_block` | Includes direction + permutation hash. |
| `telemetry.run.scorer` | `scoring/scoring_adapter.py` | Should expose `{"impl": ..., "device": ..., "dtype": ...}`. |
| `telemetry.solver_spans` | `telemetry/events.solver_start/end` | One span per solver/stage with params + final `best_score`. |
| `telemetry.solver_progress` | `telemetry/events.progress_event` | Buckets fire whenever `progress_pct` thresholds are crossed. |
| `solution.meta["work"]` | `solvers/solver_base.py` | Aggregates decrypt time, score time, eval counts, tokens processed. |

### Dumping telemetry elsewhere
```python
from rune_decrypter_prime.telemetry.pipeline import dump_telemetry

dump_path = dump_telemetry(solution, base_dir="output/telemetry/logs")
print(f"Saved telemetry to {dump_path}")
```

---

## 4. FAQ
- **Can I disable telemetry?** Set `telemetry_on=False` only for personal experiments. Tutorials, docs, and CI runs must keep telemetry enabled for reproducibility.
- **Where do progress buckets come from?** `solvers/solver_base.py` tracks `progress_pct`; it emits a bucket as soon as the solver passes each threshold.
- **How do I add a new field?** Update the relevant helper in `telemetry/events.py`, extend the schema test, and document the field here (plus `guides/architecture.md` if it affects the pipeline).

---

## 5. Related docs/tests
- Docs: `guides/outputs.md`, `guides/scoring_deep.md`, `guides/troubleshooting.md`.
- Tests: `tests/telemetry/test_schema_contract.py`, `tests/telemetry/test_progress_events.py`, `tests/pipeline/test_permutation_tracking.py`.
