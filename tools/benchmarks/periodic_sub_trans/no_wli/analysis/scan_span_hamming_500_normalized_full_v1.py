from __future__ import annotations

"""
Report-only full-data 500-token span-Hamming normalized feature scan.

This imports the canary pipeline after it has proven the mechanics, then widens
to the full S1 token-hash set and the efficient dictionary comparison set.
"""

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_span_hamming_500_normalized_canary_v1 as scan,
)


scan.RUN_LABEL = "span_hamming_500_normalized_full_v1"
scan.OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_normalized_full_v1"
)
scan.OUTPUT_DIR = scan.REPO_ROOT / scan.OUTPUT_DIR_REL

scan.TOKEN_HASH_LIMIT_FOR_CANARY = 0
scan.PROGRESS_EVERY_SAMPLES = 100
scan.PARITY_SPOT_CHECK = True
scan.PARITY_CONFIG_LIMIT = 3
scan.PARITY_SAMPLE_LIMIT = 2

scan.SPAN_CONFIG_SPECS = (
    dict(
        config_id="raw_selected_len3_14_hd2_cap256_norm500",
        dictionary_id="raw_selected",
        wordlist_rel="assets/hamming_raw_1g",
        require_selected=True,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
    ),
    dict(
        config_id="raw_all_len3_14_hd2_cap256_norm500",
        dictionary_id="raw_all",
        wordlist_rel="assets/hamming_raw_1g",
        require_selected=False,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
    ),
    dict(
        config_id="strict_selected_len3_14_hd2_cap256_norm500",
        dictionary_id="strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
    ),
    dict(
        config_id="broad_selected_len3_14_hd2_cap256_norm500",
        dictionary_id="broad_selected",
        wordlist_rel="assets/hamming_dictionary_policies/broad/hamming_raw_1g",
        require_selected=True,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
    ),
    dict(
        config_id="research_selected_len3_14_hd2_cap256_norm500",
        dictionary_id="research_selected",
        wordlist_rel="assets/hamming_dictionary_policies/research/hamming_raw_1g",
        require_selected=True,
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
    ),
)


def main() -> None:
    scan.main()


if __name__ == "__main__":
    main()
