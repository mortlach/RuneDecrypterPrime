from __future__ import annotations

"""
Report-only Phase-A-v0.14 fixed-500 exact-HD long-ladder data run.

This is the broad Phase-B data-taking run to use after the uncapped ladder
canary showed that PhaseA14 strict/normal can run with no cap pruning.

It reuses the existing fixed-500 length/HD fingerprint scanner, but switches to:

- PhaseA14 strict and normal selected dictionaries only;
- lengths 5..14, not a single winning length;
- the v0.3 enabled HD ladder by length;
- cap=100000 as a practical uncapped setting.

No runtime solver behaviour changes. No CLI arguments.
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


RUN_LABEL = "phaseA14_span_hamming_500_exact_hd_long_ladder_full_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseA14_span_hamming_500_exact_hd_long_ladder_full_v1"
)
OUTPUT_DIR = scan.REPO_ROOT / OUTPUT_DIR_REL

EFFECTIVELY_UNCAPPED_CANDIDATE_CAP = 100_000

# Long-word ladder only. This avoids assuming the current len06 result remains
# best, while keeping the long run focused on useful damaged-word evidence.
LENGTHS = (5, 6, 7, 8, 9, 10, 11, 12, 13, 14)
MAX_HD_BY_LENGTH = {
    5: 1,
    6: 2,
    7: 2,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 5,
    13: 5,
    14: 5,
}

SPAN_CONFIG_SPECS = (
    dict(
        config_id="phaseA14_strict_selected_len05_14_exact_hd_ladder_cap100000_norm500",
        dictionary_id="phaseA14_strict_selected",
        wordlist_rel="assets/hamming_dictionary_policies_phaseA_v0_14/strict/hamming_raw_1g",
        require_selected=True,
    ),
    dict(
        config_id="phaseA14_normal_selected_len05_14_exact_hd_ladder_cap100000_norm500",
        dictionary_id="phaseA14_normal_selected",
        wordlist_rel="assets/hamming_dictionary_policies_phaseA_v0_14/normal/hamming_raw_1g",
        require_selected=True,
    ),
)

TOKEN_HASH_LIMIT_FOR_CANARY = 0
PROGRESS_EVERY_SCORES = 100
MAX_CANDIDATES_PER_WINDOW = EFFECTIVELY_UNCAPPED_CANDIDATE_CAP


def _apply_config() -> None:
    scan.RUN_LABEL = RUN_LABEL
    scan.OUTPUT_DIR_REL = OUTPUT_DIR_REL
    scan.OUTPUT_DIR = OUTPUT_DIR
    scan.LENGTHS = LENGTHS
    scan.MAX_HD_BY_LENGTH = MAX_HD_BY_LENGTH
    scan.MAX_CANDIDATES_PER_WINDOW = MAX_CANDIDATES_PER_WINDOW
    scan.SPAN_CONFIG_SPECS = SPAN_CONFIG_SPECS
    scan.TOKEN_HASH_LIMIT_FOR_CANARY = TOKEN_HASH_LIMIT_FOR_CANARY
    scan.PROGRESS_EVERY_SCORES = PROGRESS_EVERY_SCORES


def main() -> None:
    _apply_config()
    scan.main()


if __name__ == "__main__":
    main()
