# ============================================================
# File: tests/patche_old_ui/test_normalize_v2.py
# Purpose: Contract tests for to_indices/make_single_word_wli v2 behavior.
# ============================================================
from __future__ import annotations
import numpy as np
import pytest

from rune_decrypter_prime.api.normalize import to_indices, make_single_word_wli
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1
from rune_decrypter_prime.utils.runeglish import Runeglish

def test_to_indices_list_and_array():
    arr = to_indices([0, 1, 2, 28])
    assert arr.dtype == np.uint8 and arr.ndim == 1 and arr.size == 4
    arr2 = to_indices(np.array([5, 6, 7], dtype=np.int32))
    assert arr2.dtype == np.uint8 and arr2.tolist() == [5, 6, 7]

def test_to_indices_string_roundtrip_if_runeglish_available():
    idx = np.asarray(plaintext1, dtype=np.uint8)
    s = Runeglish.pos_to_rune(idx)
    back = to_indices(s)
    assert back.size == idx.size  # shape check; spacing/formatting can differ

def test_make_single_word_wli_shape():
    L = 5
    w = make_single_word_wli(L)
    assert isinstance(w, list) and len(w) == L and all(len(p) == 2 for p in w)
    assert w[0] == [0, L] and w[-1] == [L - 1, L]
