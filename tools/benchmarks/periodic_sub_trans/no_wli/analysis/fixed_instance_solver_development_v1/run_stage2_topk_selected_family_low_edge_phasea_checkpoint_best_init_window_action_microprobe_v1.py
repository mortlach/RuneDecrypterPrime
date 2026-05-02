from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_both_action_microprobe_v1 as base_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1"
)
FILE_STEM = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action"
)
READOUT_TITLE = (
    "# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Action Microprobe v1"
)
RULE_ID = "best_init_ge_0p3865_from_restart32_v1"
WINDOW_START_RESTART_COUNT = 32
BEST_INIT_THRESHOLD = 0.3865
ACTION_CONTRACT_ID = "phasea_checkpoint_best_init_window_both_v1"
ACTION_CONTRACT_MODE = "fallback_and_early_stop"
NEXT_BRANCH_ADVANCE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch"
)
NEXT_BRANCH_REFINE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_refine"
)
QUESTION = (
    "If the retained 1111 family stabilizes at restart32 on "
    "phaseA_best_init_match >= 0.3865, does wiring that rule as both fallback "
    "and early stop save real wallclock on filtered 7001 while keeping 7005 "
    "no-harm relative to its prior exact replay?"
)
SUSPICION = (
    "Filtered 7001 should defer at restart16, flip to filter at restart32, "
    "fall back to baseline, and finish materially faster; kept 7005 should "
    "defer then keep at restart32 and stay no-harm."
)
MAIN_ALTERNATIVE = (
    "The restart32 best-init window may still save too little wallclock on the "
    "filtered lane, or the kept lane may drift enough that the simpler action "
    "contract is not honest yet."
)
IF_SUSPICION_TRUE_EXPECT = (
    "7001 should first emit a provisional action decision at restart32, apply "
    "fallback and early stop, land at the retained baseline, and save real "
    "wallclock; 7005 should first emit keep at restart32 and continue without "
    "action."
)
IF_ALTERNATIVE_TRUE_EXPECT = (
    "7001 may still save too little wallclock even with the restart32 rule, or "
    "7005 may fail the no-harm check."
)
DECISION_RULE = (
    "Advance only if filtered 7001 applies the restart32 best-init contract "
    "cleanly and kept 7005 stays no-harm relative to the prior exact replay. "
    "Refine if correctness holds but the filtered lane still saves too little "
    "wallclock. Hold if either canary fails the first best-init window action "
    "contract."
)
STOP_CONDITION = (
    "This microbatch is budgeted from the completed exact replay anchors on "
    "the same selector family: 7001 took about 00:23:41 and 7005 took about "
    "00:24:23, for an anchored total of about 00:48:04. After the first "
    "completed canary, recompute the projected two-job total from the observed "
    "completed row plus the remaining anchor. If that projection exceeds "
    "01:00:00, stop before launching the second canary."
)


def _build_phasea_provisional_gate_action_decider(
    *,
    reference_row: Mapping[str, Any],
    expected_gate_verdict: str,
) -> Any:
    baseline_best_match_ratio = base_mod._safe_float(
        reference_row.get("baseline_best_match_ratio")
    )
    baseline_best_stage = base_mod._safe_str(reference_row.get("baseline_best_stage"))

    def _decider(snapshot: Mapping[str, Any]) -> dict[str, Any]:
        checkpoint_count = base_mod._safe_int(snapshot.get("phaseA_checkpoint_restart_count"))
        if checkpoint_count < int(WINDOW_START_RESTART_COUNT):
            return {}
        best_value = base_mod._safe_float(snapshot.get("phaseA_best_init_match"))
        gate_verdict = (
            "keep" if best_value >= float(BEST_INIT_THRESHOLD) else "filter"
        )
        action_stop_now = int(1 if gate_verdict == "filter" else 0)
        return {
            "action_contract_id": ACTION_CONTRACT_ID,
            "action_contract_mode": ACTION_CONTRACT_MODE,
            "rule_id": RULE_ID,
            "window_start_restart_count": int(WINDOW_START_RESTART_COUNT),
            "best_init_threshold": float(BEST_INIT_THRESHOLD),
            "best_init_match": float(best_value),
            "gate_verdict": str(gate_verdict),
            "expected_gate_verdict": str(expected_gate_verdict),
            "trigger_source": (
                "best_init_window_keep"
                if gate_verdict == "keep"
                else "best_init_window_filter"
            ),
            "action_reason": (
                "best_init_window_keep_restart32"
                if gate_verdict == "keep"
                else "best_init_window_filter_restart32"
            ),
            "action_stop_now": int(action_stop_now),
            "action_fallback_to_baseline": int(action_stop_now),
            "resume_best_stage": (
                str(baseline_best_stage) if action_stop_now else ""
            ),
            "resume_best_match_ratio": (
                float(baseline_best_match_ratio) if action_stop_now else float("nan")
            ),
            "resume_best_score": float("nan"),
        }

    return _decider


def _build_child_run_label(search_seed: int) -> str:
    return (
        "stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_"
        f"exact_replay_1111_search{int(search_seed)}_v1"
    )


def _build_child_scope_note(search_seed: int) -> str:
    lane_role = base_mod._safe_str(base_mod.LANE_ROLE_BY_SEED.get(int(search_seed)))
    if lane_role == "filtered_canary":
        return (
            "exact retained replay wires the restart32 best-init checkpoint rule "
            "as both fallback and early stop on filtered 1111 canary 7001 so "
            "the read measures real saved wallclock"
        )
    return (
        "exact retained replay wires the restart32 best-init checkpoint rule "
        "as both fallback and early stop on kept 1111 canary 7005 so the read "
        "checks that the simpler action contract stays no-harm"
    )


def _configure_base_module() -> None:
    base_mod.RUN_LABEL = RUN_LABEL
    base_mod.FILE_STEM = FILE_STEM
    base_mod.READOUT_TITLE = READOUT_TITLE
    base_mod.RULE_ID = RULE_ID
    base_mod.RANK1_THRESHOLD = 2.0
    base_mod.BEST_THRESHOLD = float(BEST_INIT_THRESHOLD)
    base_mod.ACTION_CONTRACT_ID = ACTION_CONTRACT_ID
    base_mod.ACTION_CONTRACT_MODE = ACTION_CONTRACT_MODE
    base_mod.NEXT_BRANCH_ADVANCE_LABEL = NEXT_BRANCH_ADVANCE_LABEL
    base_mod.NEXT_BRANCH_REFINE_LABEL = NEXT_BRANCH_REFINE_LABEL
    base_mod.QUESTION = QUESTION
    base_mod.SUSPICION = SUSPICION
    base_mod.MAIN_ALTERNATIVE = MAIN_ALTERNATIVE
    base_mod.IF_SUSPICION_TRUE_EXPECT = IF_SUSPICION_TRUE_EXPECT
    base_mod.IF_ALTERNATIVE_TRUE_EXPECT = IF_ALTERNATIVE_TRUE_EXPECT
    base_mod.DECISION_RULE = DECISION_RULE
    base_mod.STOP_CONDITION = STOP_CONDITION
    base_mod._build_phasea_provisional_gate_action_decider = (
        _build_phasea_provisional_gate_action_decider
    )
    base_mod._build_child_run_label = _build_child_run_label
    base_mod._build_child_scope_note = _build_child_scope_note


def run_microprobe() -> dict[str, Any]:
    _configure_base_module()
    return base_mod.run_microprobe()


def main() -> None:
    _configure_base_module()
    print(base_mod.json.dumps(base_mod.run_microprobe(), sort_keys=True))


if __name__ == "__main__":
    main()
