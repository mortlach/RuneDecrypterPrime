from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_strict_full80_bucket_common_v1 import (
    run_strict_bucket,
)


PHASE = "phaseB_failed_decryption_n3c_strict_full80_bucket_12_14_query_evidence_v1"
LENGTH_BUCKET = "12-14"
MAX_TOTAL_RUNTIME_SECONDS = 7_200.0


if __name__ == "__main__":
    run_strict_bucket(LENGTH_BUCKET, PHASE, MAX_TOTAL_RUNTIME_SECONDS)
