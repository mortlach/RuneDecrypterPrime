from __future__ import annotations

from typing import Any, Callable, Dict, List

import numpy as np


def handle_oracle_floor_guard_if_triggered(
    *,
    oracle_pre: Dict[str, Any],
    tier: Any,
    text_id: int,
    key_seed: int,
    off: int,
    offset_used: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    oracle_mode: str,
    oracle_consulted_in_decisions: bool,
    stage3_continue_after_solve: bool,
    stage3_phaseb_top_n: int,
    stage3_phaseb_gate_delta_floor: float,
    stage3_phaseb_gate_end_gain_floor: float,
    stage3_c1_focus_enabled: bool,
    build_oracle_floor_guard_result_fn: Callable[..., Dict[str, Any]],
    build_iteration_payloads_fn: Callable[..., Any],
    derive_outcome_code_fn: Callable[..., str],
    commit_iteration_with_checkpoint_fn: Callable[..., None],
    mark_oracle_decision_use_fn: Callable[[], None],
    stages: List[Dict[str, Any]],
    instances: List[Dict[str, Any]],
) -> bool:
    if not bool(oracle_pre.get("floor_guard_triggered", False)):
        return False
    mark_oracle_decision_use_fn()
    stage3_floor_threshold = float(oracle_pre["stage3_floor_threshold"])
    stop_reason = str(oracle_pre["floor_guard_stop_reason"])
    outcome_code = derive_outcome_code_fn(status="stalled", stop_reason=stop_reason)
    floor_guard_result = build_oracle_floor_guard_result_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        off=int(off),
        offset_used=int(offset_used),
        stop_reason=str(stop_reason),
        outcome_code=str(outcome_code),
        stage3_floor_threshold=float(stage3_floor_threshold),
        oracle_s1=float(oracle_pre["oracle_s1"]),
        oracle_s2=float(oracle_pre["oracle_s2"]),
        oracle_s3=float(oracle_pre["oracle_s3"]),
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        stage3_continue_after_solve=bool(stage3_continue_after_solve),
        stage3_phaseB_top_n=int(stage3_phaseb_top_n),
        stage3_phaseB_gate_delta_floor=float(stage3_phaseb_gate_delta_floor),
        stage3_phaseB_gate_end_gain_floor=float(stage3_phaseb_gate_end_gain_floor),
        c1_focus=int(
            1 if (int(tier.columns) <= 1 and bool(stage3_c1_focus_enabled)) else 0
        ),
        build_iteration_payloads_fn=build_iteration_payloads_fn,
    )
    stages.append(dict(floor_guard_result["stage_row"]))
    inst_row = dict(floor_guard_result["inst_row"])
    artifact_payload = dict(floor_guard_result["artifact_payload"])
    instances.append(dict(inst_row))
    commit_iteration_with_checkpoint_fn(
        inst_row=inst_row,
        artifact_payload=artifact_payload,
        status_key="stalled",
    )
    return True
