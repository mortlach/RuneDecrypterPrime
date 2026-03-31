from __future__ import annotations

from types import SimpleNamespace

import pytest
from rune_decrypter_prime.api.specs import SolverSpec

from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.no_wli import fixture_matrix_api as fixture_api
from tools.benchmarks.periodic_sub_trans.no_wli.fixture_matrix_jobs import apply_job
from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner
from tools.benchmarks.periodic_sub_trans.no_wli.run_lock_payload import (
    build_non_scoring_lock_payload,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_bridges import (
    prepare_stage3_refine_inputs_bridge,
)


pytestmark = pytest.mark.tier_a


def _build_job(*, preset_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        fixture_id="fixture_001",
        period=9,
        columns=3,
        length=1000,
        run_seed=211,
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


def _stage_key(*, period: int, alphabet_size: int, shift: int) -> list[int]:
    out: list[int] = []
    for _ in range(int(period)):
        out.extend([int((idx + int(shift)) % int(alphabet_size)) for idx in range(int(alphabet_size))])
    return out


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


def test_stage3_entry_preset_canary_keeps_solver_cfg_clean_across_runtime_surfaces() -> None:
    job = _build_job(preset_id="stage3_entry_const_local_depth_p9")
    overrides = fixture_api._resolve_stage3_tuning_overrides_for_job(job)
    assert str(overrides["force_stage3_entry_allocation_policy"]) == "constant_local_depth"
    assert int(overrides["force_stage3_entry_mutations_per_promoted"]) == 1
    assert overrides["force_solver_stage3_overrides"] is None

    no_wli = _build_live_like_no_wli(job)
    apply_job(job=job, no_wli=no_wli, **overrides)
    state = dict(no_wli.__dict__)

    assert str(state["STAGE3_ENTRY_ALLOCATION_POLICY"]) == "constant_local_depth"
    assert int(state["STAGE3_ENTRY_MUTATIONS_PER_PROMOTED"]) == 1
    assert "entry_allocation_policy" not in dict(state["SOLVER_STAGE3"])
    assert "entry_mutations_per_promoted" not in dict(state["SOLVER_STAGE3"])

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
    assert run_config["stage3"]["entry"] == {
        "allocation_policy": "constant_local_depth",
        "mutations_per_promoted": 1,
    }
    assert "entry_allocation_policy" not in dict(run_config["stage3"]["solver"])
    assert "entry_mutations_per_promoted" not in dict(run_config["stage3"]["solver"])

    non_scoring_lock = build_non_scoring_lock_payload(
        state=state,
        build_run_mode_info_fn=no_wli_runner._build_run_mode_info,
    )
    assert non_scoring_lock["stage3_search"]["entry"] == {
        "allocation_policy": "constant_local_depth",
        "mutations_per_promoted": 1,
    }
    assert "entry_allocation_policy" not in dict(non_scoring_lock["stage3_search"]["solver"])
    assert "entry_mutations_per_promoted" not in dict(
        non_scoring_lock["stage3_search"]["solver"]
    )

    tier = state["TIERS"][0]
    alphabet_size = int(state["ALPHABET_SIZE"])
    best_key = _stage_key(period=int(tier.period), alphabet_size=alphabet_size, shift=0)
    promoted_key = _stage_key(period=int(tier.period), alphabet_size=alphabet_size, shift=1)
    prep = prepare_stage3_refine_inputs_bridge(
        state=state,
        tier=tier,
        key_len=len(best_key),
        key_seed=int(job.run_seed),
        best2_key=best_key,
        best2_match=0.209,
        stage2_promoted=[
            {"key": promoted_key, "match": 0.212},
        ],
        stage2_entry_score=-4.902364,
        stage2_entry_score_judge=-4.902364,
        scorer_stage2=dict(state["SCORER_STAGE2"]),
        scorer_full=dict(state["SCORER_FULL"]),
        oracle_s3=float("nan"),
        oracle_decision_paths_enabled=False,
    )
    assert str(prep["stage3_entry_allocation_policy"]) == "constant_local_depth"
    assert int(prep["stage3_entry_mutations_per_promoted_cfg"]) == 1
    assert int(prep["stage3_entry_target_before_cap"]) >= int(
        prep["stage3_entry_base_budget"]
    )
    assert "entry_allocation_policy" not in dict(prep["solver_stage3_cfg"])
    assert "entry_mutations_per_promoted" not in dict(prep["solver_stage3_cfg"])
    solver = SolverSpec.kaeding(**dict(prep["solver_stage3_cfg"]))
    assert str(solver.name) == "kaeding"
