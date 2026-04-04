from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.iteration_matrix_builder import (
    build_iteration_matrix_config,
)
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_matrix_flow import (
    IterationMatrixConfig,
    IterationMatrixFns,
    run_iteration_matrix,
)


pytestmark = pytest.mark.tier_a


def _config() -> IterationMatrixConfig:
    return IterationMatrixConfig(
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
        scan_stage3_gate_low_match=0.15,
        scan_stage3_gate_high_match=0.22,
        oracle_mode="off",
        oracle_decision_paths_enabled=False,
        oracle_assist_selection_effective=False,
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
        stage3_phasec_start_policy="source_order",
        stage35_enabled=False,
        stage35_baseline_selector="legacy",
        stage35_cfg={},
        require_batch_scoring=True,
    )


def test_build_iteration_matrix_config_forwards_phasec_start_policy() -> None:
    state = {
        "SCORER_STAGE1_LABEL": "A_char1",
        "SCORER_STAGE2_LABEL": "M_char12",
        "SCORER_STAGE3_LABEL": "B_char34",
        "STAGE3_CONTINUE_AFTER_SOLVE": False,
        "STAGE3_PHASEB_TOP_N": 8,
        "STAGE3_PHASEB_GATE_DELTA_FLOOR": 0.01,
        "STAGE3_PHASEB_GATE_END_GAIN_FLOOR": 0.01,
        "STAGE3_C1_FOCUS_ENABLED": False,
        "STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE": None,
        "SCORING_EXPERIMENT_C_CHAR_PCT_MIN": 0.35,
        "ORACLE_STAGE3_FLOOR_GUARD_EPS": 1e-4,
        "STAGE3_TWO_PHASE_ENABLED": False,
        "STAGE3_PHASEA_CFG": {},
        "STAGE3_PHASEB_CFG": {},
        "SOLVER_STAGE3": {},
        "STAGE3_SPAN_BASIN_JUDGE_K": 8,
        "TIER_HEARTBEAT_SECONDS": 30.0,
        "SOLVE_MATCH_THRESHOLD": 0.95,
        "STALL_DELTA": 1e-6,
        "STALL_STAGE_LIMIT": 2,
        "SCAN_STAGE3_GATE_LOW_MATCH": 0.15,
        "SCAN_STAGE3_GATE_HIGH_MATCH": 0.22,
        "STAGE3_SPAN_AUX_ROLE": "off",
        "STAGE3_SPAN_AUX_SCOPE": "basin_rep",
        "STAGE3_SPAN_AUX_PROFILE": "lite",
        "STAGE3_SPAN_AUX_BUDGET_MS": 0.0,
        "STAGE3_SPAN_AUX_TWO_PASS": False,
        "STAGE3_SPAN_AUX_FULL_TOP_M": 0,
        "SPAN_DECISION_ROLE_ENABLED": False,
        "SPAN_REPS_PER_BASIN": 1,
        "SPAN_SELECTION_TOP_K": 0,
        "SPAN_P90_CALL_MS": None,
        "STAGE3_PHASEC_START_POLICY": "novel_challenger_v1",
        "STAGE35_ENABLED": False,
        "STAGE35_BASELINE_SELECTOR": "score_plus_novelty",
        "STAGE35_CFG": {},
        "REQUIRE_BATCH_SCORING": True,
    }

    cfg = build_iteration_matrix_config(
        state=state,
        oracle_mode="off",
        oracle_decision_paths_enabled=False,
        oracle_assist_selection_effective=False,
    )

    assert cfg.stage3_phasec_start_policy == "novel_challenger_v1"
    assert cfg.stage35_baseline_selector == "score_plus_novelty"


def _build_fns(*, event_sink: list[dict[str, Any]] | None = None) -> IterationMatrixFns:
    def _slice(pt_base, wli_base, *, length, offset_hint):
        pt = np.asarray(list(pt_base)[: int(length)], dtype=np.uint8)
        return pt, list(wli_base), int(offset_hint)

    def _run_pre(**kwargs):
        state = kwargs["state"]
        seed = int(state["key_seed"])
        rng = np.random.default_rng(seed)
        key = [int(x) for x in rng.integers(0, 29, size=4)]
        score = float(rng.normal())
        return {
            "continue_iteration": False,
            "key_len": 4,
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
            "stage1_best_score": score,
            "ev1": 1,
            "best2_match": 0.1,
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

    def _run_stage3(**kwargs):
        st = kwargs["state"]
        seed = int(st["key_seed"])
        val = float(sum(int(x) for x in st["best2_key"])) + (seed % 7) * 0.001
        return {
            "best3_match": float((val % 100.0) / 100.0),
            "best3_score": float(-val),
            "best_stage": "stage3_refine",
            "status": "unsolved",
            "stop_reason": "completed_pipeline",
            "stage3_span_active_rate": 0.5,
            "stage3_span_active_rate_source": "solver_run_telemetry",
            "stage3_span_eval_total": 10.0,
            "stage3_span_eval_active": 5.0,
            "stage3_span_eval_skipped": 5.0,
            "stage3_span_seconds_total": 0.25,
            "stage3_span_seconds_active": 0.10,
            "stage3_basin_judge_span_calls_total": 4,
            "stage3_basin_judge_span_calls_active": 3,
            "stage3_basin_judge_span_calls_rejected_or_gated": 1,
            "stage3_basin_judge_span_seconds_total": 0.05,
        }

    def _finalize_post_stage3(**kwargs):
        st = kwargs["state"]
        instances = st["instances"]
        stages = st["stages"]
        instances.append(
            dict(
                tier=str(st["tier"].name),
                text_id=int(st["text_id"]),
                key_seed=int(st["key_seed"]),
                best_match_ratio=float(st["best3_match"]),
                best_objective_score=float(st["best3_score"]),
                best_stage=str(st["best_stage"]),
                stop_reason=str(st["stop_reason"]),
            )
        )
        stages.append(
            dict(
                stage="stage3_refine",
                tier=str(st["tier"].name),
                text_id=int(st["text_id"]),
                key_seed=int(st["key_seed"]),
                match_ratio=float(st["best3_match"]),
                score=float(st["best3_score"]),
            )
        )

    return IterationMatrixFns(
        slice_word_aligned_fn=_slice,
        get_oracle_consulted_in_decisions_fn=lambda: False,
        handle_autoskip_proven_iteration_fn=lambda **_: None,
        run_iteration_pre_stage3_fn=_run_pre,
        run_stage3_iteration_flow_fn=_run_stage3,
        finalize_iteration_post_stage3_fn=_finalize_post_stage3,
        build_iteration_payloads_fn=lambda **_: ({}, {}),
        derive_outcome_code_fn=lambda **_: "ok",
        commit_iteration_with_checkpoint_fn=lambda **_: None,
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
        run_stage1_substitution_fn=lambda **_: {},
        run_stage2_search_fn=lambda **_: {},
        finalize_stage2_archive_fn=lambda **_: {},
        evaluate_stage3_entry_policy_fn=lambda **_: {},
        prepare_stage3_refine_inputs_fn=lambda **_: {},
        summarize_stage3_span_fn=lambda **_: {},
        fmt_finite_float_fn=lambda *_: "",
        build_stage2_diagnostics_fn=lambda **_: {},
        build_stage3_diagnostics_fn=lambda **_: {},
        finalize_iteration_and_commit_fn=lambda **_: {},
        safe_preview_latin_fn=lambda *_: "",
        stage_engine_trace_emit_fn=(
            (lambda **kwargs: event_sink.append(dict(kwargs.get("event", {}))))
            if event_sink is not None
            else (lambda **_: None)
        ),
    )


def _run_once(
    seed: int,
    *,
    config: IterationMatrixConfig | None = None,
    event_sink: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tiers = [SimpleNamespace(name="fixture_p7_c3_l200", period=7, columns=3, length=200)]
    instances: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    run_iteration_matrix(
        tiers=tiers,
        text_offsets=[0],
        key_seeds=[int(seed)],
        pt_base=list(range(400)),
        wli_base=[(i, i + 1) for i in range(20)],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=False,
        proven_index={},
        instances=instances,
        stages=stages,
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=(config if config is not None else _config()),
        fns=_build_fns(event_sink=event_sink),
    )
    return instances, stages


def test_no_wli_iteration_matrix_fixed_seed_parity() -> None:
    a_instances, a_stages = _run_once(seed=4242)
    b_instances, b_stages = _run_once(seed=4242)
    assert a_instances == b_instances
    assert a_stages == b_stages
    assert len(a_instances) == 1
    assert len(a_stages) == 1


def test_no_wli_iteration_matrix_runner_level_span_shadow_checklist_events() -> None:
    cfg = replace(
        _config(),
        stage3_span_aux_role="shadow",
        stage3_span_aux_scope="basin_rep",
        stage3_span_aux_profile="lite",
        stage3_span_aux_budget_ms=6.0,
        stage3_span_aux_two_pass=True,
        stage3_span_aux_full_top_m=4,
        span_decision_role_enabled=False,
        span_reps_per_basin=1,
        span_selection_top_k=0,
        span_p90_call_ms=2.0,
    )
    events: list[dict[str, Any]] = []
    _run_once(seed=4242, config=cfg, event_sink=events)
    names = [str(e.get("event", "")) for e in events]
    assert "span_budget_plan" in names
    assert "span_eval_selection_plan" in names
    assert "span_two_pass_plan" in names
    stage_c_start = next(
        e
        for e in events
        if str(e.get("event")) == "stage_start" and str(e.get("stage_id")) == "stage_c_refine"
    )
    assert bool(stage_c_start.get("shadow_mode_active")) is True
    assert bool(stage_c_start.get("aux_decision_influence")) is False
    assert bool(stage_c_start.get("span_decision_role_enabled")) is False


def test_no_wli_iteration_matrix_emits_span_runtime_telemetry_event() -> None:
    events: list[dict[str, Any]] = []
    _run_once(seed=4242, event_sink=events)
    evt = next(e for e in events if str(e.get("event")) == "span_runtime_telemetry")
    assert float(evt["span_eval_total"]) == 10.0
    assert float(evt["span_eval_active"]) == 5.0
    assert int(evt["basin_judge_span_calls_total"]) == 4
    assert str(evt["span_active_rate_source"]) == "solver_run_telemetry"


def test_no_wli_iteration_matrix_forwards_stage35_cfg_into_stage3_state() -> None:
    cfg = replace(
        _config(),
        stage35_enabled=True,
        stage35_cfg={"rounds": 3, "beam_width": 4},
    )
    observed: dict[str, object] = {}

    def _run_stage3(**kwargs):
        st = kwargs["state"]
        observed["stage35_enabled"] = bool(st.get("STAGE35_ENABLED", False))
        observed["stage35_cfg"] = dict(st.get("STAGE35_CFG", {}))
        return {
            "best3_match": 0.1,
            "best3_score": -1.0,
            "best_stage": "stage3_refine",
            "status": "unsolved",
            "stop_reason": "completed_pipeline",
            "stage3_span_active_rate": 0.5,
            "stage3_span_active_rate_source": "solver_run_telemetry",
            "stage3_span_eval_total": 10.0,
            "stage3_span_eval_active": 5.0,
            "stage3_span_eval_skipped": 5.0,
            "stage3_span_seconds_total": 0.25,
            "stage3_span_seconds_active": 0.10,
            "stage3_basin_judge_span_calls_total": 4,
            "stage3_basin_judge_span_calls_active": 3,
            "stage3_basin_judge_span_calls_rejected_or_gated": 1,
            "stage3_basin_judge_span_seconds_total": 0.05,
        }

    fns = _build_fns()
    fns = replace(fns, run_stage3_iteration_flow_fn=_run_stage3)
    run_iteration_matrix(
        tiers=[SimpleNamespace(name="fixture_p7_c3_l200", period=7, columns=3, length=200)],
        text_offsets=[0],
        key_seeds=[4242],
        pt_base=list(range(400)),
        wli_base=[(i, i + 1) for i in range(20)],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=False,
        proven_index={},
        instances=[],
        stages=[],
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=cfg,
        fns=fns,
    )

    assert observed["stage35_enabled"] is True
    assert observed["stage35_cfg"] == {"rounds": 3, "beam_width": 4}


def test_no_wli_iteration_matrix_forwards_stage35_baseline_selector_into_stage3_state() -> None:
    cfg = replace(
        _config(),
        stage35_enabled=True,
        stage35_baseline_selector="score_plus_novelty",
    )
    observed: dict[str, object] = {}

    def _run_stage3(**kwargs):
        st = kwargs["state"]
        observed["stage35_baseline_selector"] = str(
            st["STAGE35_BASELINE_SELECTOR"]
        )
        return {
            "best3_match": 0.1,
            "best3_score": -1.0,
            "best_stage": "stage3_refine",
            "status": "unsolved",
            "stop_reason": "completed_pipeline",
            "stage3_span_active_rate": 0.5,
            "stage3_span_active_rate_source": "solver_run_telemetry",
            "stage3_span_eval_total": 10.0,
            "stage3_span_eval_active": 5.0,
            "stage3_span_eval_skipped": 5.0,
            "stage3_span_seconds_total": 0.25,
            "stage3_span_seconds_active": 0.10,
            "stage3_basin_judge_span_calls_total": 4,
            "stage3_basin_judge_span_calls_active": 3,
            "stage3_basin_judge_span_calls_rejected_or_gated": 1,
            "stage3_basin_judge_span_seconds_total": 0.05,
        }

    fns = _build_fns()
    fns = replace(fns, run_stage3_iteration_flow_fn=_run_stage3)
    run_iteration_matrix(
        tiers=[SimpleNamespace(name="fixture_p7_c3_l200", period=7, columns=3, length=200)],
        text_offsets=[0],
        key_seeds=[4242],
        pt_base=list(range(400)),
        wli_base=[(i, i + 1) for i in range(20)],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=False,
        proven_index={},
        instances=[],
        stages=[],
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=cfg,
        fns=fns,
    )

    assert observed["stage35_baseline_selector"] == "score_plus_novelty"


def test_no_wli_iteration_matrix_forwards_stage3_phasec_start_policy_into_stage3_state() -> None:
    cfg = replace(
        _config(),
        stage3_phasec_start_policy="novel_challenger_v1",
    )
    observed: dict[str, object] = {}

    def _run_stage3(**kwargs):
        st = kwargs["state"]
        observed["phasec_start_policy"] = str(st["STAGE3_PHASEC_START_POLICY"])
        return {
            "best3_match": 0.1,
            "best3_score": -1.0,
            "best_stage": "stage3_refine",
            "status": "unsolved",
            "stop_reason": "completed_pipeline",
            "stage3_span_active_rate": 0.5,
            "stage3_span_active_rate_source": "solver_run_telemetry",
            "stage3_span_eval_total": 10.0,
            "stage3_span_eval_active": 5.0,
            "stage3_span_eval_skipped": 5.0,
            "stage3_span_seconds_total": 0.25,
            "stage3_span_seconds_active": 0.10,
            "stage3_basin_judge_span_calls_total": 4,
            "stage3_basin_judge_span_calls_active": 3,
            "stage3_basin_judge_span_calls_rejected_or_gated": 1,
            "stage3_basin_judge_span_seconds_total": 0.05,
        }

    fns = _build_fns()
    fns = replace(fns, run_stage3_iteration_flow_fn=_run_stage3)
    run_iteration_matrix(
        tiers=[SimpleNamespace(name="fixture_p7_c3_l200", period=7, columns=3, length=200)],
        text_offsets=[0],
        key_seeds=[4242],
        pt_base=list(range(400)),
        wli_base=[(i, i + 1) for i in range(20)],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=False,
        proven_index={},
        instances=[],
        stages=[],
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=cfg,
        fns=fns,
    )

    assert observed["phasec_start_policy"] == "novel_challenger_v1"


def test_no_wli_iteration_matrix_filters_stage_engine_state_to_explicit_contract() -> None:
    observed: dict[str, object] = {}

    def _run_pre(**kwargs):
        state = kwargs["state"]
        observed["keys"] = set(state.keys())
        observed["scoring_experiment_meta"] = dict(state["scoring_experiment_meta"])
        return {"continue_iteration": True}

    fns = _build_fns()
    fns = replace(fns, run_iteration_pre_stage3_fn=_run_pre)
    run_iteration_matrix(
        tiers=[SimpleNamespace(name="fixture_p7_c3_l200", period=7, columns=3, length=200)],
        text_offsets=[0],
        key_seeds=[4242],
        pt_base=list(range(400)),
        wli_base=[(i, i + 1) for i in range(20)],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=False,
        proven_index={},
        instances=[],
        stages=[],
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=_config(),
        fns=fns,
    )

    keys = observed["keys"]
    assert "config" not in keys
    assert "fns" not in keys
    assert "stage3_runtime_call_ctx" not in keys
    assert "pt_base" not in keys
    assert "wli_base" not in keys
    assert observed["scoring_experiment_meta"] == {"profile": "off"}


def test_no_wli_iteration_matrix_propagates_require_batch_scoring_to_finalize_state() -> None:
    observed: dict[str, object] = {}

    def _finalize_post_stage3(**kwargs):
        observed["require_batch_scoring"] = bool(
            kwargs["state"]["REQUIRE_BATCH_SCORING"]
        )

    fns = _build_fns()
    fns = replace(fns, finalize_iteration_post_stage3_fn=_finalize_post_stage3)
    run_iteration_matrix(
        tiers=[SimpleNamespace(name="fixture_p7_c3_l200", period=7, columns=3, length=200)],
        text_offsets=[0],
        key_seeds=[4242],
        pt_base=list(range(400)),
        wli_base=[(i, i + 1) for i in range(20)],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=False,
        proven_index={},
        instances=[],
        stages=[],
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=replace(_config(), require_batch_scoring=False),
        fns=fns,
    )

    assert observed["require_batch_scoring"] is False


def test_no_wli_iteration_matrix_propagates_run_id_to_finalize_state() -> None:
    observed: dict[str, object] = {}

    def _finalize_post_stage3(**kwargs):
        observed["run_id"] = str(kwargs["state"].get("run_id", ""))

    fns = _build_fns()
    fns = replace(fns, finalize_iteration_post_stage3_fn=_finalize_post_stage3)
    run_iteration_matrix(
        run_id="test_run_001",
        tiers=[SimpleNamespace(name="fixture_p7_c3_l200", period=7, columns=3, length=200)],
        text_offsets=[0],
        key_seeds=[4242],
        pt_base=list(range(400)),
        wli_base=[(i, i + 1) for i in range(20)],
        direction=SimpleNamespace(value="ltr"),
        span_assets_dir=None,
        scoring_experiment_meta={"profile": "off"},
        autoskip_effective=False,
        proven_index={},
        instances=[],
        stages=[],
        stage3_runtime_call_ctx=SimpleNamespace(),
        config=_config(),
        fns=fns,
    )

    assert observed["run_id"] == "test_run_001"
