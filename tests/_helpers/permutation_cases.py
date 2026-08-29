"""Reusable fixtures for permutation-based cipher tests."""

from __future__ import annotations
from rdp import api
import numpy as np
from rune_decrypter_prime.utils.runeglish import Runeglish


def encode_text(text: str, direction: api.TextDirection):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    return (np.asarray(pt_idx, dtype=np.uint8), wli)


def columnar_roundtrip_case(
    text: str = "columnar permutation solvers must stay bijective",
):
    direction = api.TextDirection.LEFT_TO_RIGHT
    pt_idx, wli = encode_text(text, direction)
    perm = np.array([2, 0, 3, 1], dtype=np.uint8)
    columnar = api.CipherSpec.columnar(columns=len(perm), alphabet_size=29)
    ct_idx = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=columnar,
        key=tuple(int(value) for value in perm),
    )
    ct_arr = np.asarray(ct_idx, dtype=np.uint8)
    if ct_arr.ndim == 2:
        ct_arr = ct_arr[0]
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)
    return (ct_arr, pt_arr, wli, np.asarray(perm, dtype=np.uint8), direction)
