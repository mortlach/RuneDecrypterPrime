# `core/config/logging_config.py`

> Purpose: single source of truth for run-directory lifecycle. Tutorials/tests call `init_logging` (via `io/run_logger`) so every run lands under `output/<kind>/<timestamp>__<label>__<git>/` with META/config snapshots for reproducibility.

## Key APIs
| Symbol | Description |
| --- | --- |
| `LoggingConfig` dataclass | User-facing configuration (`verbose`, `print_progress`, `repo_root`, `out_root`, `run_kind`, `label`, `fixed_run_dir`). |
| `init_logging(cfg)` | Creates the run directory (logs/, trace/, artifacts/), writes `META.json` + `config/logging.json`, captures git/version info, and caches the paths for later lookups. |
| `get_run_dir()` / `current_paths()` | Helpers used by `io/run_logger` and tests to find the active run folder. |

Internal helpers (`_now_stamp`, `_detect_repo_root`, `_default_out_root`, `_collect_versions`, `_git_info`, `_write_meta`, `_write_logging_snapshot`, `_ensure_dirs`) support the guarantees above.

## Usage Example
```python
from rune_decrypter_prime.core.config.logging_config import LoggingConfig, init_logging, get_run_dir

cfg = LoggingConfig(
    verbose=True,
    run_kind="tutorials",
    label="vigenere_ga",
    out_root="output",
)
run_dir = init_logging(cfg)
print("Logs live under:", get_run_dir() / "logs")
```

## What META.json Contains
- timestamps, run_kind, label, PID, user/host, git commit info
- pointers to `logs/`, `trace/`, `artifacts/`
- `versions` block (Python, NumPy, Torch) so telemetry consumers can reproduce results

## Tests & Guardrails
- `tests/telemetry/test_schema_contract.py` - asserts META/log paths exist and contain required fields.
- `tests/tests_docs/tools.md` workflows rely on this module to keep doc-lint/report outputs under `output/tools/...`.

## Related Docs
- `docs/guides/outputs.md` - canonical directory layout produced by this module.
- `docs/reference/api/logging_utils.md` - converts lenient logging dicts into `LoggingConfig` before calling `init_logging`.

