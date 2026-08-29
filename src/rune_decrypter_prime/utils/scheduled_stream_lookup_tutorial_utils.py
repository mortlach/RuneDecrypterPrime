from __future__ import annotations

from typing import Sequence

import numpy as np

from rdp import api
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import (
    oracle_stop_score,
    print_stop_summary,
)


ALPHABET_SIZE = 29
APP_VERSION = "tutorial-scheduled-stream-lookup-1.0"
TUTORIAL_SEED = 12345


def tutorial_plaintext(max_symbols: int = 520) -> str:
    return plaintext_english_string[:max_symbols]


def key_period13() -> list[int]:
    return [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9]


def key_period31() -> list[int]:
    # Gauge choice for additive P13+P31 examples: first P31 entry is zero.
    return [0] + [((7 * i + 11) % ALPHABET_SIZE) for i in range(1, 31)]


def sample_sequence(length: int = 64) -> list[int]:
    return [((5 * i + 7) % ALPHABET_SIZE) for i in range(length)]


def concat_keys(*parts: Sequence[int]) -> list[int]:
    out: list[int] = []
    for part in parts:
        out.extend(int(v) for v in part)
    return out


def mask_from_segments(
    length: int, segments: Sequence[tuple[str, int, int | None]]
) -> list[int]:
    """Readable A/B/AB segments -> integer mask."""
    labels = {"NONE": 0, "OFF": 0, "A": 1, "B": 2, "AB": 3, "A+B": 3, "B+A": 3}
    mask: list[int | None] = [None] * int(length)
    for label, start, end in segments:
        key = str(label).strip().upper().replace(" ", "")
        if key not in labels:
            raise ValueError("segment label must be A, B, AB, or NONE")
        stop = length if end is None else int(end)
        for i in range(int(start), stop):
            if not 0 <= i < length:
                raise ValueError(f"segment index out of range: {i}")
            if mask[i] is not None:
                raise ValueError(f"overlapping segment at index {i}")
            mask[i] = labels[key]
    if any(v is None for v in mask):
        raise ValueError("mask does not cover every plaintext position")
    return [int(v) for v in mask]


def encode_plaintext(
    direction: api.TextDirection = api.TextDirection.RIGHT_TO_LEFT,
):
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        tutorial_plaintext(),
        direction=direction.value,
    )
    return [int(v) for v in pt_idx], wli, pt_runes


def default_scorer_params(direction: api.TextDirection) -> api.ScoringConfig:
    return api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )


def make_seeded_smoke_solver(
    pt_idx: Sequence[int],
    wli,
    scorer_params: api.ScoringConfig,
    direction: api.TextDirection,
    *,
    label: str,
) -> api.SolverSpec:
    """Seeded pipeline-smoke solver. This is not ciphertext-only solving."""
    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.50,
        fallback=0.54,
    )
    print_stop_summary(label, stop)
    return api.SolverSpec.beam_search(
        width=24,
        rounds=250,
        target_score=stop.stop_score,
        plateau_rounds=6,
        plateau_minimum_delta=1e-4,
        maximum_children_per_parent=16,
        seed=TUTORIAL_SEED,
    )


def make_real_solve_solver(
    *,
    stop_score: float = 0.56,
    beam_width: int = 72,
    plateau_rounds: int = 12,
    max_children_per_parent: int = 29,
    seed: int = 2026,
) -> api.SolverSpec:
    """Real key-recovery tutorial solver.

    Does not receive the true key as an initial key. The stop score is a fixed
    tutorial threshold for the short Alice sample used here.
    """
    print(f"[real solve] fixed stop_score={stop_score:.6f}; true key is not supplied")
    return api.SolverSpec.beam_search(
        width=int(beam_width),
        rounds=500,
        target_score=float(stop_score),
        plateau_rounds=int(plateau_rounds),
        plateau_minimum_delta=1e-4,
        maximum_children_per_parent=int(max_children_per_parent),
        seed=int(seed),
    )


def build_ciphertext(
    *,
    cipher_spec: api.CipherSpec,
    key_spec: api.KeySpec,
    key_values: Sequence[int],
    direction: api.TextDirection,
):
    pt_idx, wli, pt_runes = encode_plaintext(direction)
    key = tuple(int(value) for value in key_values)
    expected_key_len = int(key_spec.parameters.get("length", len(key)))
    if len(key) != expected_key_len:
        raise AssertionError(f"expected key length {expected_key_len}, got {len(key)}")

    ciphertext = api.encrypt(tuple(pt_idx), cipher=cipher_spec, key=key)
    ct_idx_list = list(ciphertext)
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)
    display_direction = "rtl" if direction is api.TextDirection.RIGHT_TO_LEFT else "ltr"
    print_tutorial_debug_preview(
        label="plaintext", idx=pt_idx, wli=wli, direction=display_direction
    )
    print_tutorial_debug_preview(
        label="ciphertext", idx=ct_idx_list, wli=wli, direction=display_direction
    )
    return cipher_spec, key_spec, pt_idx, wli, pt_runes, ct_idx_list, ct_runes, key


def _as_int_list(x) -> list[int] | None:
    if isinstance(x, (list, tuple, np.ndarray)):
        return [int(v) for v in x]
    return None


def two_period_additive_equivalent(
    found: Sequence[int] | None,
    expected: Sequence[int],
    *,
    period_a: int,
    period_b: int,
    alphabet_size: int = ALPHABET_SIZE,
) -> bool:
    """Check additive overlay gauge equivalence.

    For pure additive overlay, A+c and B-c gives the same combined stream.
    This checks equivalence rather than requiring the exact arbitrary split.
    """
    if found is None:
        return False
    found_l = [int(v) % alphabet_size for v in found]
    expected_l = [int(v) % alphabet_size for v in expected]
    if len(found_l) != period_a + period_b or len(expected_l) != period_a + period_b:
        return False

    fa, fb = found_l[:period_a], found_l[period_a:]
    ea, eb = expected_l[:period_a], expected_l[period_a:]
    shift = (fa[0] - ea[0]) % alphabet_size
    if any(fa[i] != (ea[i] + shift) % alphabet_size for i in range(period_a)):
        return False
    if any(fb[i] != (eb[i] - shift) % alphabet_size for i in range(period_b)):
        return False
    return True
