from __future__ import annotations

"""
Report-only Phase-A-v0.14 span-Hamming full length/HD ladder scan.

This uses one length and one HD per template so the output config IDs are clear:
phaseA14_strict_selected__len08_hd3__cap512, etc.

No runtime solver behaviour changes. No CLI arguments.
"""

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    calibrate_span_hamming_full_space_v1 as calibration,
)


RUN_LABEL = "phaseA14_span_hamming_full_ladder_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseA14_span_hamming_full_ladder_v1"
)

DICTIONARY_SPECS = (
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

HD_LADDER_BY_LENGTH = {
    1: (0,),
    2: (0,),
    3: (0, 1),
    4: (0, 1),
    5: (0, 1),
    6: (0, 1, 2),
    7: (0, 1, 2),
    8: (0, 1, 2, 3),
    9: (0, 1, 2, 3),
    10: (0, 1, 2, 3, 4),
    11: (0, 1, 2, 3, 4),
    12: (0, 1, 2, 3, 4, 5),
    13: (0, 1, 2, 3, 4, 5),
    14: (0, 1, 2, 3, 4, 5),
}

SPAN_TEMPLATE_SPECS = tuple(
    dict(template_id=f"len{length:02d}_hd{hd}", len_min=length, len_max=length, max_hd=hd)
    for length in range(1, 15)
    for hd in HD_LADDER_BY_LENGTH[length]
)

# Conservative first full-ladder cap. Increase only after the first run shows
# acceptable timing and cap-pressure behaviour.
TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0
PROGRESS_EVERY_CANDIDATES = 100
TIMING_SAMPLE_TOKEN_LIMIT = 12
CANDIDATE_CAPS = (512,)
INCLUDE_CAP_2048 = False
PYTHON_PARITY_SPOT_CHECK = True
PYTHON_PARITY_TOKEN_LIMIT = 3
PYTHON_PARITY_CONFIG_LIMIT = 6


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
