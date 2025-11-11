# `utils/telemetry_utils.py`

> Purpose: convenience helpers for inspecting telemetry dictionaries produced by RunAPI. Ideal for tutorials/tests that want to peek at `sol.meta["telemetry"]` without worrying about enum conversions or legacy key names.

## Functions
- `telem(sol)` - Returns `sol.meta.get("telemetry", {})`.
- `run_meta(sol)` - Returns `sol.meta.get("run_meta", {})`.
- `print_telem(sol, *paths)` - Pretty-prints the telemetry dict, optionally filtering by dotted paths (`"run.seed"`, `"solver_progress.best_score"`).
- `_upgrade_v1_time_keys` / `canonicalize_timing_keys(payload)` - Normalise legacy timing keys (e.g., `"decrypt_time"` -> `"decrypt_time_s"`).
- `_enum_to_value(obj)` / `stringify_for_telemetry(ctx)` - Convert enums/dataclasses into plain types for JSON/logging.

## Usage
```python
from rune_decrypter_prime.utils.telemetry_utils import print_telem

solution = RunAPI.run(...)
print_telem(solution, "run", "solver_progress")
```

## Tests
- Used extensively in tutorials and telemetry guardrails. If `canonicalize_timing_keys` regressed, `tests/telemetry/test_schema_contract.py` would fail due to missing `*_time_s` fields.

