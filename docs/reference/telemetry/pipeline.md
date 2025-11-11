# `telemetry/pipeline.py`

> Purpose: describe the solving pipeline (direction, permutation hash, cipher/scorer metadata) in a canonical block that accompanies every telemetry event. Also offers helpers for exporting telemetry for offline analysis.

## Functions
- `device_request_str(dev)` - Converts `Device` enums into backend request tokens (`"cpu"`, `"cuda"`) for scoring backends.
- `make_pipeline_block(problem_instance)` - Builds the dictionary inserted into `telemetry.run` / solver spans (direction, permutation hash, cipher name, key length, encoding hints).
- `dump_telemetry(solution, base_dir="output/telemetry/logs")` - Writes `solution.meta["telemetry"]` to disk for ad-hoc debugging (used by how-to recipes and tutorials).

## Usage
```python
from rune_decrypter_prime.telemetry.pipeline import dump_telemetry

path = dump_telemetry(solution, base_dir="output/telemetry/logs")
print("Telemetry JSONL saved to", path)
```

## Tests
- `tests/telemetry/test_pipeline_block_itp.py`, `tests/telemetry/test_solver_pipeline_block.py` - ensure permutation hashes/directions are populated correctly.
- `tests/telemetry/test_solution_pipeline_block.py` (if present) - verifies pipeline blocks attach to solutions via `pipeline_helpers.finalize_solution`.

## Related Docs
- `docs/guides/telemetry.md` - explains how Hands-on users can inspect pipeline blocks in `logs/app.jsonl`.
- `docs/reference/api/pipeline_helpers.md` - shows where `make_pipeline_block` output is attached to `Solution`.

