"""Immutable V1 execution, configuration, oracle, and reproducibility reports."""

from __future__ import annotations

import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType

from rune_decrypter_prime import rune_decrypter_prime_version
from rdp.api.stop_reason_contract import RunStatus, StopCategory, StopReason
from rdp.core.types import (
    ComputeDevice,
    ConcreteKey,
    FloatDType,
    JsonObject,
    JsonValue,
    ScorerBackend,
    SolverKind,
    normalize_concrete_key,
)


def _json_value(value: object, field_name: str) -> JsonValue:
    if value is None or type(value) in {str, bool, int}:
        return value  # type: ignore[return-value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name} contains a non-finite float")
        return value
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, Path):
        if value.is_absolute():
            raise ValueError(f"{field_name} contains an absolute path")
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item, f"{field_name}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{field_name}[]") for item in value]
    raise TypeError(f"{field_name} contains unsupported {type(value).__name__}")


def _mapping(value: Mapping[str, object], field_name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{field_name} keys must be strings")
    return MappingProxyType(
        {key: _json_value(item, f"{field_name}.{key}") for key, item in value.items()}
    )


def _optional_int(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer or None")
    return value


def _counter(value: int, field_name: str) -> int:
    result = _optional_int(value, field_name)
    assert result is not None
    if result < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return result


def _time(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return result


@dataclass(frozen=True, slots=True)
class ConfigurationResolution:
    requested: JsonObject = field(default_factory=dict)
    effective: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested", _mapping(self.requested, "requested"))
        object.__setattr__(self, "effective", _mapping(self.effective, "effective"))

    def to_dict(self) -> JsonObject:
        return {"requested": dict(self.requested), "effective": dict(self.effective)}

    def to_json_dict(self) -> JsonObject:
        return self.to_dict()


@dataclass(frozen=True, slots=True)
class RunConfigurationReport:
    solver: ConfigurationResolution
    scoring: ConfigurationResolution
    cipher: ConfigurationResolution

    def __post_init__(self) -> None:
        for name in ("solver", "scoring", "cipher"):
            if not isinstance(getattr(self, name), ConfigurationResolution):
                raise TypeError(f"{name} must be ConfigurationResolution")

    def to_dict(self) -> JsonObject:
        return {"solver": self.solver.to_dict(), "scoring": self.scoring.to_dict(), "cipher": self.cipher.to_dict()}

    def to_json_dict(self) -> JsonObject:
        return self.to_dict()


class OracleMode(str, Enum):
    REAL_SOLVE = "real_solve"
    TUTORIAL = "tutorial"
    TEST = "test"
    BENCHMARK = "benchmark"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class OracleReport:
    available: bool = False
    used_for_scoring: bool = False
    used_for_ranking: bool = False
    used_for_stop: bool = False
    stop_reason: StopReason | None = None
    mode: OracleMode = OracleMode.REAL_SOLVE

    def __post_init__(self) -> None:
        for name in ("available", "used_for_scoring", "used_for_ranking", "used_for_stop"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool")
        if self.stop_reason is not None and not isinstance(self.stop_reason, StopReason):
            raise TypeError("stop_reason must be StopReason or None")
        if not isinstance(self.mode, OracleMode):
            raise TypeError("mode must be OracleMode")
        if (self.used_for_scoring or self.used_for_ranking or self.used_for_stop) and not self.available:
            raise ValueError("oracle use requires available=True")
        if self.used_for_stop != (self.stop_reason is not None):
            raise ValueError("oracle stop use and stop_reason must be recorded together")

    def to_dict(self) -> JsonObject:
        return {
            "available": self.available,
            "used_for_scoring": self.used_for_scoring,
            "used_for_ranking": self.used_for_ranking,
            "used_for_stop": self.used_for_stop,
            "stop_reason": None if self.stop_reason is None else self.stop_reason.value,
            "mode": self.mode.value,
        }

    def to_json_dict(self) -> JsonObject:
        return self.to_dict()


@dataclass(frozen=True, slots=True)
class ReproducibilityMetadata:
    run_id: str | None = None
    created_at_utc: str | None = None
    rdp_version: str = rune_decrypter_prime_version
    git_branch: str | None = None
    git_commit: str | None = None
    python_version: str = sys.version
    backend: ScorerBackend | None = None
    compute_device: ComputeDevice | None = None
    compute_dtype: FloatDType | None = None
    accumulator_dtype: FloatDType | None = None
    requested_seed: int | None = None
    effective_seed: int | None = None
    stochastic: bool | None = None
    solver_config: JsonObject | None = None
    scoring_config: JsonObject | None = None
    objective: JsonObject | None = None
    cipher: JsonObject | None = None
    asset_ids: tuple[str, ...] = ()
    asset_hashes: Mapping[str, str] = field(default_factory=dict)
    dictionary_policy: str | None = None
    stop_category: StopCategory | None = None
    stop_reason: StopReason | None = None

    def __post_init__(self) -> None:
        for name, enum_type in (
            ("backend", ScorerBackend),
            ("compute_device", ComputeDevice),
            ("compute_dtype", FloatDType),
            ("accumulator_dtype", FloatDType),
            ("stop_category", StopCategory),
            ("stop_reason", StopReason),
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, enum_type):
                raise TypeError(f"{name} must be {enum_type.__name__} or None")
        object.__setattr__(self, "requested_seed", _optional_int(self.requested_seed, "requested_seed"))
        object.__setattr__(self, "effective_seed", _optional_int(self.effective_seed, "effective_seed"))
        if self.stochastic is not None and type(self.stochastic) is not bool:
            raise TypeError("stochastic must be bool or None")
        for name in ("solver_config", "scoring_config", "objective", "cipher"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _mapping(value, name))
        ids = tuple(self.asset_ids)
        if any(not isinstance(item, str) for item in ids):
            raise TypeError("asset_ids must contain strings")
        object.__setattr__(self, "asset_ids", ids)
        hashes = dict(self.asset_hashes)
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in hashes.items()):
            raise TypeError("asset_hashes must map strings to strings")
        object.__setattr__(self, "asset_hashes", MappingProxyType(hashes))

    def to_dict(self) -> JsonObject:
        def enum_value(value: Enum | None) -> str | None:
            return None if value is None else str(value.value)
        return {
            "run_id": self.run_id,
            "created_at_utc": self.created_at_utc,
            "rdp_version": self.rdp_version,
            "git_branch": self.git_branch,
            "git_commit": self.git_commit,
            "python_version": self.python_version,
            "backend": enum_value(self.backend),
            "compute_device": enum_value(self.compute_device),
            "compute_dtype": enum_value(self.compute_dtype),
            "accumulator_dtype": enum_value(self.accumulator_dtype),
            "requested_seed": self.requested_seed,
            "effective_seed": self.effective_seed,
            "stochastic": self.stochastic,
            "solver_config": None if self.solver_config is None else dict(self.solver_config),
            "scoring_config": None if self.scoring_config is None else dict(self.scoring_config),
            "objective": None if self.objective is None else dict(self.objective),
            "cipher": None if self.cipher is None else dict(self.cipher),
            "asset_ids": list(self.asset_ids),
            "asset_hashes": dict(self.asset_hashes),
            "dictionary_policy": self.dictionary_policy,
            "stop_category": enum_value(self.stop_category),
            "stop_reason": enum_value(self.stop_reason),
        }

    def to_json_dict(self) -> JsonObject:
        return self.to_dict()


@dataclass(frozen=True, slots=True)
class SolverReport:
    solver: SolverKind
    parameters: ConfigurationResolution
    requested_seed: int | None
    effective_seed: int
    status: RunStatus
    best_key: ConcreteKey | None = None
    best_score: float | None = None
    evaluations: int = 0
    steps: int = 0
    tokens_processed: int = 0
    wall_time_seconds: float = 0.0
    decrypt_time_seconds: float = 0.0
    score_time_seconds: float = 0.0
    details: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.solver, SolverKind):
            raise TypeError("solver must be SolverKind")
        if not isinstance(self.parameters, ConfigurationResolution):
            raise TypeError("parameters must be ConfigurationResolution")
        object.__setattr__(self, "requested_seed", _optional_int(self.requested_seed, "requested_seed"))
        effective_seed = _optional_int(self.effective_seed, "effective_seed")
        assert effective_seed is not None
        object.__setattr__(self, "effective_seed", effective_seed)
        if not isinstance(self.status, RunStatus):
            raise TypeError("status must be RunStatus")
        if self.best_key is not None:
            object.__setattr__(self, "best_key", normalize_concrete_key(self.best_key, field_name="best_key"))
        if self.best_score is not None:
            if isinstance(self.best_score, bool) or not isinstance(self.best_score, (int, float)):
                raise TypeError("best_score must be a number or None")
            score = float(self.best_score)
            if not math.isfinite(score):
                raise ValueError("best_score must be finite")
            object.__setattr__(self, "best_score", score)
        for name in ("evaluations", "steps", "tokens_processed"):
            object.__setattr__(self, name, _counter(getattr(self, name), name))
        for name in ("wall_time_seconds", "decrypt_time_seconds", "score_time_seconds"):
            object.__setattr__(self, name, _time(getattr(self, name), name))
        object.__setattr__(self, "details", _mapping(self.details, "details"))

    def to_dict(self) -> JsonObject:
        return {
            "solver": self.solver.value,
            "parameters": self.parameters.to_dict(),
            "requested_seed": self.requested_seed,
            "effective_seed": self.effective_seed,
            "status": self.status.to_json_dict(),
            "best_key": None if self.best_key is None else list(self.best_key),
            "best_score": self.best_score,
            "evaluations": self.evaluations,
            "steps": self.steps,
            "tokens_processed": self.tokens_processed,
            "wall_time_seconds": self.wall_time_seconds,
            "decrypt_time_seconds": self.decrypt_time_seconds,
            "score_time_seconds": self.score_time_seconds,
            "details": dict(self.details),
        }

    def to_json_dict(self) -> JsonObject:
        return self.to_dict()


__all__ = ["ConfigurationResolution", "OracleMode", "OracleReport", "ReproducibilityMetadata", "RunConfigurationReport", "SolverReport"]
