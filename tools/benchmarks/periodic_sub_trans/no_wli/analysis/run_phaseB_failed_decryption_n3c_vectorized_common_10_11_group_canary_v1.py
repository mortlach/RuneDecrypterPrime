from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_medium_shape_diverse_candidate_microbatch_v1 as microbatch,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import length_bucket


def select_common_10_11_group(files: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = sorted(
        (
            row for row in files
            if row["direction"] == "fwd"
            and int(row["ngram_order"]) == 3
            and row["dictionary_cut"] == "normal"
            and int(row["phrase_token_length"]) >= 8
            and length_bucket(int(row["phrase_token_length"])) == "10-11"
        ),
        key=lambda row: (int(row["phrase_count"]), str(row["path"])),
    )
    return [{
        **rows[-1], "shape_frequency_class": "common",
        "shape_frequency_rank": len(rows), "bucket_group_count": len(rows),
    }]


microbatch.PHASE = "phaseB_failed_decryption_n3c_vectorized_common_10_11_group_canary_v1"
microbatch.OUTPUT_DIR = (
    microbatch.REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / microbatch.PHASE
)
microbatch.select_medium_groups = select_common_10_11_group
microbatch.MAX_TOTAL_RUNTIME_SECONDS = 180.0


if __name__ == "__main__":
    microbatch.run_microbatch()
