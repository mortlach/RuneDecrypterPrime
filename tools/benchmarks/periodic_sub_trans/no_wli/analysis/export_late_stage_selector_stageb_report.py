from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_stageb import (
    load_and_write_stageb_replay_report,
)


FIXTURE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "late_stage_frontier_fixtures"
)
CONTROL_FIXTURE_PATH = FIXTURE_DIR / "v46_seed411_control_replay_frontier.json"
CANDIDATE_FIXTURE_PATH = FIXTURE_DIR / "v46_seed411_candidate_replay_frontier.json"
OUTPUT_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "late_stage_selector_stageb_v46"
)


def main() -> None:
    summary = load_and_write_stageb_replay_report(
        control_fixture_path=CONTROL_FIXTURE_PATH,
        candidate_fixture_path=CANDIDATE_FIXTURE_PATH,
        output_dir=OUTPUT_DIR,
    )
    print(
        json.dumps(
            dict(
                output_dir=str(OUTPUT_DIR.relative_to(REPO_ROOT)).replace("\\", "/"),
                control_fixture=str(CONTROL_FIXTURE_PATH.relative_to(REPO_ROOT)).replace(
                    "\\", "/"
                ),
                candidate_fixture=str(
                    CANDIDATE_FIXTURE_PATH.relative_to(REPO_ROOT)
                ).replace("\\", "/"),
                control_replay_ready=int(
                    summary.get("control", {}).get("replay_ready_selected_candidates", 0)
                    or 0
                ),
                candidate_replay_ready=int(
                    summary.get("candidate", {}).get(
                        "replay_ready_selected_candidates", 0
                    )
                    or 0
                ),
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
