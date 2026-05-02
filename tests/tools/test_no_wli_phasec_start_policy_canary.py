from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
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


def _assert_phasec_start_policy_contract(
    *,
    preset_id: str,
    expected_start_policy: str,
    expected_phaseb_top_n: int,
) -> None:
    job = _build_job(preset_id=preset_id)
    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert str(overrides["force_stage3_phasec_start_policy"]) == str(
        expected_start_policy
    )
    assert int(overrides["force_stage3_phaseb_top_n"]) == int(expected_phaseb_top_n)

    no_wli = _build_live_like_no_wli(job)
    apply_job(job=job, no_wli=no_wli, **overrides)
    state = dict(no_wli.__dict__)

    assert str(state["STAGE3_PHASEC_START_POLICY"]) == str(expected_start_policy)
    assert int(state["STAGE3_PHASEB_TOP_N"]) == int(expected_phaseb_top_n)

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
    assert str(
        run_config["stage3"]["two_phase"]["phase_c"]["start_policy"]
    ) == str(expected_start_policy)
    assert int(run_config["stage3"]["two_phase"]["phase_b_top_n"]) == int(
        expected_phaseb_top_n
    )

    non_scoring_lock = build_non_scoring_lock_payload(
        state=state,
        build_run_mode_info_fn=no_wli_runner._build_run_mode_info,
    )
    assert str(
        non_scoring_lock["stage3_search"]["phase_c"]["start_policy"]
    ) == str(expected_start_policy)
    assert int(non_scoring_lock["stage3_search"]["phase_b_top_n"]) == int(
        expected_phaseb_top_n
    )

    ctx = build_stage3_runtime_call_context_bridge(
        state=state,
        run_dir=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/dummy"),
    )
    assert str(ctx.stage3_phasec_start_policy) == str(expected_start_policy)


def test_stage3_phasec_start_policy_canary_keeps_balanced_runtime_contract_explicit() -> None:
    _assert_phasec_start_policy_contract(
        preset_id="stage3_phasec_start_balanced_p9",
        expected_start_policy="balanced_sources_v1",
        expected_phaseb_top_n=8,
    )


def test_stage3_phasec_start_policy_canary_keeps_novel_runtime_contract_explicit() -> None:
    _assert_phasec_start_policy_contract(
        preset_id="stage3_phasec_novel_challenger_p9",
        expected_start_policy="novel_challenger_v1",
        expected_phaseb_top_n=32,
    )


def test_stage3_phasec_start_policy_canary_keeps_anchor_family_runtime_contract_explicit() -> None:
    _assert_phasec_start_policy_contract(
        preset_id="stage3_phasec_anchor_family_reserved_p9",
        expected_start_policy="anchor_family_reserved_v1",
        expected_phaseb_top_n=32,
    )


def test_stage3_phasec_start_policy_canary_keeps_phaseb_topk_anchor_swap_runtime_contract_explicit() -> None:
    _assert_phasec_start_policy_contract(
        preset_id="stage3_phasec_phaseb_topk_anchor_swap_p9",
        expected_start_policy="phaseb_topk_anchor_swap_v1",
        expected_phaseb_top_n=32,
    )
