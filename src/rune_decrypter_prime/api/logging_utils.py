from __future__ import annotations

from typing import Any
from rune_decrypter_prime.core.config.logging_config import LoggingConfig as CoreLoggingConfig


def normalize_logging_cfg(logging: Any) -> CoreLoggingConfig:
    """Convert a lenient UI logging object into the strict core config."""
    if logging is None:
        return CoreLoggingConfig()
    if isinstance(logging, CoreLoggingConfig):
        return logging
    if isinstance(logging, dict):
        cfg = dict(logging)
        allowed = {
            "verbose",
            "print_progress",
            "write_jsonl",
            "repo_root",
            "out_root",
            "run_kind",
            "label",
            "fixed_run_dir",
        }
        filtered = {k: v for k, v in cfg.items() if k in allowed}
        for path_key in ("out_root", "repo_root", "fixed_run_dir"):
            value = filtered.get(path_key)
            if value is not None and not isinstance(value, str):
                try:
                    from pathlib import Path
                    filtered[path_key] = str(Path(value).resolve())
                except Exception:
                    filtered.pop(path_key, None)
        return CoreLoggingConfig(**filtered)
    raise TypeError(
        "logging must be None, a dict, or rune_decrypter_prime.core.logging_config.LoggingConfig"
    )
