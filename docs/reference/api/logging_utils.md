# `api/logging_utils.py`

> Purpose: bridge between the lenient logging knobs exposed to tutorials/tests and the strict `core.config.logging_config.LoggingConfig` used by the runtime.

## `normalize_logging_cfg(logging)`
| Accepts | Behaviour |
| --- | --- |
| `None` | Returns a default `CoreLoggingConfig()` (writes under `output/<kind>/...`). |
| `CoreLoggingConfig` | Returned as-is. |
| `dict` | Filters to supported keys (`verbose`, `print_progress`, `write_jsonl`, `repo_root`, `out_root`, `run_kind`, `label`, `fixed_run_dir`), coerces path-like values to absolute strings, and instantiates `CoreLoggingConfig`. |

Any other type raises `TypeError` to keep the logging pipeline deterministic.

## Usage
```python
from rune_decrypter_prime.api.logging_utils import normalize_logging_cfg

cfg = normalize_logging_cfg({
    "verbose": True,
    "label": "tutorial",
    "out_root": "output",
})
# cfg is a core LoggingConfig that RunAPI can pass into io/run_logger.py
```

## Tests & Guardrails
- Exercised indirectly via tutorials/tests that pass logging dictionaries into `RunAPI.run`. Invalid keys or non-string paths raise early, keeping outputs inside `output/`.

## See Also
- `docs/guides/outputs.md` - canonical tree that this config writes to.
- `docs/tests_docs/tools.md` - docs-lint runner and symbol index commands also rely on the same output conventions.

