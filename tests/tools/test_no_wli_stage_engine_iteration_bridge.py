from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.stage_engine_iteration_bridge import (
    run_iteration_with_stage_engine,
)


pytestmark = pytest.mark.tier_a


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        stage1_label="A_char1",
        stage2_label="M_char12",
        stage3_label="B_char34",
        stage3_continue_after_solve=False,
        stage3_phaseb_top_n=8,
        stage3_phaseb_gate_delta_floor=0.01,
        stage3_phaseb_gate_end_gain_floor=0.01,
        stage3_c1_focus_enabled=False,
        stage3_span_char_pct_min_override=None,
        scoring_experiment_c_char_pct_min=0.35,
        oracle_stage3_floor_guard_eps=1e-4,
        stage3_two_phase_enabled=False,
        stage3_phasea_cfg_default={},
        stage3_phaseb_cfg_default={},
        solver_stage3_default_cfg={},
        stage3_span_basin_judge_k=8,
        tier_heartbeat_seconds=30.0,
        solve_match_threshold=0.95,
        stall_delta=1e-6,
        stall_stage_limit=2,
        stage3_span_aux_role="off",
        stage3_span_aux_scope="basin_rep",
        stage3_span_aux_profile="lite",
        stage3_span_aux_budget_ms=0.0,
        stage3_span_aux_two_pass=False,
        stage3_span_aux_full_top_m=0,
        span_decision_role_enabled=False,
        span_reps_per_basin=1,
        span_selection_top_k=0,
        span_p90_call_ms=None,
    )


def _base_state() -> dict[str, object]:
    return {
        "tier": SimpleNamespace(name="t"),
        "text_id": 0,
        "key_seed": 211,
        "off": 0,
        "offset_used": 0,
        "pt_idx": np.asarray([1, 2, 3], dtype=np.uint8),
        "wli": [],
        "direction": SimpleNamespace(value="ltr"),
        "span_assets_dir": None,
        "scoring_experiment_meta": {"profile": "off"},
        "oracle_mode": "off",
        "oracle_consulted_in_decisions": False,
        "oracle_decision_paths_enabled": False,
        "oracle_assist_selection_effective": False,
        "stages": [],
        "instances": [],
        "t0_i": 0.0,
        "STAGE3_PHASEC_START_POLICY": "source_order",
    }


def test_iteration_bridge_skips_stage3_when_pre_requests_continue() -> None:
    called = {"stage3": 0}

    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=lambda **_: {"continue_iteration": True},
        run_stage3_iteration_flow_fn=lambda **_: (called.__setitem__("stage3", called["stage3"] + 1) or {}),
        build_iteration_runtime_fn=lambda **_: {},
        evaluate_oracle_precheck_fn=lambda **_: {},
        handle_oracle_floor_guard_if_triggered_fn=lambda **_: False,
        run_stage12_pipeline_fn=lambda **_: {},
        scorer_objective_summary_fn=lambda *_: "",
        oracle_score_for_stage_fn=lambda **_: 0.0,
        weights_text_fn=lambda *_: "",
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **_: None,
        build_oracle_floor_guard_result_fn=lambda **_: {},
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        derive_outcome_code_fn=lambda **_: "ok",
        commit_iteration_with_checkpoint_fn=lambda **_: None,
        run_stage1_substitution_fn=lambda **_: {},
        run_stage2_search_fn=lambda **_: {},
        finalize_stage2_archive_fn=lambda **_: {},
        evaluate_stage3_entry_policy_fn=lambda **_: {},
        prepare_stage3_refine_inputs_fn=lambda **_: {},
        summarize_stage3_span_fn=lambda **_: {},
        fmt_finite_float_fn=lambda *_: "",
    )
    out = run_iteration_with_stage_engine(
        state=_base_state(),
        config=_config(),
        fns=fns,
        stage3_runtime_call_ctx=SimpleNamespace(),
    )
    assert out.pre_stage3["continue_iteration"] is True
    assert out.stage3_flow == {}
    assert called["stage3"] == 0
    assert len(out.events) == 4


def test_iteration_bridge_runs_stage3_with_pre_outputs() -> None:
    called = {"stage3": 0}

    pre = {
        "continue_iteration": False,
        "key_len": 10,
        "full_cipher": object(),
        "ct_idx": np.asarray([1, 2, 3], dtype=np.uint8),
        "scorer_stage2": {},
        "scorer_full": {},
        "scorer_stage3_phaseA": {},
        "scorer_stage3_phaseB": {},
        "scorer_stage3_search_runtime": object(),
        "scorer_basin_judge_runtime": object(),
        "scorer_full_runtime": object(),
        "scorer_stage3_phaseA_runtime": object(),
        "oracle_s1": 0.1,
        "oracle_s2": 0.2,
        "oracle_s3": 0.3,
        "stage3_phaseA_experiment": "off",
        "stage3_phaseB_experiment": "off",
        "stage3_phaseB_char_pct_min_dynamic": 0.35,
        "stage3_phaseB_char_pct_min_source": "static",
        "sub_key_match": 0.0,
        "stage1_best_score": 0.0,
        "ev1": 1,
        "best2_match": 0.1,
        "best2_score": 0.2,
        "best2_key": [1, 2],
        "best2_pt": [1, 2, 3],
        "best2_preview": "x",
        "stage2_evals_total": 5,
        "stage2_archive": {},
        "stage2_continue_to_gate": False,
        "stage2_continue_stop_reason": "",
        "stage2_ranked": [],
        "stage2_promoted": [],
        "stage2_entry_score": 0.2,
        "stage2_entry_score_judge": 0.2,
        "stage2_score_match_spearman": 0.0,
        "stage2_topk_payload": [],
        "stage2_topk_has_best_match": False,
    }

    def _stage3(**kwargs):
        called["stage3"] += 1
        state = kwargs["state"]
        assert "best2_key" in state
        return {
            "best3_match": 0.5,
            "stage3_topk_payload": [
                {"end_hash": "h3", "score": 0.9},
                {"end_hash": "h2", "score": 0.8},
            ],
        }

    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=lambda **_: dict(pre),
        run_stage3_iteration_flow_fn=_stage3,
        build_iteration_runtime_fn=lambda **_: {},
        evaluate_oracle_precheck_fn=lambda **_: {},
        handle_oracle_floor_guard_if_triggered_fn=lambda **_: False,
        run_stage12_pipeline_fn=lambda **_: {},
        scorer_objective_summary_fn=lambda *_: "",
        oracle_score_for_stage_fn=lambda **_: 0.0,
        weights_text_fn=lambda *_: "",
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **_: None,
        build_oracle_floor_guard_result_fn=lambda **_: {},
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        derive_outcome_code_fn=lambda **_: "ok",
        commit_iteration_with_checkpoint_fn=lambda **_: None,
        run_stage1_substitution_fn=lambda **_: {},
        run_stage2_search_fn=lambda **_: {},
        finalize_stage2_archive_fn=lambda **_: {},
        evaluate_stage3_entry_policy_fn=lambda **_: {},
        prepare_stage3_refine_inputs_fn=lambda **_: {},
        summarize_stage3_span_fn=lambda **_: {},
        fmt_finite_float_fn=lambda *_: "",
    )
    out = run_iteration_with_stage_engine(
        state=_base_state(),
        config=_config(),
        fns=fns,
        stage3_runtime_call_ctx=SimpleNamespace(),
    )
    assert called["stage3"] == 1
    assert out.stage3_flow["best3_match"] == 0.5


def test_iteration_bridge_filters_unrelated_outer_state_keys_from_stage3_state() -> None:
    pre = {
        "continue_iteration": False,
        "key_len": 10,
        "full_cipher": object(),
        "ct_idx": np.asarray([1, 2, 3], dtype=np.uint8),
        "scorer_stage2": {},
        "scorer_full": {},
        "scorer_stage3_phaseA": {},
        "scorer_stage3_phaseB": {},
        "scorer_stage3_search_runtime": object(),
        "scorer_basin_judge_runtime": object(),
        "scorer_full_runtime": object(),
        "scorer_stage3_phaseA_runtime": object(),
        "oracle_s1": 0.1,
        "oracle_s2": 0.2,
        "oracle_s3": 0.3,
        "stage3_phaseA_experiment": "off",
        "stage3_phaseB_experiment": "off",
        "stage3_phaseB_char_pct_min_dynamic": 0.35,
        "stage3_phaseB_char_pct_min_source": "static",
        "sub_key_match": 0.0,
        "stage1_best_score": 0.0,
        "ev1": 1,
        "best2_match": 0.1,
        "best2_score": 0.2,
        "best2_key": [1, 2],
        "best2_pt": [1, 2, 3],
        "best2_preview": "x",
        "stage2_evals_total": 5,
        "stage2_archive": {},
        "stage2_continue_to_gate": False,
        "stage2_continue_stop_reason": "",
        "stage2_ranked": [],
        "stage2_promoted": [],
        "stage2_entry_score": 0.2,
        "stage2_entry_score_judge": 0.2,
        "stage2_score_match_spearman": 0.0,
        "stage2_topk_payload": [],
        "stage2_topk_has_best_match": False,
    }
    observed: dict[str, object] = {}

    def _stage3(**kwargs):
        st = kwargs["state"]
        observed["keys"] = set(st.keys())
        observed["stage35_enabled"] = bool(st["STAGE35_ENABLED"])
        observed["stage35_cfg"] = dict(st["STAGE35_CFG"])
        observed["phasec_start_policy"] = str(st["STAGE3_PHASEC_START_POLICY"])
        return {"best3_match": 0.1}

    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=lambda **_: dict(pre),
        run_stage3_iteration_flow_fn=_stage3,
        build_iteration_runtime_fn=lambda **_: {},
        evaluate_oracle_precheck_fn=lambda **_: {},
        handle_oracle_floor_guard_if_triggered_fn=lambda **_: False,
        run_stage12_pipeline_fn=lambda **_: {},
        scorer_objective_summary_fn=lambda *_: "",
        oracle_score_for_stage_fn=lambda **_: 0.0,
        weights_text_fn=lambda *_: "",
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **_: None,
        build_oracle_floor_guard_result_fn=lambda **_: {},
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        derive_outcome_code_fn=lambda **_: "ok",
        commit_iteration_with_checkpoint_fn=lambda **_: None,
        run_stage1_substitution_fn=lambda **_: {},
        run_stage2_search_fn=lambda **_: {},
        finalize_stage2_archive_fn=lambda **_: {},
        evaluate_stage3_entry_policy_fn=lambda **_: {},
        prepare_stage3_refine_inputs_fn=lambda **_: {},
        summarize_stage3_span_fn=lambda **_: {},
        fmt_finite_float_fn=lambda *_: "",
    )
    _ = run_iteration_with_stage_engine(
        state={
            **_base_state(),
            "STAGE3_PHASEC_START_POLICY": "novel_challenger_v1",
            "write_json": object(),
            "base": object(),
        },
        config=SimpleNamespace(**{**_config().__dict__, "stage35_enabled": False, "stage35_cfg": {}}),
        fns=fns,
        stage3_runtime_call_ctx=SimpleNamespace(),
    )

    assert "write_json" not in observed["keys"]
    assert "base" not in observed["keys"]
    assert observed["stage35_enabled"] is False
    assert observed["stage35_cfg"] == {}
    assert observed["phasec_start_policy"] == "novel_challenger_v1"


def test_iteration_bridge_emits_shadow_counterfactual_payload_from_no_wli_topk() -> None:
    pre = {
        "continue_iteration": False,
        "key_len": 10,
        "full_cipher": object(),
        "ct_idx": np.asarray([1, 2, 3], dtype=np.uint8),
        "scorer_stage2": {},
        "scorer_full": {},
        "scorer_stage3_phaseA": {},
        "scorer_stage3_phaseB": {},
        "scorer_stage3_search_runtime": object(),
        "scorer_basin_judge_runtime": object(),
        "scorer_full_runtime": object(),
        "scorer_stage3_phaseA_runtime": object(),
        "oracle_s1": 0.1,
        "oracle_s2": 0.2,
        "oracle_s3": 0.3,
        "stage3_phaseA_experiment": "off",
        "stage3_phaseB_experiment": "off",
        "stage3_phaseB_char_pct_min_dynamic": 0.35,
        "stage3_phaseB_char_pct_min_source": "static",
        "sub_key_match": 0.0,
        "stage1_best_score": 0.0,
        "ev1": 1,
        "best2_match": 0.1,
        "best2_score": 0.2,
        "best2_key": [1, 2],
        "best2_pt": [1, 2, 3],
        "best2_preview": "x",
        "stage2_evals_total": 5,
        "stage2_archive": {},
        "stage2_continue_to_gate": False,
        "stage2_continue_stop_reason": "",
        "stage2_ranked": [],
        "stage2_promoted": [],
        "stage2_entry_score": 0.2,
        "stage2_entry_score_judge": 0.2,
        "stage2_score_match_spearman": 0.0,
        "stage2_topk_payload": [
            {"end_hash": "h1", "score": 0.7},
            {"end_hash": "h2", "score": 0.6},
            {"end_hash": "h3", "score": 0.5},
        ],
        "stage2_topk_has_best_match": True,
    }
    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=lambda **_: dict(pre),
        run_stage3_iteration_flow_fn=lambda **_: {
            "best3_match": 0.5,
            "stage3_topk_payload": [
                {"end_hash": "h3", "score": 0.9},
                {"end_hash": "h1", "score": 0.8},
            ],
        },
        build_iteration_runtime_fn=lambda **_: {},
        evaluate_oracle_precheck_fn=lambda **_: {},
        handle_oracle_floor_guard_if_triggered_fn=lambda **_: False,
        run_stage12_pipeline_fn=lambda **_: {},
        scorer_objective_summary_fn=lambda *_: "",
        oracle_score_for_stage_fn=lambda **_: 0.0,
        weights_text_fn=lambda *_: "",
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **_: None,
        build_oracle_floor_guard_result_fn=lambda **_: {},
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        derive_outcome_code_fn=lambda **_: "ok",
        commit_iteration_with_checkpoint_fn=lambda **_: None,
        run_stage1_substitution_fn=lambda **_: {},
        run_stage2_search_fn=lambda **_: {},
        finalize_stage2_archive_fn=lambda **_: {},
        evaluate_stage3_entry_policy_fn=lambda **_: {},
        prepare_stage3_refine_inputs_fn=lambda **_: {},
        summarize_stage3_span_fn=lambda **_: {},
        fmt_finite_float_fn=lambda *_: "",
    )
    out = run_iteration_with_stage_engine(
        state=_base_state(),
        config=SimpleNamespace(
            **{
                **_config().__dict__,
                "stage3_span_aux_role": "shadow",
                "stage3_span_aux_budget_ms": 1.0,
            }
        ),
        fns=fns,
        stage3_runtime_call_ctx=SimpleNamespace(),
    )
    evt = next(
        e
        for e in out.events
        if str(e.get("event")) == "span_shadow_counterfactual"
        and str(e.get("stage_id")) == "stage_c_refine"
    )
    assert evt["shadow_span_winner_id"] == "h1"
    assert evt["shadow_span_rank_of_actual_winner"] == 3


def test_iteration_bridge_stage3_span_aux_emits_engine_events() -> None:
    cfg = _config()
    cfg.stage3_span_aux_role = "shadow"
    cfg.stage3_span_aux_budget_ms = 5.0
    cfg.stage3_span_aux_scope = "basin_rep"
    cfg.stage3_span_aux_two_pass = True
    cfg.stage3_span_aux_full_top_m = 6
    cfg.span_reps_per_basin = 1
    cfg.span_p90_call_ms = 2.0
    cfg.span_selection_top_k = 2

    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=lambda **_: {"continue_iteration": True},
        run_stage3_iteration_flow_fn=lambda **_: {},
        build_iteration_runtime_fn=lambda **_: {},
        evaluate_oracle_precheck_fn=lambda **_: {},
        handle_oracle_floor_guard_if_triggered_fn=lambda **_: False,
        run_stage12_pipeline_fn=lambda **_: {},
        scorer_objective_summary_fn=lambda *_: "",
        oracle_score_for_stage_fn=lambda **_: 0.0,
        weights_text_fn=lambda *_: "",
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **_: None,
        build_oracle_floor_guard_result_fn=lambda **_: {},
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        derive_outcome_code_fn=lambda **_: "ok",
        commit_iteration_with_checkpoint_fn=lambda **_: None,
        run_stage1_substitution_fn=lambda **_: {},
        run_stage2_search_fn=lambda **_: {},
        finalize_stage2_archive_fn=lambda **_: {},
        evaluate_stage3_entry_policy_fn=lambda **_: {},
        prepare_stage3_refine_inputs_fn=lambda **_: {},
        summarize_stage3_span_fn=lambda **_: {},
        fmt_finite_float_fn=lambda *_: "",
    )
    out = run_iteration_with_stage_engine(
        state=_base_state(),
        config=cfg,
        fns=fns,
        stage3_runtime_call_ctx=SimpleNamespace(),
    )
    event_names = [str(e.get("event", "")) for e in out.events]
    assert "span_budget_plan" in event_names
    assert "span_eval_selection_plan" in event_names
    assert "span_two_pass_plan" in event_names
    plan_evt = next(e for e in out.events if str(e.get("event")) == "span_eval_selection_plan")
    assert int(plan_evt.get("ambiguity_expand_top_k", 0)) == 2


def test_iteration_bridge_validates_required_function_contract() -> None:
    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=lambda **_: {"continue_iteration": True},
    )
    with pytest.raises(TypeError, match="run_stage3_iteration_flow_fn"):
        run_iteration_with_stage_engine(
            state=_base_state(),
            config=_config(),
            fns=fns,
            stage3_runtime_call_ctx=SimpleNamespace(),
        )


def test_iteration_bridge_two_pass_aux_controls_stage3_two_phase_and_topn() -> None:
    cfg = _config()
    cfg.stage3_two_phase_enabled = False
    cfg.stage3_span_aux_role = "shadow"
    cfg.stage3_span_aux_budget_ms = 1.0
    cfg.stage3_span_aux_two_pass = True
    cfg.stage3_span_aux_full_top_m = 11

    pre = {
        "continue_iteration": False,
        "key_len": 10,
        "full_cipher": object(),
        "ct_idx": np.asarray([1, 2, 3], dtype=np.uint8),
        "scorer_stage2": {},
        "scorer_full": {},
        "scorer_stage3_phaseA": {},
        "scorer_stage3_phaseB": {},
        "scorer_stage3_search_runtime": object(),
        "scorer_basin_judge_runtime": object(),
        "scorer_full_runtime": object(),
        "scorer_stage3_phaseA_runtime": object(),
        "oracle_s1": 0.1,
        "oracle_s2": 0.2,
        "oracle_s3": 0.3,
        "stage3_phaseA_experiment": "off",
        "stage3_phaseB_experiment": "off",
        "stage3_phaseB_char_pct_min_dynamic": 0.35,
        "stage3_phaseB_char_pct_min_source": "static",
        "sub_key_match": 0.0,
        "stage1_best_score": 0.0,
        "ev1": 1,
        "best2_match": 0.1,
        "best2_score": 0.2,
        "best2_key": [1, 2],
        "best2_pt": [1, 2, 3],
        "best2_preview": "x",
        "stage2_evals_total": 5,
        "stage2_archive": {},
        "stage2_continue_to_gate": False,
        "stage2_continue_stop_reason": "",
        "stage2_ranked": [],
        "stage2_promoted": [],
        "stage2_entry_score": 0.2,
        "stage2_entry_score_judge": 0.2,
        "stage2_score_match_spearman": 0.0,
        "stage2_topk_payload": [],
        "stage2_topk_has_best_match": False,
    }
    observed: dict[str, object] = {}

    def _stage3(**kwargs):
        observed["stage3_two_phase_enabled"] = bool(kwargs.get("stage3_two_phase_enabled"))
        observed["stage3_phaseb_top_n_default"] = int(kwargs.get("stage3_phaseb_top_n_default"))
        return {"best3_match": 0.1}

    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=lambda **_: dict(pre),
        run_stage3_iteration_flow_fn=_stage3,
        build_iteration_runtime_fn=lambda **_: {},
        evaluate_oracle_precheck_fn=lambda **_: {},
        handle_oracle_floor_guard_if_triggered_fn=lambda **_: False,
        run_stage12_pipeline_fn=lambda **_: {},
        scorer_objective_summary_fn=lambda *_: "",
        oracle_score_for_stage_fn=lambda **_: 0.0,
        weights_text_fn=lambda *_: "",
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **_: None,
        build_oracle_floor_guard_result_fn=lambda **_: {},
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        derive_outcome_code_fn=lambda **_: "ok",
        commit_iteration_with_checkpoint_fn=lambda **_: None,
        run_stage1_substitution_fn=lambda **_: {},
        run_stage2_search_fn=lambda **_: {},
        finalize_stage2_archive_fn=lambda **_: {},
        evaluate_stage3_entry_policy_fn=lambda **_: {},
        prepare_stage3_refine_inputs_fn=lambda **_: {},
        summarize_stage3_span_fn=lambda **_: {},
        fmt_finite_float_fn=lambda *_: "",
    )
    _ = run_iteration_with_stage_engine(
        state=_base_state(),
        config=cfg,
        fns=fns,
        stage3_runtime_call_ctx=SimpleNamespace(),
    )
    assert observed["stage3_two_phase_enabled"] is True
    assert observed["stage3_phaseb_top_n_default"] == 11
