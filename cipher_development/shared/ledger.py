from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rune_decrypter_prime.api.stop_reason_contract import STOP_CATEGORIES

SCHEMA = "rdp_cipher_development_experiment_ledger.v1"
_STATUSES = {"completed", "failed"}
_DECISIONS = {"promote", "refine", "close"}
_WLI_MODES = {"with_wli", "without_wli"}
_TRUTH_POLICIES = {"benchmark_only", "none"}
_MECHANISMS = {
    "contract", "objective", "candidate_supply", "diversity_collapse", "ranking",
    "handoff", "exploitation", "acceptance", "budget", "evidence_reproducibility",
}
_LESSON_ID_RE = re.compile(r"^CSL-[0-9]{3}$")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _choice(value: Any, name: str, allowed: set[str] | frozenset[str]) -> str:
    value = _text(value, name)
    if value not in allowed:
        raise ValueError(f"{name} must be one of {sorted(allowed)}")
    return value


def _json_value(value: Any, name: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name} contains a non-finite float")
        return float(value)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise TypeError(f"{name} mapping keys must be non-empty strings")
            out[key] = _json_value(item, f"{name}.{key}")
        return out
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{name}[]") for item in value]
    raise TypeError(f"{name} must contain only JSON-compatible values")


def _relpath(value: Any) -> str:
    text = _text(value, "result_relpath")
    path = Path(text)
    if "\\" in text or path.is_absolute() or ".." in path.parts:
        raise ValueError("result_relpath must be a campaign-relative POSIX path")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class ExperimentLedgerRow:
    schema: str
    recorded_at: str
    run_id: str
    campaign_id: str
    experiment_id: str
    benchmark_id: str
    question: str
    hypothesis: str
    alternative: str
    configuration_hash: str
    wli_mode: str
    truth_policy: str
    mechanisms: tuple[str, ...] = ()
    budget_seconds: float | None = None
    budget_evaluations: int | None = None
    lesson_ids: tuple[str, ...] = ()
    status: str = "completed"
    decision: str | None = None
    stop_category: str = "not_started"
    stop_reason: str = "not_started"
    elapsed_s: float = 0.0
    telemetry: Mapping[str, Any] = field(default_factory=dict)
    result_summary: Mapping[str, Any] = field(default_factory=dict)
    result_relpath: str = ""
    git_commit: str | None = None
    git_dirty: bool | None = None

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError(f"schema must be {SCHEMA!r}")
        for name in (
            "recorded_at", "run_id", "campaign_id", "experiment_id", "benchmark_id",
            "question", "hypothesis", "alternative", "configuration_hash", "stop_reason",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))

        object.__setattr__(self, "wli_mode", _choice(self.wli_mode, "wli_mode", _WLI_MODES))
        object.__setattr__(self, "truth_policy", _choice(
            self.truth_policy, "truth_policy", _TRUTH_POLICIES
        ))
        mechanisms = tuple(_choice(item, "mechanisms[]", _MECHANISMS) for item in self.mechanisms)
        if len(set(mechanisms)) != len(mechanisms):
            raise ValueError("mechanisms must not contain duplicates")
        object.__setattr__(self, "mechanisms", mechanisms)

        if self.budget_seconds is not None:
            if isinstance(self.budget_seconds, bool):
                raise TypeError("budget_seconds must be a positive finite float or None")
            seconds = float(self.budget_seconds)
            if not math.isfinite(seconds) or seconds <= 0:
                raise ValueError("budget_seconds must be a positive finite float or None")
            object.__setattr__(self, "budget_seconds", seconds)
        if self.budget_evaluations is not None:
            evaluations = self.budget_evaluations
            if isinstance(evaluations, bool) or not isinstance(evaluations, int):
                raise TypeError("budget_evaluations must be a positive integer or None")
            if evaluations <= 0:
                raise ValueError("budget_evaluations must be a positive integer or None")
        lesson_ids = tuple(_text(item, "lesson_ids[]") for item in self.lesson_ids)
        if any(not _LESSON_ID_RE.fullmatch(item) for item in lesson_ids):
            raise ValueError("lesson_ids must use the CSL-NNN format")
        if len(set(lesson_ids)) != len(lesson_ids):
            raise ValueError("lesson_ids must be unique")
        object.__setattr__(self, "lesson_ids", lesson_ids)

        status = _choice(self.status, "status", _STATUSES)
        decision = None if self.decision is None else _choice(self.decision, "decision", _DECISIONS)
        if status == "completed" and decision is None:
            raise ValueError("completed ledger rows require a decision")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "stop_category", _choice(
            self.stop_category, "stop_category", STOP_CATEGORIES
        ))

        if isinstance(self.elapsed_s, bool):
            raise TypeError("elapsed_s must be a non-negative finite float")
        elapsed = float(self.elapsed_s)
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("elapsed_s must be a non-negative finite float")
        object.__setattr__(self, "elapsed_s", elapsed)

        if not isinstance(self.telemetry, Mapping) or not isinstance(self.result_summary, Mapping):
            raise TypeError("telemetry and result_summary must be mappings")
        object.__setattr__(self, "telemetry", _json_value(self.telemetry, "telemetry"))
        object.__setattr__(self, "result_summary", _json_value(self.result_summary, "result_summary"))
        object.__setattr__(self, "result_relpath", _relpath(self.result_relpath))
        if self.git_commit is not None:
            object.__setattr__(self, "git_commit", _text(self.git_commit, "git_commit"))
        if self.git_dirty is not None and type(self.git_dirty) is not bool:
            raise TypeError("git_dirty must be bool or None")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "recorded_at": self.recorded_at, "run_id": self.run_id,
            "campaign_id": self.campaign_id, "experiment_id": self.experiment_id,
            "benchmark_id": self.benchmark_id, "question": self.question,
            "hypothesis": self.hypothesis, "alternative": self.alternative,
            "configuration_hash": self.configuration_hash, "wli_mode": self.wli_mode,
            "truth_policy": self.truth_policy, "mechanisms": list(self.mechanisms),
            "budget_seconds": self.budget_seconds,
            "budget_evaluations": self.budget_evaluations,
            "lesson_ids": list(self.lesson_ids),
            "status": self.status, "decision": self.decision,
            "stop_category": self.stop_category, "stop_reason": self.stop_reason,
            "elapsed_s": self.elapsed_s, "telemetry": dict(self.telemetry),
            "result_summary": dict(self.result_summary), "result_relpath": self.result_relpath,
            "git_commit": self.git_commit, "git_dirty": self.git_dirty,
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "ExperimentLedgerRow":
        if not isinstance(payload, Mapping):
            raise TypeError("ledger row must be a mapping")
        return cls(**dict(payload))


def append_ledger_row(path: Path, row: ExperimentLedgerRow) -> None:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    if not isinstance(row, ExperimentLedgerRow):
        raise TypeError("row must be an ExperimentLedgerRow")
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row.to_json_dict(), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False) + "\n"
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(line)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass


def read_ledger(path: Path) -> tuple[ExperimentLedgerRow, ...]:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    if not path.exists():
        return ()
    rows: list[ExperimentLedgerRow] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"blank ledger line at line {number}")
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed ledger JSON at line {number}: {exc.msg}") from exc
            try:
                rows.append(ExperimentLedgerRow.from_json_dict(payload))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid ledger row at line {number}: {exc}") from exc
    return tuple(rows)


__all__ = ["ExperimentLedgerRow", "append_ledger_row", "read_ledger"]
