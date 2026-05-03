from __future__ import annotations

"""
Report-only focused span-Hamming dictionary policy comparison.

This intentionally reuses the S1f calibration implementation with a narrow,
hardcoded config set: one S1b-shaped span scan over the current selected list
and the four policy-cut assets.
"""

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    calibrate_span_hamming_full_space_v1 as calibration,
)


calibration.RUN_LABEL = "span_hamming_policy_cut_comparison_v1"
calibration.OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_policy_cut_comparison_v1"
)
calibration.OUTPUT_DIR = calibration.REPO_ROOT / calibration.OUTPUT_DIR_REL

calibration.TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0
calibration.PROGRESS_EVERY_CANDIDATES = 100
calibration.TIMING_SAMPLE_TOKEN_LIMIT = 12
calibration.CANDIDATE_CAPS = (256,)
calibration.INCLUDE_CAP_2048 = False
calibration.PYTHON_PARITY_SPOT_CHECK = True
calibration.PYTHON_PARITY_TOKEN_LIMIT = 4
calibration.PYTHON_PARITY_CONFIG_LIMIT = 3

calibration.DICTIONARY_SPECS = (
    dict(dictionary_id="raw_selected", wordlist_rel="assets/hamming_raw_1g", require_selected=True),
    dict(
        dictionary_id="strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="normal_selected",
        wordlist_rel="assets/hamming_dictionary_policies/normal/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="broad_selected",
        wordlist_rel="assets/hamming_dictionary_policies/broad/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="research_selected",
        wordlist_rel="assets/hamming_dictionary_policies/research/hamming_raw_1g",
        require_selected=True,
    ),
)

calibration.SPAN_TEMPLATE_SPECS = (
    dict(template_id="len3_14_hd2_s1b_shape", len_min=3, len_max=14, max_hd=2),
)


def main() -> None:
    calibration.main()


if __name__ == "__main__":
    main()
