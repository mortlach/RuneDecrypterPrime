from __future__ import annotations

"""
Report-only full-data wrapper for the fixed-500 length/HD fingerprint scan.
"""

import sys
from pathlib import Path


def _bootstrap_repo_root() -> None:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            src_dir = parent / "src"
            if src_dir.exists() and str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))
            return
    raise RuntimeError("Could not locate repo root from script path")


_bootstrap_repo_root()

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    scan_span_hamming_500_length_hd_fingerprint_canary_v1 as scan,
)


scan.RUN_LABEL = "span_hamming_500_length_hd_fingerprint_full_v1"
scan.OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_length_hd_fingerprint_full_v1"
)
scan.OUTPUT_DIR = scan.REPO_ROOT / scan.OUTPUT_DIR_REL
scan.TOKEN_HASH_LIMIT_FOR_CANARY = 0
scan.PROGRESS_EVERY_SCORES = 100


def main() -> None:
    scan.main()


if __name__ == "__main__":
    main()
