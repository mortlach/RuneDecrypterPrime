# Telemetry

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Read the schema and required fields
Prereqs: Completed one tutorial

**Concept**  
Structured JSONL events that describe a run. Minimal schema; true on/off toggle.

## Always present
- `timestamp` / `wall_time_s`  
- `step`, `evals`, `since_improve`  
- `best_score`  
- `optimizer` (name, params or hash)  
- `scorer` (impl, dtype)  
- `device` (e.g. `"cpu"`)  
- `seed`  
- `pipeline` (direction, permutation summary)

## Telemetry toggle and overhead
- `RunAPI.run(..., telemetry=False)` -> **no events and no files**.  
- When enabled, events go to `output/<label>/<timestamp>/logs/app.jsonl`.

**Overhead discipline (v1):**
- Logging overhead kept small and stable; snapshot tests guard schema and key timings.
- Event names are short and consistent: `run_start`, `phase`, `new_best`, `run_end`.

**Device parity (v1):**  
All examples and tests run on **CPU**. If Torch is present, it is pinned to CPU for deterministic parity across machines.

## Example events (shape)
```json
{"event":"run_start","seed":42,"device":"cpu",
 "pipeline":{"direction":"ltr","permutation":{"kind":"none"}}}

{"event":"new_best","evals":1042,"since_improve":0,"best_score":1.2345}

{"event":"run_end","evals":50000,"best_score":1.5678}
```

**See also**  

**Related tests**
- `tests/telemetry/test_schema_contract.py`
- `tests/telemetry/test_progress_events.py`
**See also**  
[Engine & API](engine_api.md) · [Data & Scoring](data.md)

[<- Optimisers](optimisers.md) · [Next -> Data & Scoring](data.md)

