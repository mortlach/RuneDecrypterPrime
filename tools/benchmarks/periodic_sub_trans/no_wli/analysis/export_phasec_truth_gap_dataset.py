from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_truth_gap_dataset import (
    collect_phasec_truth_gap_rows,
    write_phasec_truth_gap_dataset,
)

RUN_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli")
OUTPUT_DIR = RUN_ROOT / "analysis" / "phasec_truth_gap_dataset"
TOP_N = 12


def main() -> None:
    rows = collect_phasec_truth_gap_rows(RUN_ROOT)
    summary = write_phasec_truth_gap_dataset(
        rows=rows,
        output_dir=OUTPUT_DIR,
        top_n=int(TOP_N),
    )
    print(
        "[no_wli_phasec_truth_gap_dataset] "
        + f"rows={int(summary.get('row_count', 0))} "
        + f"summary={str((OUTPUT_DIR / 'summary.json')).replace(chr(92), '/')}",
        flush=True,
    )


if __name__ == "__main__":
    main()
