# `io/run_logger.py`

> Purpose: simple structured logger used by tutorials/tests to write JSONL events (`logs/app.jsonl`) and ad-hoc trace files under `output/<kind>/<run>/trace/`. Automatically initialises the logging config if a run directory does not exist yet.

## Key Pieces
| Symbol | Description |
| --- | --- |
| `_ts()` | Timestamp helper (timezone-aware when `zoneinfo` is available). |
| `_ensure_dir(path)` | Safe `mkdir -p`. |
| `RunLogger` class | Provides `log_event` (append JSONL) and `log_trace` (write text files + emit event). Automatically creates a run directory via `LoggingConfig` if one is not active. |
| `get_logger()` | Singleton accessor; creates a default `RunLogger` on first call. |

## Usage
```python
from rune_decrypter_prime.io.run_logger import get_logger

logger = get_logger()
logger.log_event({"type": "progress", "pct": 10, "best_score": 0.52})
logger.log_trace({"func": "solver_debug", "trace": "..."})
```

## Integration Points
- `api/logging_utils.normalize_logging_cfg` and `core/config/logging_config.init_logging` cooperate so every run has a canonical folder.
- Telemetry helpers (`telemetry/events.py`) rely on `RunLogger` writing their JSON payloads.

## Tests
- Behaviour is exercised implicitly by every tutorial/test that writes telemetry. Failures manifest as missing `logs/app.jsonl`, caught by guards like `tests/telemetry/test_schema_contract.py`.

