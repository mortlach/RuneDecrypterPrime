"""User-facing logging normalisers that feed the core LoggingConfig."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from rune_decrypter_prime.core.config.logging_config import LoggingConfig as CoreLoggingConfig

_RUNTIME_LOGGING_KEYS = {"progress_callback", "log_interval"}
_DURABLE_OUTPUT_PATH_KEYS = {
    "output_root",
    "run_directory",
    "run_category",
    "label",
}
_DURABLE_OUTPUT_TRUE_KEYS = {
    "portable_output",
    "redact_identity",
    "write_event_log",
    "write_solver_report",
    "write_artifact_manifest",
}
_STRICT_BOOL_KEYS = {"write_solver_report", "write_artifact_manifest"}


@dataclass(frozen=True)
class _LoggingRoute:
    config: CoreLoggingConfig | None = None
    runtime_controls: dict[str, Any] = field(default_factory=dict)
    initialize_output: bool = False


def normalize_logging_cfg(logging: Any) -> CoreLoggingConfig:
    """Construct the strict config from canonical serialized fields."""
    if logging is None:
        return CoreLoggingConfig()
    if isinstance(logging, CoreLoggingConfig):
        return logging
    if isinstance(logging, dict):
        return CoreLoggingConfig.from_dict(dict(logging))
    raise TypeError(
        "logging must be None, a dict, or rune_decrypter_prime.core.logging_config.LoggingConfig"
    )


def _dict_requests_durable_output(logging: dict[str, Any]) -> bool:
    _validate_strict_bool_keys(logging)
    for key in _DURABLE_OUTPUT_PATH_KEYS:
        if key in logging and logging[key] is not None:
            return True
    return any(bool(logging.get(key)) for key in _DURABLE_OUTPUT_TRUE_KEYS)


def _validate_strict_bool_keys(logging: dict[str, Any]) -> None:
    for key in _STRICT_BOOL_KEYS:
        if key in logging and type(logging[key]) is not bool:
            raise TypeError(f"{key} must be a bool")


def _route_logging_input(logging: Any) -> _LoggingRoute:
    """Split public logging input into durable config and runtime controls."""
    if logging is None:
        return _LoggingRoute()
    if isinstance(logging, CoreLoggingConfig):
        return _LoggingRoute(config=logging, initialize_output=True)
    if isinstance(logging, dict):
        runtime_controls = {k: logging[k] for k in _RUNTIME_LOGGING_KEYS if k in logging}
        if _dict_requests_durable_output(logging):
            return _LoggingRoute(
                config=normalize_logging_cfg(logging),
                runtime_controls=runtime_controls,
                initialize_output=True,
            )
        return _LoggingRoute(runtime_controls=runtime_controls)
    raise TypeError(
        "logging must be None, a dict, or rune_decrypter_prime.core.logging_config.LoggingConfig"
    )
