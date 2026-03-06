from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.common.campaign_run_config import (
    build_campaign_run_config,
)


pytestmark = pytest.mark.tier_a


def test_build_campaign_run_config_normalizes_and_types_fields():
    cfg = build_campaign_run_config(
        run_seed="123",
        period="7",
        columns="3",
        length="1000",
        tier_name="tier_a",
        run_mode="full",
        profile_name="profile_x",
        heartbeat_seconds="3600",
        autoskip_proven=1,
        force_rerun_proven=0,
        avoid_repeat_fail=True,
        text_offsets=[0, "10"],
        tiers_regex_override="  ",
        scorer_impl="  numpy  ",
        scorer_stage3_impl_avg_fulltext="  torch ",
        scorer_schedule={"early": "stage1_default_char1_only"},
    )

    assert cfg.run_seed == 123
    assert cfg.period == 7
    assert cfg.columns == 3
    assert cfg.length == 1000
    assert cfg.heartbeat_seconds == 3600
    assert cfg.autoskip_proven is True
    assert cfg.force_rerun_proven is False
    assert cfg.avoid_repeat_fail is True
    assert cfg.text_offsets == (0, 10)
    assert cfg.tiers_regex_override is None
    assert cfg.scorer_impl == "numpy"
    assert cfg.scorer_stage3_impl_avg_fulltext == "torch"
    assert cfg.scorer_schedule == {"early": "stage1_default_char1_only"}


def test_build_campaign_run_config_rejects_non_mapping_schedule():
    with pytest.raises(ValueError, match="scorer_schedule must be a mapping"):
        build_campaign_run_config(
            run_seed=1,
            period=7,
            columns=3,
            length=1000,
            tier_name="tier_a",
            run_mode="full",
            profile_name="profile_x",
            heartbeat_seconds=3600,
            autoskip_proven=False,
            force_rerun_proven=True,
            avoid_repeat_fail=False,
            text_offsets=[0],
            tiers_regex_override=None,
            scorer_schedule=["bad"],  # type: ignore[arg-type]
        )


def test_campaign_run_config_tier_builder():
    cfg = build_campaign_run_config(
        run_seed=1,
        period=7,
        columns=3,
        length=1000,
        tier_name="tier_a",
        run_mode="full",
        profile_name="profile_x",
        heartbeat_seconds=3600,
        autoskip_proven=False,
        force_rerun_proven=True,
        avoid_repeat_fail=False,
        text_offsets=[0],
        tiers_regex_override=None,
    )

    tier = cfg.tier()
    assert tier.name == "tier_a"
    assert tier.period == 7
    assert tier.columns == 3
    assert tier.length == 1000

