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
    }


def test_no_wli_iteration_bridge_parity_smoke() -> None:
    pre_out = {
        "continue_iteration": False,
        "key_len": 4,
        "full_cipher": object(),
        "ct_idx": [1, 2, 3],
        "scorer_stage2": {"objective": "avg.logp.win20"},
        "scorer_full": {"objective": "avg.logp.win20"},
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
        "stage1_best_score": -1.0,
        "ev1": 12,
        "best2_match": 0.2,
        "best2_score": -2.0,
        "best2_key": [1, 2, 3, 4],
        "best2_pt": [1, 2, 3],
        "best2_preview": "abc",
        "stage2_evals_total": 20,
        "stage2_archive": {},
        "stage2_continue_to_gate": False,
        "stage2_continue_stop_reason": "",
        "stage2_ranked": [],
        "stage2_promoted": [],
        "stage2_entry_score": -2.0,
        "stage2_entry_score_judge": -2.0,
        "stage2_score_match_spearman": 0.0,
        "stage2_topk_payload": [],
        "stage2_topk_has_best_match": False,
    }
    legacy_stage3 = {"best3_match": 0.6, "status": "ok"}

    def _run_pre(**_kwargs):
        return dict(pre_out)

    def _run_stage3(**_kwargs):
        return dict(legacy_stage3)

    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=_run_pre,
        run_stage3_iteration_flow_fn=_run_stage3,
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
    assert out.pre_stage3 == pre_out
    assert out.stage3_flow == legacy_stage3
