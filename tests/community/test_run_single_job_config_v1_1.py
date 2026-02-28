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


class _ConfigurableModule(SimpleNamespace):
    def configure_campaign_run(self, **kwargs: object) -> None:
        self._cfg = dict(kwargs)
        self.AUTOSKIP_PROVEN = bool(kwargs["autoskip_proven"])
        self.FORCE_RERUN_PROVEN = bool(kwargs["force_rerun_proven"])
        self.AVOID_REPEAT_FAIL = bool(kwargs["avoid_repeat_fail"])
        self.KEY_SEEDS_OVERRIDE = [int(kwargs["run_seed"])]
        self.KEY_SEEDS = [int(kwargs["run_seed"])]
        self.TEXT_OFFSETS = [int(x) for x in kwargs["text_offsets"]]  # type: ignore[index]
        self.PIPELINE_RUN_MODE = str(kwargs["run_mode"])
        self.PROFILE = str(kwargs["profile_name"])
        self.HEARTBEAT_SECONDS = int(kwargs["heartbeat_seconds"])
        self.TIERS = [
            _Tier(
                str(kwargs["tier_name"]),
                int(kwargs["period"]),
                int(kwargs["columns"]),
                int(kwargs["length"]),
            )
        ]
        impl = str(kwargs.get("scorer_impl", "")).strip()
        if impl:
            for attr in (
                "SCORER_STAGE1",
                "SCORER_STAGE1_HARD_RERANK",
                "SCORER_STAGE2",
                "SCORER_FULL",
                "SCORER_SUB",
            ):
                cfg = getattr(self, attr, None)
                if isinstance(cfg, dict):
                    cfg["impl"] = impl
            profiles = getattr(self, "STAGEAB_SCORER_PROFILES", None)
            if isinstance(profiles, dict):
                for cfg in profiles.values():
                    if isinstance(cfg, dict):
                        cfg["impl"] = impl
            if hasattr(self, "SCORER_IMPL"):
                self.SCORER_IMPL = impl
            if hasattr(self, "SCORER_STAGE3_IMPL_AVG_FULLTEXT"):
                self.SCORER_STAGE3_IMPL_AVG_FULLTEXT = impl


def test_configure_module_for_campaign_disables_autoskip_and_applies_profile():
    module = _ConfigurableModule(
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
    assert module._cfg["tier_name"] == "community_col_then_sub_p10_c7_l1234"
    assert module._cfg["run_mode"] == "full"


def test_configure_module_for_campaign_forces_numpy_scorer_impl():
    module = _ConfigurableModule(
        AUTOSKIP_PROVEN=True,
        FORCE_RERUN_PROVEN=False,
        AVOID_REPEAT_FAIL=True,
        KEY_SEEDS_OVERRIDE=None,
        KEY_SEEDS=[111],
        TEXT_OFFSETS=[0],
        PIPELINE_RUN_MODE="focus_p10_fast_resume",
        PROFILE="old_profile",
        HEARTBEAT_SECONDS=1200,
        SCORER_IMPL="torch",
        SCORER_STAGE3_IMPL_AVG_FULLTEXT="torch",
        SCORER_STAGE1={"impl": "torch"},
        SCORER_STAGE1_HARD_RERANK={"impl": "torch"},
        SCORER_FULL={"impl": "torch"},
        SCORER_SUB={"impl": "torch"},
        STAGEAB_SCORER_PROFILE="A_CHAR34_WLI34",
        STAGEAB_SCORER_PROFILES={
            "A_CHAR1": {"impl": "torch"},
            "A_CHAR34_WLI34": {"impl": "torch"},
        },
        Tier=_Tier,
        TIERS=[_Tier("old", 10, 3, 2376)],
    )
    job = {
        "order": "sub_then_col",
        "run_seed": 222,
        "period": 10,
        "columns": 7,
        "text_fixture_id": "fixture_001",
        "profile_id": "baseline_resume_v1_1",
    }
    campaign_config = {"fixtures": [{"text_fixture_id": "fixture_001", "length": 1234}]}
    profile_catalog = {
        "profiles": [
            {
                "profile_id": "baseline_resume_v1_1",
                "overrides": {},
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

    assert module.SCORER_IMPL == "numpy"
    assert module.SCORER_STAGE3_IMPL_AVG_FULLTEXT == "numpy"
    assert module.SCORER_STAGE1["impl"] == "numpy"
    assert module.SCORER_STAGE1_HARD_RERANK["impl"] == "numpy"
    assert module.SCORER_FULL["impl"] == "numpy"
    assert module.SCORER_SUB["impl"] == "numpy"
    assert module.STAGEAB_SCORER_PROFILES["A_CHAR1"]["impl"] == "numpy"
    assert module.STAGEAB_SCORER_PROFILES["A_CHAR34_WLI34"]["impl"] == "numpy"


def test_configure_module_for_campaign_requires_runner_entrypoint():
    module = SimpleNamespace()
    job = {
        "order": "col_then_sub",
        "run_seed": 222,
        "period": 10,
        "columns": 7,
        "text_fixture_id": "fixture_001",
        "profile_id": "baseline_resume_v1_1",
    }
    campaign_config = {"fixtures": [{"text_fixture_id": "fixture_001", "length": 1234}]}
    profile_catalog = {
        "profiles": [
            {
                "profile_id": "baseline_resume_v1_1",
                "overrides": {},
            }
        ]
    }

    with pytest.raises(ValueError, match="configure_campaign_run"):
        rsj._configure_module_for_campaign_job(
            module=module,
            job=job,
            campaign_config=campaign_config,
            profile_catalog=profile_catalog,
            repo_root=Path.cwd(),
        )


def test_configure_module_for_campaign_uses_runner_config_entrypoint_when_available():
    calls: list[dict[str, object]] = []

    class _Module:
        def configure_campaign_run(self, **kwargs: object) -> None:
            calls.append(dict(kwargs))

    module = _Module()
    job = {
        "order": "col_then_sub",
        "run_seed": 222,
        "period": 10,
        "columns": 7,
        "text_fixture_id": "fixture_001",
        "profile_id": "baseline_resume_v1_1",
    }
    campaign_config = {"fixtures": [{"text_fixture_id": "fixture_001", "length": 1234}]}
    profile_catalog = {
        "profiles": [
            {
                "profile_id": "baseline_resume_v1_1",
                "overrides": {},
            }
        ]
    }

    rsj._configure_module_for_campaign_job(
        module=module,  # type: ignore[arg-type]
        job=job,
        campaign_config=campaign_config,
        profile_catalog=profile_catalog,
        repo_root=Path.cwd(),
    )

    assert len(calls) == 1
    cfg = calls[0]
    assert cfg["run_seed"] == 222
    assert cfg["period"] == 10
    assert cfg["columns"] == 7
    assert cfg["length"] == 1234
    assert cfg["tier_name"] == "community_col_then_sub_p10_c7_l1234"
    assert cfg["run_mode"] == "full"
    assert cfg["profile_name"] == "community_baseline_resume_v1_1"
    assert cfg["heartbeat_seconds"] == 3600
    assert cfg["autoskip_proven"] is False
    assert cfg["force_rerun_proven"] is True
    assert cfg["scorer_impl"] == "numpy"
    assert cfg["scorer_stage3_impl_avg_fulltext"] == "numpy"
