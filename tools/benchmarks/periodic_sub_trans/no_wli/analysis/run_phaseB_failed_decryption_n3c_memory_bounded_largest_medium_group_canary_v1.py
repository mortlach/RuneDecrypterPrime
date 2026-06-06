from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_memory_bounded_medium_group_canary_v1 as canary,
)


canary.PHASE = "phaseB_failed_decryption_n3c_memory_bounded_largest_medium_group_canary_v1"
canary.OUTPUT_DIR = (
    canary.REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / canary.PHASE
)
canary.TARGET_BUCKET = "12-14"


if __name__ == "__main__":
    canary.run_canary()
