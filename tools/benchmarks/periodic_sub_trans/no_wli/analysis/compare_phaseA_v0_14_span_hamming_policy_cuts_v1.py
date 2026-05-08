from __future__ import annotations

"""
Report-only old-vs-Phase-A-v0.14 span-Hamming policy comparison.

No runtime solver behaviour changes. No CLI arguments. Edit constants below if a
larger or smaller canary is needed.
"""

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    calibrate_span_hamming_full_space_v1 as calibration,
)


RUN_LABEL = "phaseA14_span_hamming_policy_cut_comparison_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseA14_span_hamming_policy_cut_comparison_v1"
)

DICTIONARY_SPECS = (
    dict(
        dictionary_id="old_strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="old_normal_selected",
        wordlist_rel="assets/hamming_dictionary_policies/normal/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="phaseA14_strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies_phaseA_v0_14/strict/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        dictionary_id="phaseA14_normal_selected",
        wordlist_rel="assets/hamming_dictionary_policies_phaseA_v0_14/normal/hamming_raw_1g",
        require_selected=True,
    ),
)

SPAN_TEMPLATE_SPECS = (
    dict(template_id="len3_14_hd2_s1b_shape", len_min=3, len_max=14, max_hd=2),
    dict(template_id="len5_14_hd2_longer", len_min=5, len_max=14, max_hd=2),
    dict(template_id="len8_14_hd2_long_signal", len_min=8, len_max=14, max_hd=2),
    dict(template_id="len10_14_hd2_very_long_signal", len_min=10, len_max=14, max_hd=2),
)

# 0 means the full available S1 token set. Set a small number locally if you
# want a short IDE smoke run before the full comparison.
TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0
PROGRESS_EVERY_CANDIDATES = 50
TIMING_SAMPLE_TOKEN_LIMIT = 12
CANDIDATE_CAPS = (256, 512)
INCLUDE_CAP_2048 = False
PYTHON_PARITY_SPOT_CHECK = True
PYTHON_PARITY_TOKEN_LIMIT = 4
PYTHON_PARITY_CONFIG_LIMIT = 4


def _apply_config() -> None:
    calibration.RUN_LABEL = RUN_LABEL
    calibration.OUTPUT_DIR_REL = OUTPUT_DIR_REL
    calibration.OUTPUT_DIR = calibration.REPO_ROOT / OUTPUT_DIR_REL
    calibration.DICTIONARY_SPECS = DICTIONARY_SPECS
    calibration.SPAN_TEMPLATE_SPECS = SPAN_TEMPLATE_SPECS
    calibration.TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = TOKEN_HASH_LIMIT_FOR_DEV_SMOKE
    calibration.PROGRESS_EVERY_CANDIDATES = PROGRESS_EVERY_CANDIDATES
    calibration.TIMING_SAMPLE_TOKEN_LIMIT = TIMING_SAMPLE_TOKEN_LIMIT
    calibration.CANDIDATE_CAPS = CANDIDATE_CAPS
    calibration.INCLUDE_CAP_2048 = INCLUDE_CAP_2048
    calibration.PYTHON_PARITY_SPOT_CHECK = PYTHON_PARITY_SPOT_CHECK
    calibration.PYTHON_PARITY_TOKEN_LIMIT = PYTHON_PARITY_TOKEN_LIMIT
    calibration.PYTHON_PARITY_CONFIG_LIMIT = PYTHON_PARITY_CONFIG_LIMIT


def main() -> None:
    _apply_config()
    calibration.main()


if __name__ == "__main__":
    main()
