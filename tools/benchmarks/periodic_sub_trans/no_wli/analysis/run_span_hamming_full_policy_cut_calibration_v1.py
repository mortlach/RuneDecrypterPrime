from __future__ import annotations

"""
Report-only full span-Hamming calibration with restored policy-cut assets.

This wrapper keeps the original S1f calibration script unchanged and redirects
the full 243-config run to a fresh output directory.
"""

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    calibrate_span_hamming_full_space_v1 as calibration,
)


calibration.RUN_LABEL = "span_hamming_full_policy_cut_calibration_v1"
calibration.OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_full_policy_cut_calibration_v1"
)
calibration.OUTPUT_DIR = calibration.REPO_ROOT / calibration.OUTPUT_DIR_REL

calibration.TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0
calibration.PROGRESS_EVERY_CANDIDATES = 100
calibration.PYTHON_PARITY_SPOT_CHECK = True
calibration.PYTHON_PARITY_TOKEN_LIMIT = 4
calibration.PYTHON_PARITY_CONFIG_LIMIT = 3


def main() -> None:
    calibration.main()


if __name__ == "__main__":
    main()
