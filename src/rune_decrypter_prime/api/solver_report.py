from __future__ import annotations

import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from numbers import Integral, Real
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rune_decrypter_prime import rune_decrypter_prime_version
from rune_decrypter_prime.api.stop_reason_contract import (
    CanonicalStopReason,
    ExecutionStatus,
    RUN_STATUS_SCHEMA,
    RunStatus,
    StopCategory,
    build_run_status,
    execution_status_for_category,
    stop_category_for_reason,
)


class SolverReportDetailKey(StrEnum):
    REPORT_CONTRACT = "report_contract"
    ORACLE_USE = "oracle_use"
    TRUTH_DATA_POLICY = "truth_data_policy"
    RUN_STATUS = "run_status"
    ORACLE = "oracle"
    CONFIGURATION = "configuration"
    REPRODUCIBILITY = "reproducibility"
    EXECUTION_ROUTE = "execution_route"
    SCORER_LANES = "scorer_lanes"


class ExecutionRoute(StrEnum):
    KNOWN_KEY_FASTPATH = "known_key_fastpath"


class SolverParamKey(StrEnum):
    TEST_KEY = "test_key"


class SolverStopReason(StrEnum):
    TEST_KEY = "test_key"


class OracleUse(StrEnum):
    NONE = "none"
    TEST_KEY = "test_key"
    KNOWN_KEY_FASTPATH = "known_key_fastpath"


class TruthDataPolicy(StrEnum):
    NONE = "none"
    REPORTED_TEST_OR_TUTORIAL_ONLY = "reported_test_or_tutorial_only"


class OracleMode(StrEnum):
    REAL_SOLVE = "real_solve"
    TUTORIAL = "tutorial"
    TEST = "test"
    BENCHMARK = "benchmark"
    UNKNOWN = "unknown"


class SolverReportDetailsVersion(StrEnum):
    V1 = "api_solver_report_details.v1"


class ReproducibilityKey(StrEnum):
    DETERMINISTIC_SEED_POLICY = "deterministic_seed_policy"
    REQUESTED_SEED = "requested_seed"
    EFFECTIVE_SEED = "effective_seed"
    SOLVER_NAME = "solver_name"
    RUN_ID = "run_id"
    CREATED_AT_UTC = "created_at_utc"
    RDP_VERSION = "rdp_version"
    GIT_BRANCH = "git_branch"
    GIT_COMMIT = "git_commit"
    PYTHON_VERSION = "python_version"
    BACKEND = "backend"
    DEVICE = "device"
    DTYPE = "dtype"
    SEED = "seed"
    STOCHASTIC = "stochastic"
    SOLVER_CONFIG = "solver_config"
    SCORING_CONFIG = "scoring_config"
    OBJECTIVE = "objective"
    CIPHER = "cipher"
    ASSET_IDS = "asset_ids"
    ASSET_HASHES = "asset_hashes"
    DICTIONARY_POLICY = "dictionary_policy"
    STOP_CATEGORY = "stop_category"
    STOP_REASON = "stop_reason"


class DeterministicSeedPolicy(StrEnum):
    EXPLICIT_OR_DEFAULT_ZERO = "explicit_or_default_zero"


@dataclass(frozen=True, slots=True)
class OracleReport:
    available: bool = False
    used_for_scoring: bool = False
    used_for_ranking: bool = False
    used_for_stop: bool = False
    stop_reason: str | None = None
    mode: OracleMode = OracleMode.REAL_SOLVE

    def __post_init__(self) -> None:
        for field_name in ("available", "used_for_scoring", "used_for_ranking", "used_for_stop"):
            if type(getattr(self, field_name)) is not bool:
                raise TypeError(f"{field_name} must be bool")
        if self.stop_reason is not None and not isinstance(self.stop_reason, str):
            raise TypeError("stop_reason must be str or None")
        if not isinstance(self.mode, OracleMode):
            raise TypeError("mode must be OracleMode")
        if (self.used_for_scoring or self.used_for_ranking or self.used_for_stop) and not self.available:
            raise ValueError("oracle use requires available=True")
        if self.used_for_stop and not self.stop_reason:
            raise ValueError("used_for_stop=True requires stop_reason")
        if not self.used_for_stop and self.stop_reason is not None:
            raise ValueError("stop_reason is only valid when used_for_stop=True")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "used_for_scoring": self.used_for_scoring,
            "used_for_ranking": self.used_for_ranking,
            "used_for_stop": self.used_for_stop,
            "stop_reason": self.stop_reason,
            "mode": self.mode.value,
        }


@dataclass(frozen=True, slots=True)
class RequestedEffectiveConfig:
    requested: Mapping[str, Any] = field(default_factory=dict)
    effective: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested", _copy_json_mapping(self.requested, "requested"))
        object.__setattr__(self, "effective", _copy_json_mapping(self.effective, "effective"))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "requested": _to_json_value(self.requested),
            "effective": _to_json_value(self.effective),
        }


@dataclass(frozen=True, slots=True)
class RunConfigurationReport:
    solver: RequestedEffectiveConfig
    scoring: RequestedEffectiveConfig
    cipher: RequestedEffectiveConfig

    def __post_init__(self) -> None:
        for name in ("solver", "scoring", "cipher"):
            if not isinstance(getattr(self, name), RequestedEffectiveConfig):
                raise TypeError(f"{name} must be RequestedEffectiveConfig")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "solver": self.solver.to_json_dict(),
            "scoring": self.scoring.to_json_dict(),
            "cipher": self.cipher.to_json_dict(),
        }


@dataclass(frozen=True, slots=True)
class ReproducibilityMetadata:
    run_id: str | None = None
    created_at_utc: str | None = None
    rdp_version: str = rune_decrypter_prime_version
    git_branch: str | None = None
    git_commit: str | None = None
    python_version: str = sys.version
    backend: str | None = None
    device: str | None = None
    dtype: str | None = None
    seed: int | None = None
    stochastic: bool | None = None
    solver_config: Mapping[str, Any] | None = None
    scoring_config: Mapping[str, Any] | None = None
    objective: Mapping[str, Any] | str | None = None
    cipher: Mapping[str, Any] | str | None = None
    asset_ids: Sequence[str] | None = None
    asset_hashes: Mapping[str, str] | None = None
    dictionary_policy: str | None = None
    stop_category: StopCategory | None = None
    stop_reason: CanonicalStopReason | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "run_id", "created_at_utc", "rdp_version", "git_branch", "git_commit",
            "python_version", "backend", "device", "dtype", "dictionary_policy",
        ):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{field_name} must be str or None")
        if self.stop_category is not None and not isinstance(self.stop_category, StopCategory):
            raise TypeError("stop_category must be StopCategory or None")
        if self.stop_reason is not None and not isinstance(self.stop_reason, CanonicalStopReason):
            raise TypeError("stop_reason must be CanonicalStopReason or None")
        if self.stop_category is not None and self.stop_reason is not None:
            expected = stop_category_for_reason(self.stop_reason.value)
            if self.stop_category is not expected:
                raise ValueError("stop_category must match stop_reason")
        if self.seed is not None:
            object.__setattr__(self, "seed", _require_optional_int(self.seed, "seed"))
        if self.stochastic is not None and type(self.stochastic) is not bool:
            raise TypeError("stochastic must be bool or None")
        for field_name in ("solver_config", "scoring_config"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _copy_json_mapping(value, field_name))
        if isinstance(self.objective, Mapping):
            object.__setattr__(self, "objective", _copy_json_mapping(self.objective, "objective"))
        elif self.objective is not None and not isinstance(self.objective, str):
            raise TypeError("objective must be mapping, str, or None")
        if isinstance(self.cipher, Mapping):
            object.__setattr__(self, "cipher", _copy_json_mapping(self.cipher, "cipher"))
        elif self.cipher is not None and not isinstance(self.cipher, str):
            raise TypeError("cipher must be mapping, str, or None")
        if self.asset_ids is not None:
            if isinstance(self.asset_ids, (str, bytes, Path)):
                raise TypeError("asset_ids must be a sequence of strings or None")
            ids = tuple(self.asset_ids)
            if any(not isinstance(value, str) for value in ids):
                raise TypeError("asset_ids entries must be strings")
            object.__setattr__(self, "asset_ids", ids)
        if self.asset_hashes is not None:
            hashes = _copy_json_mapping(self.asset_hashes, "asset_hashes")
            if any(not isinstance(value, str) for value in hashes.values()):
                raise TypeError("asset_hashes values must be strings")
            object.__setattr__(self, "asset_hashes", hashes)

    def to_json_dict(self) -> dict[str, object]:
        return {
            ReproducibilityKey.RUN_ID.value: self.run_id,
            ReproducibilityKey.CREATED_AT_UTC.value: self.created_at_utc,
            ReproducibilityKey.RDP_VERSION.value: self.rdp_version,
            ReproducibilityKey.GIT_BRANCH.value: self.git_branch,
            ReproducibilityKey.GIT_COMMIT.value: self.git_commit,
            ReproducibilityKey.PYTHON_VERSION.value: self.python_version,
            ReproducibilityKey.BACKEND.value: self.backend,
            ReproducibilityKey.DEVICE.value: self.device,
            ReproducibilityKey.DTYPE.value: self.dtype,
            ReproducibilityKey.SEED.value: self.seed,
            ReproducibilityKey.STOCHASTIC.value: self.stochastic,
            ReproducibilityKey.SOLVER_CONFIG.value: _to_json_value(self.solver_config),
            ReproducibilityKey.SCORING_CONFIG.value: _to_json_value(self.scoring_config),
            ReproducibilityKey.OBJECTIVE.value: _to_json_value(self.objective),
            ReproducibilityKey.CIPHER.value: _to_json_value(self.cipher),
            ReproducibilityKey.ASSET_IDS.value: None if self.asset_ids is None else list(self.asset_ids),
            ReproducibilityKey.ASSET_HASHES.value: _to_json_value(self.asset_hashes),
            ReproducibilityKey.DICTIONARY_POLICY.value: self.dictionary_policy,
            ReproducibilityKey.STOP_CATEGORY.value: None if self.stop_category is None else self.stop_category.value,
            ReproducibilityKey.STOP_REASON.value: None if self.stop_reason is None else self.stop_reason.value,
        }


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
        object.__setattr__(self, "requested_seed", _require_optional_int(self.requested_seed, "requested_seed"))
        object.__setattr__(self, "effective_seed", _require_optional_int(self.effective_seed, "effective_seed"))
        object.__setattr__(self, "normalized_params", _copy_json_mapping(self.normalized_params, "normalized_params"))
        object.__setattr__(self, "stop_reason", _require_optional_text(self.stop_reason, "stop_reason"))
        object.__setattr__(self, "best_score", _require_optional_finite_float(self.best_score, "best_score"))
        object.__setattr__(self, "best_key", _copy_best_key(self.best_key))
        object.__setattr__(self, "step", _require_optional_counter(self.step, "step"))
        object.__setattr__(self, "evals", _require_optional_counter(self.evals, "evals"))
        object.__setattr__(self, "tokens_processed", _require_optional_counter(self.tokens_processed, "tokens_processed"))
        object.__setattr__(self, "wall_time_s", _require_optional_nonnegative_float(self.wall_time_s, "wall_time_s"))
        object.__setattr__(self, "decrypt_time_s", _require_optional_nonnegative_float(self.decrypt_time_s, "decrypt_time_s"))
        object.__setattr__(self, "score_time_s", _require_optional_nonnegative_float(self.score_time_s, "score_time_s"))
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
    run_status: RunStatus | None = None,
    oracle: OracleReport | None = None,
    configuration: RunConfigurationReport | None = None,
    reproducibility: ReproducibilityMetadata | None = None,
) -> SolverReport:
    if isinstance(normalized_params, Mapping) and "name" in normalized_params:
        raise ValueError('normalized_params must not include "name"')
    merged_details = _solver_report_contract_details(
        solver_name=solver_name,
        requested_seed=requested_seed,
        effective_seed=effective_seed,
        normalized_params=normalized_params,
        stop_reason=stop_reason,
        details=details,
        run_status=run_status,
        oracle=oracle,
        configuration=configuration,
        reproducibility=reproducibility,
    )
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
        details=merged_details,
    )


RESERVED_CONTRACT_DETAIL_KEYS = frozenset(
    key.value
    for key in (
        SolverReportDetailKey.REPORT_CONTRACT,
        SolverReportDetailKey.ORACLE_USE,
        SolverReportDetailKey.TRUTH_DATA_POLICY,
        SolverReportDetailKey.RUN_STATUS,
        SolverReportDetailKey.ORACLE,
        SolverReportDetailKey.CONFIGURATION,
        SolverReportDetailKey.REPRODUCIBILITY,
    )
)


def _solver_report_contract_details(
    *,
    solver_name: str,
    requested_seed: int | None,
    effective_seed: int | None,
    normalized_params: Mapping[str, Any],
    stop_reason: str | None,
    details: Mapping[str, Any] | None,
    run_status: RunStatus | None,
    oracle: OracleReport | None,
    configuration: RunConfigurationReport | None,
    reproducibility: ReproducibilityMetadata | None,
) -> dict[str, Any]:
    out = dict(details or {})
    blocked = RESERVED_CONTRACT_DETAIL_KEYS.intersection(out)
    if blocked:
        keys = ", ".join(sorted(blocked))
        raise ValueError(f"details cannot overwrite generated solver-report contract section(s): {keys}")

    oracle_use, truth_data_policy = _oracle_use_details(
        normalized_params=normalized_params,
        stop_reason=stop_reason,
        existing_details=out,
    )
    if run_status is None:
        if oracle_use is OracleUse.KNOWN_KEY_FASTPATH:
            run_status = RunStatus(
                execution_status=ExecutionStatus.COMPLETED,
                stop_category=StopCategory.SUCCESS,
                stop_reason=CanonicalStopReason.KNOWN_KEY_EXECUTION_COMPLETED,
                legacy_reason=stop_reason,
            )
        elif oracle_use is OracleUse.TEST_KEY:
            run_status = RunStatus(
                execution_status=ExecutionStatus.COMPLETED,
                stop_category=StopCategory.SUCCESS,
                stop_reason=CanonicalStopReason.ORACLE_TEST_KEY_USED,
                legacy_reason=stop_reason,
            )
        else:
            category = stop_category_for_reason(stop_reason)
            run_status = build_run_status(
                legacy_reason=stop_reason,
                execution_status=execution_status_for_category(category),
            )
    if oracle is None:
        oracle = _canonical_oracle_report(
            oracle_use=oracle_use,
            stop_reason=run_status.stop_reason.value,
        )
    if configuration is None:
        solver_config = RequestedEffectiveConfig(
            requested={"name": solver_name, "params": dict(normalized_params), "seed": requested_seed},
            effective={"name": solver_name, "params": dict(normalized_params), "seed": effective_seed},
        )
        configuration = RunConfigurationReport(
            solver=solver_config,
            scoring=RequestedEffectiveConfig(),
            cipher=RequestedEffectiveConfig(),
        )
    if reproducibility is None:
        reproducibility = ReproducibilityMetadata(
            seed=effective_seed,
            stochastic=None,
            solver_config=configuration.solver.to_json_dict(),
            scoring_config=configuration.scoring.to_json_dict(),
            stop_category=run_status.stop_category,
            stop_reason=run_status.stop_reason,
        )

    repro_payload = reproducibility.to_json_dict()
    # Preserve the established V1 seed breadcrumbs while adding the complete June mapping.
    repro_payload.update({
        ReproducibilityKey.DETERMINISTIC_SEED_POLICY.value: DeterministicSeedPolicy.EXPLICIT_OR_DEFAULT_ZERO.value,
        ReproducibilityKey.REQUESTED_SEED.value: requested_seed,
        ReproducibilityKey.EFFECTIVE_SEED.value: effective_seed,
        ReproducibilityKey.SOLVER_NAME.value: str(solver_name),
    })

    oracle_payload = oracle.to_json_dict()
    run_status_payload = run_status.to_json_dict()
    run_status_payload.update({
        "schema": RUN_STATUS_SCHEMA,
        "oracle": oracle_payload,
        "reproducibility": repro_payload,
    })

    out[SolverReportDetailKey.REPORT_CONTRACT.value] = {"version": SolverReportDetailsVersion.V1.value}
    out[SolverReportDetailKey.ORACLE_USE.value] = oracle_use.value
    out[SolverReportDetailKey.TRUTH_DATA_POLICY.value] = truth_data_policy.value
    out[SolverReportDetailKey.RUN_STATUS.value] = run_status_payload
    out[SolverReportDetailKey.ORACLE.value] = oracle_payload
    out[SolverReportDetailKey.CONFIGURATION.value] = configuration.to_json_dict()
    out[SolverReportDetailKey.REPRODUCIBILITY.value] = repro_payload
    return out


def _oracle_use_details(
    *,
    normalized_params: Mapping[str, Any],
    stop_reason: str | None,
    existing_details: Mapping[str, Any],
) -> tuple[OracleUse, TruthDataPolicy]:
    if existing_details.get(SolverReportDetailKey.EXECUTION_ROUTE.value) == ExecutionRoute.KNOWN_KEY_FASTPATH.value:
        # Preserve the established V1 compatibility contract: the known-key
        # fast path is explicit test/tutorial truth use, never an ordinary
        # real-solve handoff.
        return OracleUse.KNOWN_KEY_FASTPATH, TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY
    reason = "" if stop_reason is None else str(stop_reason).strip().lower()
    has_test_key = isinstance(normalized_params, Mapping) and SolverParamKey.TEST_KEY.value in normalized_params
    if has_test_key or reason == SolverStopReason.TEST_KEY.value:
        return OracleUse.TEST_KEY, TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY
    return OracleUse.NONE, TruthDataPolicy.NONE


def _canonical_oracle_report(*, oracle_use: OracleUse, stop_reason: str) -> OracleReport:
    if oracle_use is OracleUse.TEST_KEY:
        return OracleReport(
            available=True,
            used_for_scoring=False,
            used_for_ranking=False,
            used_for_stop=True,
            stop_reason=stop_reason,
            mode=OracleMode.TEST,
        )
    if oracle_use is OracleUse.KNOWN_KEY_FASTPATH:
        return OracleReport(
            available=True,
            used_for_scoring=False,
            used_for_ranking=False,
            used_for_stop=True,
            stop_reason=stop_reason,
            mode=OracleMode.UNKNOWN,
        )
    return OracleReport(mode=OracleMode.REAL_SOLVE)


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


__all__ = [
    "DeterministicSeedPolicy",
    "ExecutionRoute",
    "OracleMode",
    "OracleReport",
    "OracleUse",
    "ReproducibilityKey",
    "ReproducibilityMetadata",
    "RequestedEffectiveConfig",
    "RunConfigurationReport",
    "SolverParamKey",
    "SolverReport",
    "SolverReportDetailKey",
    "SolverReportDetailsVersion",
    "SolverStopReason",
    "TruthDataPolicy",
    "build_solver_report",
]
