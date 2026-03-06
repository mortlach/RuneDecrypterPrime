from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from tools.benchmarks.community import _run_single_job as rsj
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    DEFAULT_SCORER_SCHEDULE,
    SCHEDULE_EARLY_A_CHAR34,
    SCHEDULE_EARLY_CHAR34_ONLY,
    SCHEDULE_LATE_B_CHAR34,
    SCHEDULE_LATE_CHAR34_ONLY,
    SCHEDULE_MIDDLE_M_CHAR34,
    SCHEDULE_MIDDLE_CHAR34_ONLY,
)

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
    assert module._cfg["scorer_schedule"] == DEFAULT_SCORER_SCHEDULE.as_dict()


def test_run_single_job_helper_adds_src_import_path():
    repo_root = Path(rsj.__file__).resolve().parents[3]
    src_root = repo_root / "src"
    assert str(src_root) in sys.path


def test_run_single_job_result_paths_are_repo_relative():
    repo_root = Path(rsj.__file__).resolve().parents[3]
    run_dir = repo_root / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "col_then_sub" / "run_x"
    row = rsj._build_result_row(
        job={
            "campaign_id": "cid",
            "job_id": "jid",
            "git_sha": "sha",
            "text_fixture_id": "fixture_001",
            "period": 7,
            "columns": 3,
            "order": "col_then_sub",
            "profile_id": "baseline_resume_v1_1",
            "run_seed": 111,
            "replicate_idx": 0,
            "config_fingerprint": "fp",
        },
        inst={
            "status": "unsolved",
            "stop_reason": "completed_pipeline",
            "best_match_ratio": 0.5,
            "best_stage": "stage2",
            "total_seconds": 1.0,
            "total_evals": 10,
        },
        stages=[],
        fastlm_present=True,
        run_dir=run_dir,
        repo_root=repo_root,
    )
    assert str(row["output_run_dir"]).startswith("output/")
    assert Path(str(row["output_run_dir"])).is_absolute() is False


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
    assert cfg["scorer_schedule"] == DEFAULT_SCORER_SCHEDULE.as_dict()


def test_configure_module_for_campaign_forwards_profile_scorer_schedule():
    calls: list[dict[str, object]] = []

    class _Module:
        def configure_campaign_run(self, **kwargs: object) -> None:
            calls.append(dict(kwargs))

    module = _Module()
    job = {
        "order": "col_then_sub",
        "run_seed": 333,
        "period": 10,
        "columns": 7,
        "text_fixture_id": "fixture_001",
        "profile_id": "schedule_char34_only_v1_1",
    }
    campaign_config = {"fixtures": [{"text_fixture_id": "fixture_001", "length": 1234}]}
    profile_catalog = {
        "profiles": [
            {
                "profile_id": "schedule_char34_only_v1_1",
                "scorer_schedule": {
                    "early": SCHEDULE_EARLY_CHAR34_ONLY,
                    "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
                    "late": SCHEDULE_LATE_CHAR34_ONLY,
                },
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
    assert calls[0]["scorer_schedule"] == {
        "early": SCHEDULE_EARLY_CHAR34_ONLY,
        "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
        "late": SCHEDULE_LATE_CHAR34_ONLY,
    }


def test_configure_module_for_campaign_forwards_no_wli_style_schedule_ids():
    calls: list[dict[str, object]] = []

    class _Module:
        def configure_campaign_run(self, **kwargs: object) -> None:
            calls.append(dict(kwargs))

    module = _Module()
    job = {
        "order": "col_then_sub",
        "run_seed": 333,
        "period": 10,
        "columns": 7,
        "text_fixture_id": "fixture_001",
        "profile_id": "schedule_nowli_style_v1_1",
    }
    campaign_config = {"fixtures": [{"text_fixture_id": "fixture_001", "length": 1234}]}
    profile_catalog = {
        "profiles": [
            {
                "profile_id": "schedule_nowli_style_v1_1",
                "scorer_schedule": {
                    "early": SCHEDULE_EARLY_A_CHAR34,
                    "middle": SCHEDULE_MIDDLE_M_CHAR34,
                    "late": SCHEDULE_LATE_B_CHAR34,
                },
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
    assert calls[0]["scorer_schedule"] == {
        "early": SCHEDULE_EARLY_A_CHAR34,
        "middle": SCHEDULE_MIDDLE_M_CHAR34,
        "late": SCHEDULE_LATE_B_CHAR34,
    }


def test_community_adapter_dispatch_schedule_changes_col_then_sub_effective_path():
    from tools.benchmarks.periodic_sub_trans.col_then_sub import runner as col_runner

    old_state = dict(
        autoskip=bool(col_runner.AUTOSKIP_PROVEN),
        force_rerun=bool(col_runner.FORCE_RERUN_PROVEN),
        avoid_repeat=bool(col_runner.AVOID_REPEAT_FAIL),
        key_seeds=list(col_runner.KEY_SEEDS),
        key_seeds_override=None
        if col_runner.KEY_SEEDS_OVERRIDE is None
        else list(col_runner.KEY_SEEDS_OVERRIDE),
        text_offsets=list(col_runner.TEXT_OFFSETS),
        run_mode=str(col_runner.PIPELINE_RUN_MODE),
        profile=str(col_runner.PROFILE),
        heartbeat=int(col_runner.HEARTBEAT_SECONDS),
        tiers=list(col_runner.TIERS),
        tiers_regex=col_runner.TIERS_REGEX_OVERRIDE,
        tiers_period_sweep=str(col_runner.TIERS_PERIOD_SWEEP),
        tiers_min_columns=col_runner.TIERS_MIN_COLUMNS,
        scorer_stage1=copy.deepcopy(col_runner.SCORER_STAGE1),
        scorer_stage1_hard=copy.deepcopy(col_runner.SCORER_STAGE1_HARD_RERANK),
        scorer_full=copy.deepcopy(col_runner.SCORER_FULL),
        scorer_impl=str(col_runner.SCORER_IMPL),
    )

    try:
        job = {
            "order": "col_then_sub",
            "run_seed": 222,
            "period": 10,
            "columns": 7,
            "text_fixture_id": "fixture_001",
            "profile_id": "schedule_char34_only_v1_1",
        }
        campaign_config = {"fixtures": [{"text_fixture_id": "fixture_001", "length": 1234}]}
        profile_catalog = {
            "profiles": [
                {
                    "profile_id": "schedule_char34_only_v1_1",
                    "scorer_schedule": {
                        "early": SCHEDULE_EARLY_CHAR34_ONLY,
                        "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
                        "late": SCHEDULE_LATE_CHAR34_ONLY,
                    },
                    "overrides": {},
                }
            ]
        }

        rsj._configure_module_for_campaign_job(
            module=col_runner,  # type: ignore[arg-type]
            job=job,
            campaign_config=campaign_config,
            profile_catalog=profile_catalog,
            repo_root=Path.cwd(),
        )

        assert dict(col_runner.SCORER_STAGE1.get("char_weights", {})) == {3: 0.2, 4: 0.8}
        assert bool(col_runner.SCORER_STAGE1.get("use_word_breaks", True)) is False
        assert dict(col_runner.SCORER_FULL.get("char_weights", {})) == {3: 0.2, 4: 0.8}
        assert bool(col_runner.SCORER_FULL.get("use_word_breaks", True)) is False
        assert dict(col_runner.SCORER_FULL.get("wli_weights", {})) == {}
    finally:
        col_runner.AUTOSKIP_PROVEN = bool(old_state["autoskip"])
        col_runner.FORCE_RERUN_PROVEN = bool(old_state["force_rerun"])
        col_runner.AVOID_REPEAT_FAIL = bool(old_state["avoid_repeat"])
        col_runner.KEY_SEEDS = list(old_state["key_seeds"])
        col_runner.KEY_SEEDS_OVERRIDE = (
            None
            if old_state["key_seeds_override"] is None
            else list(old_state["key_seeds_override"])
        )
        col_runner.TEXT_OFFSETS = list(old_state["text_offsets"])
        col_runner.PIPELINE_RUN_MODE = str(old_state["run_mode"])
        col_runner.PROFILE = str(old_state["profile"])
        col_runner.HEARTBEAT_SECONDS = int(old_state["heartbeat"])
        col_runner.TIERS = list(old_state["tiers"])
        col_runner.TIERS_REGEX_OVERRIDE = old_state["tiers_regex"]
        col_runner.TIERS_PERIOD_SWEEP = str(old_state["tiers_period_sweep"])
        col_runner.TIERS_MIN_COLUMNS = old_state["tiers_min_columns"]
        col_runner.SCORER_STAGE1 = copy.deepcopy(old_state["scorer_stage1"])
        col_runner.SCORER_STAGE1_HARD_RERANK = copy.deepcopy(old_state["scorer_stage1_hard"])
        col_runner.SCORER_FULL = copy.deepcopy(old_state["scorer_full"])
        col_runner.SCORER_IMPL = str(old_state["scorer_impl"])


def test_community_adapter_dispatch_schedule_changes_sub_then_col_effective_path():
    from tools.benchmarks.periodic_sub_trans.sub_then_col import runner as sub_runner

    old_state = dict(
        autoskip=bool(sub_runner.AUTOSKIP_PROVEN),
        force_rerun=bool(sub_runner.FORCE_RERUN_PROVEN),
        key_seeds=list(sub_runner.KEY_SEEDS),
        key_seeds_override=None
        if sub_runner.KEY_SEEDS_OVERRIDE is None
        else list(sub_runner.KEY_SEEDS_OVERRIDE),
        text_offsets=list(sub_runner.TEXT_OFFSETS),
        run_mode=str(sub_runner.PIPELINE_RUN_MODE),
        profile=str(sub_runner.PROFILE),
        heartbeat=int(sub_runner.HEARTBEAT_SECONDS),
        tiers=list(sub_runner.TIERS),
        tiers_regex=sub_runner.TIERS_REGEX_OVERRIDE,
        scorer_sub=copy.deepcopy(sub_runner.SCORER_SUB),
        scorer_full=copy.deepcopy(sub_runner.SCORER_FULL),
        scorer_profile=str(sub_runner.STAGEAB_SCORER_PROFILE),
        scorer_profiles=copy.deepcopy(sub_runner.STAGEAB_SCORER_PROFILES),
        scorer_impl=str(sub_runner.SCORER_IMPL),
    )

    try:
        job = {
            "order": "sub_then_col",
            "run_seed": 222,
            "period": 10,
            "columns": 7,
            "text_fixture_id": "fixture_001",
            "profile_id": "schedule_char34_only_v1_1",
        }
        campaign_config = {"fixtures": [{"text_fixture_id": "fixture_001", "length": 1234}]}
        profile_catalog = {
            "profiles": [
                {
                    "profile_id": "schedule_char34_only_v1_1",
                    "scorer_schedule": {
                        "early": SCHEDULE_EARLY_CHAR34_ONLY,
                        "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
                        "late": SCHEDULE_LATE_CHAR34_ONLY,
                    },
                    "overrides": {},
                }
            ]
        }

        rsj._configure_module_for_campaign_job(
            module=sub_runner,  # type: ignore[arg-type]
            job=job,
            campaign_config=campaign_config,
            profile_catalog=profile_catalog,
            repo_root=Path.cwd(),
        )

        assert str(sub_runner.STAGEAB_SCORER_PROFILE) == sub_runner.StageABScorerProfile.A_CHAR34.value
        assert bool(sub_runner.SCORER_SUB.get("use_word_breaks", True)) is False
        assert dict(sub_runner.SCORER_SUB.get("wli_weights", {})) == {}
        assert bool(sub_runner.SCORER_FULL.get("use_word_breaks", True)) is False
        assert dict(sub_runner.SCORER_FULL.get("wli_weights", {})) == {}
    finally:
        sub_runner.AUTOSKIP_PROVEN = bool(old_state["autoskip"])
        sub_runner.FORCE_RERUN_PROVEN = bool(old_state["force_rerun"])
        sub_runner.KEY_SEEDS = list(old_state["key_seeds"])
        sub_runner.KEY_SEEDS_OVERRIDE = (
            None
            if old_state["key_seeds_override"] is None
            else list(old_state["key_seeds_override"])
        )
        sub_runner.TEXT_OFFSETS = list(old_state["text_offsets"])
        sub_runner.PIPELINE_RUN_MODE = str(old_state["run_mode"])
        sub_runner.PROFILE = str(old_state["profile"])
        sub_runner.HEARTBEAT_SECONDS = int(old_state["heartbeat"])
        sub_runner.TIERS = list(old_state["tiers"])
        sub_runner.TIERS_REGEX_OVERRIDE = old_state["tiers_regex"]
        sub_runner.SCORER_SUB = copy.deepcopy(old_state["scorer_sub"])
        sub_runner.SCORER_FULL = copy.deepcopy(old_state["scorer_full"])
        sub_runner.STAGEAB_SCORER_PROFILE = str(old_state["scorer_profile"])
        sub_runner.STAGEAB_SCORER_PROFILES = copy.deepcopy(old_state["scorer_profiles"])
        sub_runner.SCORER_IMPL = str(old_state["scorer_impl"])
