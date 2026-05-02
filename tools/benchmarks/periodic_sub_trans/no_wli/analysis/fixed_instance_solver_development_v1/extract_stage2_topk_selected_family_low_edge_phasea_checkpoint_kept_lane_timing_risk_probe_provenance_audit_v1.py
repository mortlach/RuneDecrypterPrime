from __future__ import annotations

import json
import sys
from pathlib import Path


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_provenance_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_provenance_audit_v1 as audit_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    run_stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_v1 as probe_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_provenance_audit_v1"
)
FILE_STEM = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_kept_lane_timing_risk_probe_provenance_audit"
)
READOUT_TITLE = (
    "# Stage-2 Selected-Family Phase-A Checkpoint Kept-Lane Timing-Risk Probe Provenance Audit v1"
)
SOURCE_BUNDLE_DIR: Path | None = None
USE_LATEST_SOURCE_BUNDLE = True


def configure_audit_module_for_probe() -> None:
    probe_mod.configure_live_module_for_probe()
    probe_mod.live_mod.LIVE_CANARY_LAUNCH_APPROVED = False
    audit_mod.RUN_LABEL = RUN_LABEL
    audit_mod.FILE_STEM = FILE_STEM
    audit_mod.READOUT_TITLE = READOUT_TITLE
    audit_mod.SOURCE_BUNDLE_DIR = SOURCE_BUNDLE_DIR
    audit_mod.USE_LATEST_SOURCE_BUNDLE = bool(USE_LATEST_SOURCE_BUNDLE)


def run_audit() -> dict[str, object]:
    configure_audit_module_for_probe()
    return audit_mod.run_audit()


if __name__ == "__main__":
    print(json.dumps(run_audit(), sort_keys=True))
