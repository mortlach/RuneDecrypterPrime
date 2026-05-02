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
        "run_stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    run_stage35_resume_from_handoff_focus_family_rescue_real_7005_v1 as base_run,
)


RUN_LABEL = "stage35_resume_from_handoff_focus_family_rescue_real_7005_guard_selector_v1"
RUN_MODE = "real_selected_best_frontier_one_round_guard_selector"

STAGE35_CFG_OVERRIDE: dict[str, Any] = dict(base_run.REAL_STAGE35_CFG_OVERRIDE)
STAGE35_CFG_OVERRIDE.update(
    {
        "accept_guard_passing_selector_mode": "top_score_then_search",
    }
)


def _rewrite_readout(output_dir: Path) -> None:
    readout_path = output_dir / "stage35_resume_real_7005_readout.md"
    if not readout_path.exists():
        return
    text = readout_path.read_text(encoding="utf-8")
    text = text.replace(
        "# Stage35 Resume From Handoff Focus-Family Rescue v1 Real 7005 Run",
        "# Stage35 Resume From Handoff Focus-Family Rescue v1 Real 7005 Guard-Selector Run",
    )
    text = text.replace(
        "- run the first real selected-best-frontier late-stage comparison on `1111/search7005`",
        "- run the guard-passing-selector follow-up on `1111/search7005`",
    )
    text = text.replace(
        "  - `max_runtime_seconds = 0`",
        "  - `max_runtime_seconds = 0`\n  - `accept_guard_passing_selector_mode = top_score_then_search`",
    )
    text = text.replace(
        "- extract the completed bundle and compare it against the retained `0.372` and selected-row start `0.416`\n"
        "- decide whether the smaller `1111/search7004` selected-row headroom is worth a secondary confirmation run",
        "- compare the accepted guard-selector result against the posthoc `0.422` archive read\n"
        "- decide whether the smaller `1111/search7004` selected-row headroom is still worth a secondary confirmation run",
    )
    readout_path.write_text(text, encoding="utf-8")


def run_guard_selector_7005() -> dict[str, Any]:
    base_run.RUN_LABEL = RUN_LABEL
    base_run.RUN_MODE = RUN_MODE
    base_run.REAL_STAGE35_CFG_OVERRIDE = dict(STAGE35_CFG_OVERRIDE)
    result = dict(base_run.run_real_7005())
    output_dir = base_run.REPO_ROOT / str(result["output_dir"])
    _rewrite_readout(output_dir)
    return result


def main() -> None:
    print(json.dumps(run_guard_selector_7005(), sort_keys=True))


if __name__ == "__main__":
    main()
