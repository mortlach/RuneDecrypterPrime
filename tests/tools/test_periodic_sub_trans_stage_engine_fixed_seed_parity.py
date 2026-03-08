from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.col_then_sub.stage_engine_contract import (
    build_col_then_sub_stage_specs,
)
from tools.benchmarks.periodic_sub_trans.col_then_sub.stage_engine_iteration_bridge import (
    ColThenSubStageEngineFns,
    run_iteration_with_stage_engine as run_col_bridge,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage_engine_iteration_bridge import (
    run_iteration_with_stage_engine as run_no_wli_bridge,
)
from tools.benchmarks.periodic_sub_trans.sub_then_col.stage_engine_contract import (
    build_sub_then_col_stage_specs,
)
from tools.benchmarks.periodic_sub_trans.sub_then_col.stage_engine_iteration_bridge import (
    SubThenColStageEngineFns,
    run_iteration_with_stage_engine as run_sub_bridge,
)


pytestmark = pytest.mark.tier_a


def test_col_then_sub_bridge_fixed_seed_parity() -> None:
    state = {"seed": 20260307, "delta": 0.25}

    def _a(s):
        rng = np.random.default_rng(int(s["seed"]))
        return {"a": [int(x) for x in rng.integers(0, 50, size=4)]}

    def _b(s, a):
        _ = s
        vals = [int(x) for x in a["a"]]
        return {"b": int(sum(vals))}

    def _c(s, a, b):
        return {"c": float(b["b"]) + float(s["delta"]) + float(a["a"][0])}

    legacy_a = _a(state)
    legacy_b = _b(state, legacy_a)
    legacy_c = _c(state, legacy_a, legacy_b)

    specs = build_col_then_sub_stage_specs(
        state=dict(
            SCORER_STAGE1={"objective": "pct.logp.win10"},
            SCORER_FULL={"objective": "pct.logp.win10"},
            STAGE12_ARCHIVE_KEEP=4,
            STAGE12_PROMOTE_TOP=2,
            STAGE3_INITIAL_KEYS=8,
        )
    )
    out = run_col_bridge(
        state=state,
        stage_specs=specs,
        fns=ColThenSubStageEngineFns(run_stage_a_fn=_a, run_stage_b_fn=_b, run_stage_c_fn=_c),
    )
    assert out.stage_a == legacy_a
    assert out.stage_b == legacy_b
    assert out.stage_c == legacy_c


def test_sub_then_col_bridge_fixed_seed_parity() -> None:
    state = {"seed": 111, "offset": 7}

    def _a(s):
        rng = np.random.default_rng(int(s["seed"]))
        return {"p": [int(x) for x in rng.integers(0, 10, size=3)]}

    def _b(s, a):
        return {"q": int(sum(int(x) for x in a["p"])) + int(s["offset"])}

    def _c(s, a, b):
        _ = s
        return {"r": int(b["q"]) + int(a["p"][0])}

    legacy_a = _a(state)
    legacy_b = _b(state, legacy_a)
    legacy_c = _c(state, legacy_a, legacy_b)

    specs = build_sub_then_col_stage_specs(
        state=dict(
            SCORER_SUB={"objective": "pct.logp.win10"},
            SCORER_FULL={"objective": "pct.logp.win10"},
            COL_KEEP=3,
            STAGE3_INITIAL_KEYS=8,
        )
    )
    out = run_sub_bridge(
        state=state,
        stage_specs=specs,
        fns=SubThenColStageEngineFns(run_stage_a_fn=_a, run_stage_b_fn=_b, run_stage_c_fn=_c),
    )
    assert out.stage_a == legacy_a
    assert out.stage_b == legacy_b
    assert out.stage_c == legacy_c


def _no_wli_cfg() -> SimpleNamespace:
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


def test_no_wli_iteration_bridge_fixed_seed_parity() -> None:
    state = {"seed": 333}

    def _pre(**kwargs):
        seed = int(kwargs["state"]["seed"])
        rng = np.random.default_rng(seed)
        key = [int(x) for x in rng.integers(0, 29, size=5)]
        score = float(rng.normal())
        return {
            "continue_iteration": False,
            "key_len": 5,
            "full_cipher": object(),
            "ct_idx": [1, 2, 3],
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
            "stage1_best_score": score,
            "ev1": 2,
            "best2_match": 0.2,
            "best2_score": score,
            "best2_key": key,
            "best2_pt": [1, 2, 3],
            "best2_preview": "x",
            "stage2_evals_total": 5,
            "stage2_archive": {},
            "stage2_continue_to_gate": False,
            "stage2_continue_stop_reason": "",
            "stage2_ranked": [],
            "stage2_promoted": [],
            "stage2_entry_score": score,
            "stage2_entry_score_judge": score,
            "stage2_score_match_spearman": 0.0,
            "stage2_topk_payload": [],
            "stage2_topk_has_best_match": False,
        }

    def _stage3(**kwargs):
        best2 = kwargs["state"]["best2_key"]
        return {"best3_match": float(sum(int(x) for x in best2) % 100) / 100.0}

    legacy_pre = _pre(state=state)
    legacy_stage3 = _stage3(state=dict(legacy_pre))

    fns = SimpleNamespace(
        run_iteration_pre_stage3_fn=_pre,
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
    out = run_no_wli_bridge(
        state=state,
        config=_no_wli_cfg(),
        fns=fns,
        stage3_runtime_call_ctx=SimpleNamespace(),
    )
    comparable_keys = [
        "continue_iteration",
        "key_len",
        "ct_idx",
        "oracle_s1",
        "oracle_s2",
        "oracle_s3",
        "stage3_phaseA_experiment",
        "stage3_phaseB_experiment",
        "stage3_phaseB_char_pct_min_dynamic",
        "stage3_phaseB_char_pct_min_source",
        "sub_key_match",
        "stage1_best_score",
        "ev1",
        "best2_match",
        "best2_score",
        "best2_key",
        "best2_pt",
        "best2_preview",
        "stage2_evals_total",
        "stage2_entry_score",
        "stage2_entry_score_judge",
    ]
    assert {k: out.pre_stage3[k] for k in comparable_keys} == {
        k: legacy_pre[k] for k in comparable_keys
    }
    assert out.stage3_flow == legacy_stage3
