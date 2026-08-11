"""Crib-drag style integration tests for RunAPI."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import (
    RunAPI,
    SolverSpec,
    KeySpec,
    Direction,
    by_name,
    cipher_instance,
)
from rune_decrypter_prime.utils.runeglish import Runeglish
from tests.tutorials._utils import plaintext_match_rate

pytestmark = pytest.mark.tier_a


def _encode_text(text: str, direction: Direction):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    return np.asarray(pt_idx, dtype=np.uint8), wli


def _derive_repeat_key_from_crib(
    ciphertext: np.ndarray,
    crib_idx: np.ndarray,
    period: int,
    alphabet: int = 29,
):
    """
    Slide the crib across the ciphertext and derive a repeating Vigenère key.
    Returns (key, offset) if every phase slot is consistent.
    """
    L = int(ciphertext.size)
    M = int(crib_idx.size)
    if M == 0 or L < M or period <= 0:
        return None, None

    for start in range(L - M + 1):
        slots: list[int | None] = [None] * period
        ok = True
        for offset in range(M):
            slot = (start + offset) % period
            pt_val = int(crib_idx[offset])
            ct_val = int(ciphertext[start + offset])
            delta = (ct_val - pt_val) % alphabet
            prev = slots[slot]
            if prev is None:
                slots[slot] = delta
            elif prev != delta:
                ok = False
                break
        if ok and all(value is not None for value in slots):
            return np.asarray(slots, dtype=np.uint8), start
    return None, None


def _encrypt_vigenere(text: str, direction: Direction, key: np.ndarray):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    cipher = cipher_instance("vigenere", key_length=key.size, text_transposition=direction.value)
    ct_idx = cipher.encrypt(plaintext=np.asarray(pt_idx, dtype=np.uint8), key=key)
    ct_arr = np.asarray(ct_idx, dtype=np.uint8)
    if ct_arr.ndim == 2:
        ct_arr = ct_arr[0]
    return ct_arr, np.asarray(pt_idx, dtype=np.uint8), wli



def test_runapi_accepts_crib_seeded_keys_for_vigenere():
    """
    Derive a Vigenère key from a plaintext crib and ensure RunAPI converges.
    """
    direction = Direction.LTR
    plaintext = "future crib drag cases keep new presets stable for release"
    true_key = np.array([3, 7, 11, 5, 19], dtype=np.uint8)
    ct_idx, pt_idx, wli = _encrypt_vigenere(plaintext, direction, true_key)

    crib_text = "new presets stable"
    crib_idx = np.asarray(
        Runeglish.encode_english_to_runes(crib_text, direction=direction.value)[0],
        dtype=np.uint8,
    )
    seeded_key, offset = _derive_repeat_key_from_crib(ct_idx, crib_idx, period=true_key.size)
    assert seeded_key is not None and offset is not None, "Failed to derive key from crib drag"

    solver = SolverSpec.beam(
        beam_width=1,
        seed=2025,
        progress_pct=1,
        stop_score=0.5,
        rounds=1,
    )
    sol = RunAPI.run(
        text=ct_idx,
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=true_key.size),
        solver=solver,
        encoding_dir=direction,
        wli_data=wli,
        telemetry_on=False,
        initial_keys=[seeded_key.tolist()],
    )

    match = plaintext_match_rate(sol.plaintext_idx, pt_idx)
    assert match >= 0.99


def test_hill_crib_drag_route_is_not_public_v1():
    with pytest.raises(NotImplementedError, match="not a supported RDP V1"):
        by_name.cipher("hill")
