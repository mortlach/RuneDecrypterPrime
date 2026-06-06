from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 as full80,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import length_bucket


ORIGINAL_SELECTOR = full80.select_full_n3c_chunks


def select_bucket_15_17_chunks(files: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        row for row in ORIGINAL_SELECTOR(files)
        if length_bucket(int(row["phrase_token_length"])) == "15-17"
    ]


full80.PHASE = "phaseB_failed_decryption_n3c_full80_bucket_15_17_query_evidence_v1"
full80.OUTPUT_DIR = (
    full80.REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / full80.PHASE
)
full80.MAX_TOTAL_RUNTIME_SECONDS = 7_200.0
full80.QUERY_SCOPE_LABEL = "budget_anchor_full_15_17_bucket_only_for_selected_80_candidates"
full80.QUERY_IS_FULL_N3C_FOR_SELECTED_80 = False
full80.select_full_n3c_chunks = select_bucket_15_17_chunks


if __name__ == "__main__":
    full80.run_full80()
