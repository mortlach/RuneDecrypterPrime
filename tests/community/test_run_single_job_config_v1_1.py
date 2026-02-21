from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.benchmarks.community import _run_single_job as rsj

pytestmark = pytest.mark.tier_a


@dataclass(frozen=True)
class _Tier:
    name: str
    period: int
    columns: int
    length: int


def test_configure_module_for_campaign_disables_autoskip_and_applies_profile():
    module = SimpleNamespace(
        AUTOSKIP_PROVEN=True,
        FORCE_RERUN_PROVEN=False,
        AVOID_REPEAT_FAIL=True,
        KEY_SEEDS_OVERRIDE=None,
        KEY_SEEDS=[111],
        TEXT_OFFSETS=[0],
        PIPELINE_RUN_MODE="focus_p10_fast_resume",
        PROFILE="old_profile",
        HEARTBEAT_SECONDS=1200,
        Tier=_Tier,
        TIERS=[_Tier("old", 10, 3, 2376)],
        STAGE3_FULL_ENTRY_SCORE=0.1,
        STAGE3_PROBE_ENTRY_SCORE=0.06,
        STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS={3: 0.1},
        STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS={3: 0.06},
        STAGE12_PROMOTE_TOP=8,
        STAGE12_ARCHIVE_KEEP=24,
        STAGE1_SUB_CANDIDATES_BY_COLUMNS={3: 10},
        STAGE3_INITIAL_KEYS_BY_COLUMNS={3: 12},
        SOLVER_STAGE1={"steps": 10},
        SOLVER_STAGE2={"rounds": 2},
        SOLVER_STAGE3={"steps": 20},
    )
    job = {
        "order": "col_then_sub",
        "run_seed": 222,
        "period": 10,
        "columns": 7,
        "text_fixture_id": "fixture_001",
        "profile_id": "stage3_fullband_basin_v1_1",
    }
    campaign_config = {
        "fixtures": [{"text_fixture_id": "fixture_001", "length": 1234}],
    }
    profile_catalog = {
        "profiles": [
            {
                "profile_id": "stage3_fullband_basin_v1_1",
                "overrides": {
                    "stage3_gating": {"full_entry_score": None, "probe_entry_score": None},
                    "stage12_carry_through": {"promote_top": 16, "archive_keep": 32},
                    "stage1_breadth": {"sub_candidates_by_columns": {"7": 24}},
                    "stage3_basin_exploration": {"initial_keys_by_columns": {"7": 40}},
                },
            }
        ]
    }

    rsj._configure_module_for_campaign_job(
        module=module,
        job=job,
        campaign_config=campaign_config,
        profile_catalog=profile_catalog,
        repo_root=Path.cwd(),
    )

    assert module.AUTOSKIP_PROVEN is False
    assert module.FORCE_RERUN_PROVEN is True
    assert module.AVOID_REPEAT_FAIL is False
    assert module.KEY_SEEDS_OVERRIDE == [222]
    assert module.KEY_SEEDS == [222]
    assert module.STAGE3_FULL_ENTRY_SCORE is None
    assert module.STAGE3_PROBE_ENTRY_SCORE is None
    assert module.STAGE12_PROMOTE_TOP == 16
    assert module.STAGE12_ARCHIVE_KEEP == 32
    assert module.STAGE1_SUB_CANDIDATES_BY_COLUMNS[7] == 24
    assert module.STAGE3_INITIAL_KEYS_BY_COLUMNS[7] == 40
    assert len(module.TIERS) == 1
    assert module.TIERS[0].period == 10
    assert module.TIERS[0].columns == 7
    assert module.TIERS[0].length == 1234
