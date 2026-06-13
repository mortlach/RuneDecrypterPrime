"""Reusable fixtures for permutation-based cipher tests."""
from __future__ import annotations

import numpy as np

from rune_decrypter_prime.api import Direction, by_name, cipher_instance
from rune_decrypter_prime.utils.runeglish import Runeglish


def encode_text(text: str, direction: Direction):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    return np.asarray(pt_idx, dtype=np.uint8), wli


def columnar_roundtrip_case(text: str = "columnar permutation solvers must stay bijective"):
    direction = Direction.LTR
    pt_idx, wli = encode_text(text, direction)
    perm = np.array([2, 0, 3, 1], dtype=np.uint8)
    columnar = cipher_instance(by_name.cipher("columnar", key_len=len(perm)))
    ct_idx = columnar.encrypt(plaintext=np.asarray(pt_idx, dtype=np.uint8), key=perm)
    ct_arr = np.asarray(ct_idx, dtype=np.uint8)
    if ct_arr.ndim == 2:
        ct_arr = ct_arr[0]
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)
    return (
        ct_arr,
        pt_arr,
        wli,
        np.asarray(perm, dtype=np.uint8),
        direction,
    )
