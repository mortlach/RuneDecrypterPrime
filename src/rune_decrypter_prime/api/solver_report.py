from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Integral, Real
from pathlib import Path
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True, slots=True)
class SolverReport:
    solver_name: str
    requested_seed: int | None = None
    effective_seed: int | None = None
    normalized_params: Mapping[str, Any] = field(default_factory=dict)
    stop_reason: str | None = None
    best_score: float | None = None
    best_key: Sequence[int] | None = None
    step: int | None = None
    evals: int | None = None
    tokens_processed: int | None = None
    wall_time_s: float | None = None
    decrypt_time_s: float | None = None
    score_time_s: float | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "solver_name", _require_text(self.solver_name, "solver_name"))
        object.__setattr__(
            self,
            "requested_seed",
            _require_optional_int(self.requested_seed, "requested_seed"),
        )
        object.__setattr__(
            self,
            "effective_seed",
            _require_optional_int(self.effective_seed, "effective_seed"),
        )
        object.__setattr__(
            self,
            "normalized_params",
            _copy_json_mapping(self.normalized_params, "normalized_params"),
        )
        object.__setattr__(
            self,
            "stop_reason",
            _require_optional_text(self.stop_reason, "stop_reason"),
        )
        object.__setattr__(
            self,
            "best_score",
            _require_optional_finite_float(self.best_score, "best_score"),
        )
        object.__setattr__(self, "best_key", _copy_best_key(self.best_key))
        object.__setattr__(self, "step", _require_optional_counter(self.step, "step"))
        object.__setattr__(self, "evals", _require_optional_counter(self.evals, "evals"))
        object.__setattr__(
            self,
            "tokens_processed",
            _require_optional_counter(self.tokens_processed, "tokens_processed"),
        )
        object.__setattr__(
            self,
            "wall_time_s",
            _require_optional_nonnegative_float(self.wall_time_s, "wall_time_s"),
        )
        object.__setattr__(
            self,
            "decrypt_time_s",
            _require_optional_nonnegative_float(self.decrypt_time_s, "decrypt_time_s"),
        )
        object.__setattr__(
            self,
            "score_time_s",
            _require_optional_nonnegative_float(self.score_time_s, "score_time_s"),
        )
        object.__setattr__(self, "details", _copy_json_mapping(self.details, "details"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "solver_name": self.solver_name,
            "requested_seed": self.requested_seed,
            "effective_seed": self.effective_seed,
            "normalized_params": _to_json_value(self.normalized_params),
            "stop_reason": self.stop_reason,
            "best_score": self.best_score,
            "best_key": list(self.best_key) if self.best_key is not None else None,
            "step": self.step,
            "evals": self.evals,
            "tokens_processed": self.tokens_processed,
            "wall_time_s": self.wall_time_s,
            "decrypt_time_s": self.decrypt_time_s,
            "score_time_s": self.score_time_s,
            "details": _to_json_value(self.details),
        }


def build_solver_report(
    *,
    solver_name: str,
    requested_seed: int | None,
    effective_seed: int | None,
    normalized_params: Mapping[str, Any],
    stop_reason: str | None = None,
    best_score: float | None = None,
    best_key: Sequence[int] | None = None,
    step: int | None = None,
    evals: int | None = None,
    tokens_processed: int | None = None,
    wall_time_s: float | None = None,
    decrypt_time_s: float | None = None,
    score_time_s: float | None = None,
    details: Mapping[str, Any] | None = None,
) -> SolverReport:
    if isinstance(normalized_params, Mapping) and "name" in normalized_params:
        raise ValueError('normalized_params must not include "name"')
    return SolverReport(
        solver_name=solver_name,
        requested_seed=requested_seed,
        effective_seed=effective_seed,
        normalized_params=normalized_params,
        stop_reason=stop_reason,
        best_score=best_score,
        best_key=best_key,
        step=step,
        evals=evals,
        tokens_processed=tokens_processed,
        wall_time_s=wall_time_s,
        decrypt_time_s=decrypt_time_s,
        score_time_s=score_time_s,
        details={} if details is None else details,
    )


def _require_text(value: Any, field_name: str) -> str:
    if isinstance(value, Path) or not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _require_optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)


def _require_optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer or None")
    return int(value)


def _require_optional_counter(value: Any, field_name: str) -> int | None:
    item = _require_optional_int(value, field_name)
    if item is not None and item < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return item


def _require_optional_finite_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a finite float or None")
    item = float(value)
    if not math.isfinite(item):
        raise ValueError(f"{field_name} must be finite")
    return item


def _require_optional_nonnegative_float(value: Any, field_name: str) -> float | None:
    item = _require_optional_finite_float(value, field_name)
    if item is not None and item < 0.0:
        raise ValueError(f"{field_name} must be >= 0")
    return item


def _copy_best_key(value: Any) -> tuple[int, ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, Path, Mapping)) or not isinstance(value, Sequence):
        raise TypeError("best_key must be an ordered sequence of integers or None")
    return tuple(_require_key_int(item, f"best_key[{index}]") for index, item in enumerate(value))


def _require_key_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    return int(value)


def _copy_json_mapping(value: Any, field_name: str) -> MappingProxyType[str, Any]:
    if isinstance(value, Path) or not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")

    copied: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(key, Path) or not isinstance(key, str):
            raise TypeError(f"{field_name} keys must be strings")
        if not key:
            raise ValueError(f"{field_name} keys must not be empty")
        copied[key] = _copy_json_value(item, f"{field_name}.{key}")
    return MappingProxyType(copied)


def _copy_json_value(value: Any, field_name: str) -> Any:
    if isinstance(value, Path):
        raise TypeError(f"{field_name} must not be a Path")
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name} float values must be finite")
        return float(value)
    if isinstance(value, Mapping):
        return _copy_json_mapping(value, field_name)
    if isinstance(value, (list, tuple)):
        return tuple(_copy_json_value(item, f"{field_name}[]") for item in value)
    raise TypeError(f"{field_name} must be JSON-compatible")


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _to_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    return value


__all__ = ["SolverReport", "build_solver_report"]
