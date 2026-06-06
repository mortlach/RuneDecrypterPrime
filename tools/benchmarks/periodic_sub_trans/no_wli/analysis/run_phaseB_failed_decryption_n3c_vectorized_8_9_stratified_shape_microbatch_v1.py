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


def select_stratified_8_9_groups(files: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = sorted(
        (
            row for row in files
            if row["direction"] == "fwd"
            and int(row["ngram_order"]) == 3
            and row["dictionary_cut"] == "normal"
            and int(row["phrase_token_length"]) >= 8
            and length_bucket(int(row["phrase_token_length"])) == "8-9"
        ),
        key=lambda row: (int(row["phrase_count"]), str(row["path"])),
    )
    picks = (
        (0, "rare"), (1, "rare"),
        (len(rows) // 2 - 1, "medium"), (len(rows) // 2, "medium"), (len(rows) // 2 + 1, "medium"),
        (len(rows) - 3, "common"), (len(rows) - 2, "common"), (len(rows) - 1, "common"),
    )
    return [
        {
            **rows[index], "shape_frequency_class": frequency_class,
            "shape_frequency_rank": index + 1, "bucket_group_count": len(rows),
        }
        for index, frequency_class in picks
    ]


microbatch.PHASE = "phaseB_failed_decryption_n3c_vectorized_8_9_stratified_shape_microbatch_v1"
microbatch.OUTPUT_DIR = (
    microbatch.REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / microbatch.PHASE
)
microbatch.select_medium_groups = select_stratified_8_9_groups
microbatch.MAX_TOTAL_RUNTIME_SECONDS = 300.0
microbatch.QUERY_SCOPE = "eight_stratified_8_9_groups_diverse_80_candidate_microbatch"
microbatch.READOUT_TITLE = "N3C Stratified 8-9 Query Microbatch"


if __name__ == "__main__":
    microbatch.run_microbatch()
