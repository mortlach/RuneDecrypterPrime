from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_benchmark import (
    load_late_stage_frontier_fixture,
    load_phasec_truth_gap_rows,
    write_late_stage_selector_stagea_report,
)


FIXTURE_PATH = Path(
    "tests/fixtures/no_wli/v45_seed411_late_frontier_fixture.json"
)
TRUTH_GAP_ROWS_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json"
)
OUTPUT_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea"
)


def main() -> None:
    fixture = load_late_stage_frontier_fixture(FIXTURE_PATH)
    rows = load_phasec_truth_gap_rows(TRUTH_GAP_ROWS_PATH)
    summary = write_late_stage_selector_stagea_report(
        fixture=fixture,
        truth_gap_rows=rows,
        output_dir=OUTPUT_DIR,
    )
    print(
        "[no_wli_late_stage_selector_stagea] "
        f"fixture={summary['fixture_id']} "
        f"disagreement_rows={summary['dataset_summary']['disagreement_row_count']} "
        f"weighted={summary['selector_evaluation']['revised_candidate_hash']} "
        f"pairwise={summary['selector_evaluation']['pairwise_candidate_hash']}"
    )


if __name__ == "__main__":
    main()
