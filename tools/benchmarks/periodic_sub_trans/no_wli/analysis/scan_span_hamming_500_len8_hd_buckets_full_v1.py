from __future__ import annotations

"""
Report-only full-data wrapper for the fixed-500 len-8 HD bucket diagnostic.
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

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_span_hamming_500_len8_hd_buckets_canary_v1 as scan,
)


scan.RUN_LABEL = "span_hamming_500_len8_hd_buckets_full_v1"
scan.OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_len8_hd_buckets_full_v1"
)
scan.OUTPUT_DIR = scan.REPO_ROOT / scan.OUTPUT_DIR_REL

scan.TOKEN_HASH_LIMIT_FOR_CANARY = 0
scan.PROGRESS_EVERY_SAMPLES = 100

scan.SPAN_CONFIG_SPECS = (
    dict(
        config_id="raw_selected_len8_hd4_cap256_norm500",
        dictionary_id="raw_selected",
        wordlist_rel="assets/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        config_id="raw_all_len8_hd4_cap256_norm500",
        dictionary_id="raw_all",
        wordlist_rel="assets/hamming_raw_1g",
        require_selected=False,
    ),
    dict(
        config_id="strict_selected_len8_hd4_cap256_norm500",
        dictionary_id="strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies/strict/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        config_id="broad_selected_len8_hd4_cap256_norm500",
        dictionary_id="broad_selected",
        wordlist_rel="assets/hamming_dictionary_policies/broad/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        config_id="research_selected_len8_hd4_cap256_norm500",
        dictionary_id="research_selected",
        wordlist_rel="assets/hamming_dictionary_policies/research/hamming_raw_1g",
        require_selected=True,
    ),
)


def main() -> None:
    scan.main()


if __name__ == "__main__":
    main()
