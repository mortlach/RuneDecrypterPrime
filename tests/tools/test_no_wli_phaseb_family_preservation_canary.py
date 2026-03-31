from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.no_wli import (
    artifact_resume as resume_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli import fixture_matrix_api as fixture_api
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_jobs import apply_job
from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner
from tools.benchmarks.periodic_sub_trans.no_wli.run_lock_payload import (
    build_non_scoring_lock_payload,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_bridges import (
    build_stage3_runtime_call_context_bridge,
)


pytestmark = pytest.mark.tier_a


def _build_job(*, preset_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=411,
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
        heartbeat_seconds=180,
        text_offsets=(0,),
        scorer_impl="torch",
        scorer_stage3_impl_avg_fulltext="torch",
        scoring_experiment_profile="c_min_late",
        schedule_early="a_char1_avg_fulltext",
        schedule_middle="m_char12_avg_fulltext",
        schedule_late="b_char4_avg_fulltext",
        stage3_tuning_preset_id=preset_id,
        span_ab_case_id="none",
        span_decision_role_enabled=False,
        tier_name=lambda: "fixture_fixture_001_p9_c3_l1000",
        scorer_schedule=lambda: {
            "early": "a_char1_avg_fulltext",
            "middle": "m_char12_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )


def _build_live_like_no_wli(job: SimpleNamespace) -> SimpleNamespace:
    state = dict(no_wli_runner.__dict__)
    profile = get_no_wli_pipeline_profile(str(job.profile_id))
    no_wli_runner._apply_profile_defaults_from_profile_external(
        state=state,
        profile=profile,
        effective_stage3_impl_fn=no_wli_runner._effective_stage3_impl,
    )
    state["PROFILE"] = str(job.profile_id)
    state["PIPELINE_RUN_MODE"] = str(job.run_mode)
    state["TEXT_OFFSETS"] = [int(x) for x in job.text_offsets]
    state["KEY_SEEDS"] = [int(job.run_seed)]
    state["TIERS"] = [
        no_wli_runner.Tier(
            str(job.tier_name()),
            int(job.period),
            int(job.columns),
            int(job.length),
        )
    ]
    state["SCORING_EXPERIMENT_PROFILE"] = str(job.scoring_experiment_profile)
    state_ns = SimpleNamespace()
    state_ns.__dict__.update(state)
    state_ns.configure_campaign_run = lambda **kwargs: None
    return state_ns


def test_stage3_phaseb_family_preservation_canary_keeps_runtime_contract_explicit() -> None:
    job = _build_job(preset_id="stage3_phaseb_family_preserve_p9")
    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert (
        str(overrides["force_stage3_phaseb_family_preservation_policy"])
        == "reserve_by_family_v1"
    )
    assert str(overrides["force_stage3_phaseb_family_view_id"]) == "prefix_hamming_le_24"
    assert int(overrides["force_stage3_phaseb_family_reserved_slots"]) == 2

    no_wli = _build_live_like_no_wli(job)
    apply_job(job=job, no_wli=no_wli, **overrides)
    state = dict(no_wli.__dict__)

    assert (
        str(state["STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY"])
        == "reserve_by_family_v1"
    )
    assert str(state["STAGE3_PHASEB_FAMILY_VIEW_ID"]) == "prefix_hamming_le_24"
    assert int(state["STAGE3_PHASEB_FAMILY_RESERVED_SLOTS"]) == 2

    mode_info = no_wli_runner._build_run_mode_info(str(job.run_mode))
    run_config = no_wli_runner._build_run_config_external(
        state=state,
        mode_canonical=str(mode_info.mode_canonical),
        mode_raw=str(mode_info.mode_raw),
        mode_intent=str(mode_info.intent),
        stage3_can_skip=bool(mode_info.stage3_can_skip),
        scoring_experiment_meta={"profile": "c_min_late", "enabled": True},
        root=no_wli_runner._repo_root(),
        direction=no_wli_runner.Direction.LTR,
        autoskip_effective=False,
        proven_known=0,
        oracle_mode="off",
        oracle_decision_paths_enabled=False,
        oracle_assist_selection_effective=False,
        is_adaptive_focus_mode_fn=no_wli_runner._is_adaptive_focus_mode,
        scorer_cfg_for_output_fn=no_wli_runner._scorer_cfg_for_output,
        stage3_search_cfg_fn=no_wli_runner._stage3_char4_avg_fulltext_search_cfg,
        scoring_meta_for_output_fn=no_wli_runner._scoring_meta_for_output,
        build_no_wli_order_dispatch_payload_fn=no_wli_runner._build_no_wli_order_dispatch_payload,
    )
    assert run_config["stage3"]["two_phase"]["family_preservation"] == {
        "policy": "reserve_by_family_v1",
        "family_view_id": "prefix_hamming_le_24",
        "reserved_slots": 2,
    }

    non_scoring_lock = build_non_scoring_lock_payload(
        state=state,
        build_run_mode_info_fn=no_wli_runner._build_run_mode_info,
    )
    assert non_scoring_lock["stage3_search"]["phase_b_family_preservation"] == {
        "policy": "reserve_by_family_v1",
        "family_view_id": "prefix_hamming_le_24",
        "reserved_slots": 2,
    }

    ctx = build_stage3_runtime_call_context_bridge(
        state=state,
        run_dir=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/dummy"),
    )
    assert str(ctx.stage3_phaseb_family_preservation_policy) == "reserve_by_family_v1"
    assert str(ctx.stage3_phaseb_family_view_id) == "prefix_hamming_le_24"
    assert int(ctx.stage3_phaseb_family_reserved_slots) == 2

    resume_ctx = resume_mod._build_stage3_runtime_call_context(
        artifact={"order": "col_then_sub", "alphabet_size": int(state["ALPHABET_SIZE"])},
        run_config=run_config,
        output_dir=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/dummy"),
    )
    assert (
        str(resume_ctx.stage3_phaseb_family_preservation_policy)
        == "reserve_by_family_v1"
    )
    assert str(resume_ctx.stage3_phaseb_family_view_id) == "prefix_hamming_le_24"
    assert int(resume_ctx.stage3_phaseb_family_reserved_slots) == 2
