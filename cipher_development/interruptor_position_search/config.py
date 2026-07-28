from __future__ import annotations

from dataclasses import dataclass

ALPHABET_SIZE = 29
DIRECTION = "ltr"
KEY_VALUES = (7, 0, 13, 2, 5, 21, 8)
KEY_LENGTH = len(KEY_VALUES)

INTERRUPTOR_LATIN_SYMBOL = "F"
TRUE_INTERRUPT_COUNT = 4
MIN_INTERRUPT_COUNT = 0
MAX_INTERRUPT_COUNT = 6

CONTROL_SEED = 8080
CANARY_SEED = 8081
SCIENCE_BLOCK_IDS = (81, 82, 83)
SCIENCE_SEEDS = (880081, 880082, 880083)

CONTROL_BEAM_WIDTH = 64
CANARY_BEAM_WIDTH = 64
SCIENCE_BEAM_WIDTH = 256
EXPAND_MODE = "sweep"
CONTROL_PLATEAU_ROUNDS = 8
SCIENCE_PLATEAU_ROUNDS = 20
PLATEAU_MIN_DELTA = 1e-4

GLOBAL_TARGET_S = 12 * 60 * 60
TERMINAL_PACKAGING_RESERVE_S = 30 * 60
RUNTIME_SAFETY_FACTOR = 1.20

SCORER_PARAMS = {
    "objective": "pct.logp.win10",
    "include_char": True,
    "use_word_breaks": True,
    "char_weights": {2: 0.3},
    "wli_weights": {2: 0.7},
    "encoding_dir": DIRECTION,
}


@dataclass(frozen=True, slots=True)
class SciencePlan:
    block_ids: tuple[int, ...] = SCIENCE_BLOCK_IDS
    seeds: tuple[int, ...] = SCIENCE_SEEDS
    global_target_s: float = float(GLOBAL_TARGET_S)
    reserve_s: float = float(TERMINAL_PACKAGING_RESERVE_S)
    safety_factor: float = float(RUNTIME_SAFETY_FACTOR)
