from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


def evaluate_stage3_entry_policy(
    *,
    tier_name: str,
    text_id: int,
    key_seed: int,
    best2_match: float,
    solve_match_threshold: float,
    scan_mode_active: bool,
    scan_time_cap_seconds: float,
    tier_elapsed_before_stage3: float,
    scan_stage3_gate_low_match: float,
    scan_stage3_gate_high_match: float,
    stage2_continue_to_gate: bool,
    stage2_continue_stop_reason: str,
    stages: List[Dict[str, Any]],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    stop_reason = "completed_pipeline"
    stage3_band_name = ""
    stage3_scan_phaseA_only = False
    policy_branch = "continue"

    if np.isfinite(best2_match) and best2_match >= float(solve_match_threshold):
        stop_reason = "solved_stage2"
        policy_branch = "solved_stage2"
    elif (
        bool(scan_mode_active)
        and (float(scan_time_cap_seconds) > 0.0)
        and (float(tier_elapsed_before_stage3) >= float(scan_time_cap_seconds))
    ):
        stop_reason = (
            f"time_cap_before_stage3:"
            f"elapsed={float(tier_elapsed_before_stage3):.1f}:"
            f"cap={float(scan_time_cap_seconds):.1f}"
        )
        stage3_band_name = "time_cap"
        policy_branch = "time_cap_skip"
        print(
            f"{log_prefix} stage3-skip tier={tier_name} text={text_id} key_seed={key_seed} "
            f"reason=time_cap elapsed={float(tier_elapsed_before_stage3):.1f}s "
            f"cap={float(scan_time_cap_seconds):.1f}s",
            flush=True,
        )
        stages.append(
            dict(
                tier=str(tier_name),
                text_id=int(text_id),
                key_seed=int(key_seed),
                stage="stage3_skipped",
                score=float("nan"),
                match_ratio=float("nan"),
                seconds=0.0,
                evals=0,
                reason="time_cap",
                elapsed_seconds=float(tier_elapsed_before_stage3),
                cap_seconds=float(scan_time_cap_seconds),
            )
        )
    elif (
        bool(scan_mode_active)
        and np.isfinite(float(best2_match))
        and (float(best2_match) < float(scan_stage3_gate_low_match))
    ):
        weak_reason = (
            "stage2_cap_weak_stage2"
            if (bool(stage2_continue_to_gate) and str(stage2_continue_stop_reason) == "cap")
            else "weak_stage2"
        )
        stop_reason = (
            f"scan_skip_stage3_{str(weak_reason)}:"
            f"best2_match={float(best2_match):.3f}:"
            f"threshold={float(scan_stage3_gate_low_match):.3f}"
        )
        stage3_band_name = "stage2_cap_skip" if str(weak_reason).startswith("stage2_cap") else "weak_stage2_skip"
        policy_branch = str(weak_reason)
        print(
            f"{log_prefix} stage3-skip tier={tier_name} text={text_id} key_seed={key_seed} "
            f"reason={str(weak_reason)} best2_match={float(best2_match):.3f} "
            f"threshold={float(scan_stage3_gate_low_match):.3f}",
            flush=True,
        )
        stages.append(
            dict(
                tier=str(tier_name),
                text_id=int(text_id),
                key_seed=int(key_seed),
                stage="stage3_skipped",
                score=float("nan"),
                match_ratio=float("nan"),
                seconds=0.0,
                evals=0,
                reason=str(weak_reason),
                best2_match=float(best2_match),
                threshold=float(scan_stage3_gate_low_match),
            )
        )
    elif (
        bool(scan_mode_active)
        and np.isfinite(float(best2_match))
        and (float(best2_match) < float(scan_stage3_gate_high_match))
    ):
        stage3_scan_phaseA_only = True
        policy_branch = "phaseA_only"
        print(
            f"{log_prefix} stage3-policy tier={tier_name} text={text_id} key_seed={key_seed} "
            f"policy=phaseA_only best2_match={float(best2_match):.3f} "
            f"gate_low={float(scan_stage3_gate_low_match):.3f} "
            f"gate_high={float(scan_stage3_gate_high_match):.3f}",
            flush=True,
        )
        stages.append(
            dict(
                tier=str(tier_name),
                text_id=int(text_id),
                key_seed=int(key_seed),
                stage="stage3_policy",
                policy="phaseA_only",
                best2_match=float(best2_match),
                gate_low=float(scan_stage3_gate_low_match),
                gate_high=float(scan_stage3_gate_high_match),
            )
        )

    return dict(
        stop_reason=str(stop_reason),
        stage3_band_name=str(stage3_band_name),
        stage3_scan_phaseA_only=bool(stage3_scan_phaseA_only),
        policy_branch=str(policy_branch),
    )
