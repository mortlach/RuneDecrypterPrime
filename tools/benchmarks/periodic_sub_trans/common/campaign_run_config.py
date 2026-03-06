from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .runner_types import Tier


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _normalize_optional_mapping(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("scorer_schedule must be a mapping when provided")
    return {str(k): v for k, v in value.items()}


@dataclass(frozen=True)
class CampaignRunConfig:
    """Canonical config payload used by runner configure_campaign_run entrypoints."""

    run_seed: int
    period: int
    columns: int
    length: int
    tier_name: str
    run_mode: str
    profile_name: str
    heartbeat_seconds: int
    autoskip_proven: bool
    force_rerun_proven: bool
    avoid_repeat_fail: bool
    text_offsets: tuple[int, ...]
    tiers_regex_override: str | None
    scorer_impl: str | None
    scorer_stage3_impl_avg_fulltext: str | None
    scorer_schedule: dict[str, Any] | None

    def tier(self) -> Tier:
        return Tier(
            str(self.tier_name),
            int(self.period),
            int(self.columns),
            int(self.length),
        )


def build_campaign_run_config(
    *,
    run_seed: int,
    period: int,
    columns: int,
    length: int,
    tier_name: str,
    run_mode: str,
    profile_name: str,
    heartbeat_seconds: int,
    autoskip_proven: bool,
    force_rerun_proven: bool,
    avoid_repeat_fail: bool,
    text_offsets: Sequence[int],
    tiers_regex_override: str | None,
    scorer_impl: str | None = None,
    scorer_stage3_impl_avg_fulltext: str | None = None,
    scorer_schedule: Mapping[str, Any] | None = None,
) -> CampaignRunConfig:
    return CampaignRunConfig(
        run_seed=int(run_seed),
        period=int(period),
        columns=int(columns),
        length=int(length),
        tier_name=str(tier_name),
        run_mode=str(run_mode),
        profile_name=str(profile_name),
        heartbeat_seconds=int(heartbeat_seconds),
        autoskip_proven=bool(autoskip_proven),
        force_rerun_proven=bool(force_rerun_proven),
        avoid_repeat_fail=bool(avoid_repeat_fail),
        text_offsets=tuple(int(x) for x in text_offsets),
        tiers_regex_override=_normalize_optional_text(tiers_regex_override),
        scorer_impl=_normalize_optional_text(scorer_impl),
        scorer_stage3_impl_avg_fulltext=_normalize_optional_text(
            scorer_stage3_impl_avg_fulltext
        ),
        scorer_schedule=_normalize_optional_mapping(scorer_schedule),
    )

