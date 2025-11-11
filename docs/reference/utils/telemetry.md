# `utils/telemetry.py`

> Purpose: no-throw helpers for updating telemetry dictionaries and constructing event payloads. Used by scorers and solvers to avoid duplicating boilerplate when recording stats.

## Functions
- `stash(holder, **fields)` - Safely merges key/value pairs into `holder` (if it's a dict). Swallows exceptions so telemetry never interferes with scoring/solving.
- `event(name, **kv)` - Returns a dict like `{"type": name, ...kv}`; used by logging routines before handing events to `RunLogger`.

## Usage
```python
from rune_decrypter_prime.utils.telemetry import stash, event

stats = {}
stash(stats, best_score=0.54, evals=1024)
logger.log_event(event("solver_progress", pct=10, best_score=0.54))
```

## Tests
- Indirect coverage through scoring and solver telemetry tests (`tests/scoring/test_pct_win10_stats_and_telemetry.py`, `tests/telemetry/test_progress_events.py`) since they rely on these helpers to populate stats without throwing.

