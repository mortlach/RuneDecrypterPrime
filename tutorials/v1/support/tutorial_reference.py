from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tutorials.v1.support.tutorial_benchmark import (
    TutorialRunKind,
    TutorialStopPolicy,
    TutorialTruthPolicy,
    build_tutorial_benchmark_summary,
)


@dataclass(frozen=True, slots=True)
class TutorialReference:
    """Attachable tutorial/benchmark reference data.

    The reference can be created early, passed around a tutorial session, and
    used to build a benchmark summary once a solution exists. Missing reference
    pieces are allowed so tutorial code can stay easy to compose.
    """

    truth_policy: TutorialTruthPolicy | str = TutorialTruthPolicy.NONE
    plaintext_idx: tuple[int, ...] | None = None
    key_idx: tuple[int, ...] | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "truth_policy", _truth_policy(self.truth_policy))
        object.__setattr__(self, "plaintext_idx", _int_tuple(self.plaintext_idx))
        object.__setattr__(self, "key_idx", _int_tuple(self.key_idx))
        if self.label is not None:
            object.__setattr__(self, "label", str(self.label))

    @classmethod
    def none(cls, *, label: str | None = None) -> "TutorialReference":
        return cls(truth_policy=TutorialTruthPolicy.NONE, label=label)

    @classmethod
    def plaintext(
        cls,
        plaintext_idx: Sequence[int] | None = None,
        *,
        label: str | None = None,
    ) -> "TutorialReference":
        return cls(
            truth_policy=TutorialTruthPolicy.KNOWN_PLAINTEXT_REFERENCE,
            plaintext_idx=_int_tuple(plaintext_idx),
            label=label,
        )

    @classmethod
    def key_and_plaintext(
        cls,
        *,
        key_idx: Sequence[int] | None = None,
        plaintext_idx: Sequence[int] | None = None,
        label: str | None = None,
    ) -> "TutorialReference":
        return cls(
            truth_policy=TutorialTruthPolicy.KNOWN_KEY_AND_PLAINTEXT,
            plaintext_idx=_int_tuple(plaintext_idx),
            key_idx=_int_tuple(key_idx),
            label=label,
        )

    def with_plaintext(self, plaintext_idx: Sequence[int]) -> "TutorialReference":
        return TutorialReference(
            truth_policy=self.truth_policy,
            plaintext_idx=_int_tuple(plaintext_idx),
            key_idx=self.key_idx,
            label=self.label,
        )

    def with_key(self, key_idx: Sequence[int]) -> "TutorialReference":
        return TutorialReference(
            truth_policy=self.truth_policy,
            plaintext_idx=self.plaintext_idx,
            key_idx=_int_tuple(key_idx),
            label=self.label,
        )

    def match_ratio(self, solution_or_plaintext: Any) -> float | None:
        found = _solution_plaintext(solution_or_plaintext)
        if found is None or self.plaintext_idx is None:
            return None
        denom = max(len(found), len(self.plaintext_idx))
        if denom == 0:
            return None
        limit = min(len(found), len(self.plaintext_idx))
        return sum(1 for idx in range(limit) if found[idx] == self.plaintext_idx[idx]) / float(denom)

    def key_exact(self, solution_or_key: Any) -> bool | None:
        found = _solution_key(solution_or_key)
        if found is None or self.key_idx is None:
            return None
        return found == self.key_idx

    def build_summary(
        self,
        *,
        run_kind: TutorialRunKind,
        stop_policy: TutorialStopPolicy,
        solution: Any,
    ):
        return build_tutorial_benchmark_summary(
            run_kind=run_kind,
            truth_policy=self.truth_policy,
            stop_policy=stop_policy,
            plaintext_idx=_solution_plaintext(solution),
            reference_idx=self.plaintext_idx,
            score=getattr(solution, "score", None),
            evals=getattr(solution, "evals", None),
            tokens=getattr(solution, "tokens_processed", None),
            wall_time_s=getattr(solution, "wall_time_s", None),
            solver_stop_reason=getattr(solution, "stop_reason", None),
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "truth_policy": self.truth_policy.value,
            "label": self.label,
            "has_plaintext": self.plaintext_idx is not None,
            "has_key": self.key_idx is not None,
        }


def _truth_policy(value: TutorialTruthPolicy | str) -> TutorialTruthPolicy:
    if isinstance(value, TutorialTruthPolicy):
        return value
    try:
        return TutorialTruthPolicy(str(value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in TutorialTruthPolicy)
        raise ValueError(f"unknown tutorial truth policy {value!r}; expected one of: {allowed}") from exc


def _solution_plaintext(value: Any) -> tuple[int, ...] | None:
    plaintext = getattr(value, "plaintext_idx", None)
    if plaintext is None:
        plaintext = getattr(value, "plaintext", value)
    return _int_tuple(plaintext)


def _solution_key(value: Any) -> tuple[int, ...] | None:
    return _int_tuple(getattr(value, "key", value))


def _int_tuple(value: Any) -> tuple[int, ...] | None:
    if value is None or isinstance(value, (str, bytes, Path, Mapping)):
        return None
    try:
        out = tuple(int(item) for item in value)
    except Exception:
        return None
    return out if out else None


__all__ = ["TutorialReference"]
