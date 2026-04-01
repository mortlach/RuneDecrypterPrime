from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_stageb_continuation import (
    load_and_write_stageb_continuation_report,
)


SELECTED_ROWS_PATH = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "late_stage_selector_stageb_v46"
    / "selected_trial_material_rows.json"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "late_stage_selector_stageb_v46_continuation"
)


def main() -> None:
    summary = load_and_write_stageb_continuation_report(
        selected_rows_path=SELECTED_ROWS_PATH,
        output_dir=OUTPUT_DIR,
    )
    print(
        json.dumps(
            dict(
                selected_rows_path=str(
                    SELECTED_ROWS_PATH.relative_to(REPO_ROOT)
                ).replace("\\", "/"),
                output_dir=str(OUTPUT_DIR.relative_to(REPO_ROOT)).replace("\\", "/"),
                row_count=int(summary.get("row_count", 0) or 0),
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
