from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path
from typing import Any, Mapping

from rune_decrypter_prime.core.types import ObjectiveSpec


def _objective_spec_to_dict(spec: ObjectiveSpec) -> dict[str, Any]:
    family = getattr(spec.family, "value", spec.family)
    stat = getattr(spec.stat, "value", spec.stat) if spec.stat is not None else None
    win = int(spec.win) if spec.win is not None else None
    return {
        "family": str(family),
        "stat": (str(stat) if stat is not None else None),
        "win": win,
    }


def _finite_float(value: Any, *, field_name: str) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{field_name} must be finite, got {value!r}")
    return out


def _to_json_primitive(value: Any, *, max_items: int = 64, depth: int = 0) -> Any:
    if isinstance(value, Path):
        if value.is_absolute():
            raise ValueError("report payload contains absolute Path")
        return value.as_posix()
    if depth > 6:
        return str(value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("report payload contains non-finite float")
        return float(value)
    if isinstance(value, Enum):
        return getattr(value, "value", str(value))
    if isinstance(value, ObjectiveSpec):
        return _objective_spec_to_dict(value)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for idx, (k, v) in enumerate(value.items()):
            if idx >= max_items:
                break
            out[str(k)] = _to_json_primitive(v, max_items=max_items, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        vals = list(value)[:max_items]
        return [_to_json_primitive(v, max_items=max_items, depth=depth + 1) for v in vals]
    return str(value)


@dataclass(frozen=True)
class ScorerReport:
    objective_str: str
    objective_spec: ObjectiveSpec
    score: float
    raw_score: float | None = None
    telemetry: Mapping[str, Any] = field(default_factory=dict)
    metrics: Mapping[str, float] = field(default_factory=dict)
    cost_ms: float | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        score = _finite_float(self.score, field_name="score")
        raw_score = (
            _finite_float(self.raw_score, field_name="raw_score")
            if self.raw_score is not None
            else None
        )
        cost_ms = (
            _finite_float(self.cost_ms, field_name="cost_ms")
            if self.cost_ms is not None
            else None
        )

        metrics: dict[str, float] = {}
        for k, v in dict(self.metrics or {}).items():
            metrics[str(k)] = _finite_float(v, field_name=f"metrics.{k}")

        return {
            "objective_str": str(self.objective_str),
            "objective_spec": _objective_spec_to_dict(self.objective_spec),
            "score": score,
            "raw_score": raw_score,
            "telemetry": _to_json_primitive(dict(self.telemetry or {})),
            "metrics": metrics,
            "cost_ms": cost_ms,
            "details": _to_json_primitive(dict(self.details or {})),
        }

