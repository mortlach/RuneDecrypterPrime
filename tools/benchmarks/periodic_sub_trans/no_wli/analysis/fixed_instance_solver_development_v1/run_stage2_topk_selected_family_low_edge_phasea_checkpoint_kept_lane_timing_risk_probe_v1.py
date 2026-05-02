from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1 as live_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1"
)
FILE_STEM = "stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe"
READOUT_TITLE = (
    "# Stage-2 Selected-Family Phase-A Checkpoint Kept-Lane Timing-Risk Probe v1"
)
FIXTURE_SEED = 1111
SEARCH_SEEDS = (7003,)
LANE_ROLE_BY_SEED = {7003: "kept_family"}
EXPECTED_GATE_VERDICT_BY_SEED = {7003: "keep"}
INTENDED_WALLCLOCK_BUDGET_HOURS = 8.0
MAX_WALLCLOCK_SECONDS = INTENDED_WALLCLOCK_BUDGET_HOURS * 3600.0
QUESTION = (
    "Does the kept/no-action live runtime path for 1111/search7003 reproduce "
    "the prior 1.409x slowdown, or was the earlier kept canary an isolated "
    "timing event?"
)
SUSPICION = (
    "A repeat kept/no-action timing probe will preserve the selected path but "
    "may again show live runtime inflation by checkpoint32 and through Phase B."
)
MAIN_ALTERNATIVE = (
    "The prior live kept/no-action slowdown was transient runtime variance; a "
    "repeat probe returns close to the retained exact replay and family-action "
    "timing class."
)
DECISION_RULE = (
    "Advance timing analysis only if the probe completes or cleanly reaches "
    "the checkpoint surface, all artefact layers agree, row recomputation has "
    "zero mismatches, and the elapsed timing can be compared against the "
    "retained exact replay, family-action replay, and prior live kept canary. "
    "Otherwise hold."
)
STOP_CONDITION = (
    "Run exactly one 1111/search7003 kept/no-action timing-risk probe with an "
    "08:00:00 cap. Stop after this one run. Hold if it exceeds the cap without "
    "usable checkpoint evidence or if the output bundle is not auditable."
)


def _build_child_run_label(search_seed: int) -> str:
    return (
        "stage2_topk_selected_family_low_edge_phasea_checkpoint_"
        f"kept_lane_timing_risk_probe_exact_replay_1111_search{int(search_seed)}_v1"
    )


def _build_child_scope_note(search_seed: int) -> str:
    return (
        "one-cell kept/no-action timing-risk probe repeats the reviewed "
        "restart32 best-init checkpoint on 1111/search7003; the run tests "
        "live timing reproducibility and auditability, not threshold tuning, "
        "selector development, or broad runtime reopening"
    )


def configure_live_module_for_probe() -> None:
    live_mod.RUN_LABEL = RUN_LABEL
    live_mod.FILE_STEM = FILE_STEM
    live_mod.READOUT_TITLE = READOUT_TITLE
    live_mod.LIVE_CANARY_LAUNCH_APPROVED = True
    live_mod.FIXTURE_SEED = FIXTURE_SEED
    live_mod.SEARCH_SEEDS = tuple(SEARCH_SEEDS)
    live_mod.LANE_ROLE_BY_SEED = dict(LANE_ROLE_BY_SEED)
    live_mod.EXPECTED_GATE_VERDICT_BY_SEED = dict(EXPECTED_GATE_VERDICT_BY_SEED)
    live_mod.INTENDED_WALLCLOCK_BUDGET_HOURS = float(INTENDED_WALLCLOCK_BUDGET_HOURS)
    live_mod.MAX_WALLCLOCK_SECONDS = float(MAX_WALLCLOCK_SECONDS)
    live_mod.QUESTION = QUESTION
    live_mod.SUSPICION = SUSPICION
    live_mod.MAIN_ALTERNATIVE = MAIN_ALTERNATIVE
    live_mod.DECISION_RULE = DECISION_RULE
    live_mod.STOP_CONDITION = STOP_CONDITION
    live_mod.NEXT_BRANCH_ADVANCE_LABEL = (
        "stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_review"
    )
    live_mod.NEXT_BRANCH_REFINE_LABEL = (
        "stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_harness_refine"
    )
    live_mod._build_child_run_label = _build_child_run_label
    live_mod._build_child_scope_note = _build_child_scope_note


def run_probe() -> dict[str, Any]:
    configure_live_module_for_probe()
    return live_mod.run_live_canary()


if __name__ == "__main__":
    print(json.dumps(run_probe(), sort_keys=True))
