from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FixtureSpec:
    fixture_id: str
    length: int
    source_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": str(self.fixture_id),
            "length": int(self.length),
            "source_path": (None if self.source_path is None else str(self.source_path)),
        }


@dataclass(frozen=True)
class NoWliFixtureJob:
    fixture_id: str
    period: int
    columns: int
    length: int
    run_seed: int
    run_mode: str
    profile_id: str
    heartbeat_seconds: int
    text_offsets: tuple[int, ...]
    scorer_impl: str
    scorer_stage3_impl_avg_fulltext: str
    scoring_experiment_profile: str
    schedule_early: str
    schedule_middle: str
    schedule_late: str
    stage3_tuning_preset_id: str = "base"
    span_ab_case_id: str = "none"
    span_decision_role_enabled: bool = False

    def scorer_schedule(self) -> dict[str, str]:
        return {
            "early": str(self.schedule_early),
            "middle": str(self.schedule_middle),
            "late": str(self.schedule_late),
        }

    def tier_name(self) -> str:
        return (
            f"fixture_{self.fixture_id}_p{int(self.period)}"
            f"_c{int(self.columns)}_l{int(self.length)}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": str(self.fixture_id),
            "period": int(self.period),
            "columns": int(self.columns),
            "length": int(self.length),
            "run_seed": int(self.run_seed),
            "run_mode": str(self.run_mode),
            "profile_id": str(self.profile_id),
            "heartbeat_seconds": int(self.heartbeat_seconds),
            "text_offsets": [int(x) for x in self.text_offsets],
            "scorer_impl": str(self.scorer_impl),
            "scorer_stage3_impl_avg_fulltext": str(self.scorer_stage3_impl_avg_fulltext),
            "scoring_experiment_profile": str(self.scoring_experiment_profile),
            "stage3_tuning_preset_id": str(self.stage3_tuning_preset_id),
            "span_ab_case_id": str(self.span_ab_case_id),
            "span_decision_role_enabled": bool(self.span_decision_role_enabled),
            "scorer_schedule": self.scorer_schedule(),
            "tier_name": self.tier_name(),
        }
