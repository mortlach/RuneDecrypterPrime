from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner


pytestmark = pytest.mark.tier_a


def test_no_wli_run_config_includes_stage3_span_aux_block() -> None:
    state = dict(no_wli_runner.__dict__)
    state["STAGE3_SPAN_AUX_ROLE"] = "shadow"
    state["STAGE3_SPAN_AUX_SCOPE"] = "basin_rep"
    state["STAGE3_SPAN_AUX_PROFILE"] = "lite"
    state["STAGE3_SPAN_AUX_BUDGET_MS"] = 12.5
    state["STAGE3_SPAN_AUX_TWO_PASS"] = True
    state["STAGE3_SPAN_AUX_FULL_TOP_M"] = 8
    state["SPAN_DECISION_ROLE_ENABLED"] = False
    state["SPAN_REPS_PER_BASIN"] = 2
    state["SPAN_SELECTION_TOP_K"] = 16
    state["SPAN_P90_CALL_MS"] = 3.0

    cfg = no_wli_runner._build_run_config_external(
        state=state,
        mode_canonical="adaptive_focus_v1",
        mode_raw="adaptive_focus_v1",
        mode_intent="focus",
        stage3_can_skip=False,
        scoring_experiment_meta={"profile": "off", "enabled": False},
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
    aux = cfg["stage3"]["span_aux"]
    assert aux["role"] == "shadow"
    assert aux["scope"] == "basin_rep"
    assert aux["profile"] == "lite"
    assert aux["budget_ms"] == pytest.approx(12.5)
    assert aux["two_pass_enabled"] is True
    assert aux["full_top_m"] == 8
    assert aux["decision_role_enabled"] is False
    assert aux["reps_per_basin"] == 2
    assert aux["selection_top_k"] == 16
    assert aux["p90_call_ms"] == pytest.approx(3.0)


def test_no_wli_run_config_requires_stage3_span_aux_keys() -> None:
    state = dict(no_wli_runner.__dict__)
    del state["STAGE3_SPAN_AUX_ROLE"]

    with pytest.raises(KeyError, match="STAGE3_SPAN_AUX_ROLE"):
        no_wli_runner._build_run_config_external(
            state=state,
            mode_canonical="adaptive_focus_v1",
            mode_raw="adaptive_focus_v1",
            mode_intent="focus",
            stage3_can_skip=False,
            scoring_experiment_meta={"profile": "off", "enabled": False},
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


def test_no_wli_run_config_requires_stage3_phasec_keys() -> None:
    state = dict(no_wli_runner.__dict__)
    del state["STAGE3_PHASEC_CFG"]

    with pytest.raises(KeyError, match="STAGE3_PHASEC_CFG"):
        no_wli_runner._build_run_config_external(
            state=state,
            mode_canonical="adaptive_focus_v1",
            mode_raw="adaptive_focus_v1",
            mode_intent="focus",
            stage3_can_skip=False,
            scoring_experiment_meta={"profile": "off", "enabled": False},
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


def test_no_wli_run_config_includes_stage3_phasec_start_policy() -> None:
    state = dict(no_wli_runner.__dict__)
    state["STAGE3_PHASEC_START_POLICY"] = "balanced_sources_v1"

    cfg = no_wli_runner._build_run_config_external(
        state=state,
        mode_canonical="adaptive_focus_v1",
        mode_raw="adaptive_focus_v1",
        mode_intent="focus",
        stage3_can_skip=False,
        scoring_experiment_meta={"profile": "off", "enabled": False},
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

    assert str(cfg["stage3"]["two_phase"]["phase_c"]["start_policy"]) == "balanced_sources_v1"
