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


microbatch.PHASE = "phaseB_failed_decryption_n3c_vectorized_10_11_group_canary_v1"
microbatch.OUTPUT_DIR = (
    microbatch.REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / microbatch.PHASE
)
microbatch.BUCKET_ORDER = ("10-11",)
microbatch.MAX_TOTAL_RUNTIME_SECONDS = 180.0


if __name__ == "__main__":
    microbatch.run_microbatch()
