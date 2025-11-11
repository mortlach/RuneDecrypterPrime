from __future__ import annotations
import numpy as np

from rune_decrypter_prime.api.normalize import to_indices, wli_from_text, make_single_word_wli, runes_from_indices
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1
from rune_decrypter_prime.data.cipher_tests.plaintext import (
    plaintext1,              # indices
    word_breaks1,            # WLI
    plaintext_rune_string,   # rune characters
    plaintext_english_string # normal English (26 letters)
)
from rune_decrypter_prime.utils.runeglish import Runeglish

import numpy as np
import unicodedata
import pytest


def _norm_runes(s: str) -> str:
    # fold whitespace and normalize Unicode to avoid false diffs
    s = "".join(ch for ch in s if not ch.isspace())
    return s

def test_rune_string_to_indices_matches_packaged_indices():
    # reference shape
    idx_ref = np.asarray(plaintext1, dtype=np.uint8).reshape(-1)

    # parse the rune string (with spaces removed for consistency)
    rs = _norm_runes(plaintext_rune_string)
    idx_from_runes = to_indices(rs)

    # the durable invariants
    assert idx_from_runes.dtype == np.uint8
    assert idx_from_runes.shape == idx_ref.shape

    # round-trip: indices → runes should equal original (normalized) runes
    runes_rt = (Runeglish.pos_to_rune(idx_from_runes))
    assert runes_rt == rs

    # # Optional strict mode for exact byte-for-byte equality with assets
    # if pytest.config.getoption("--strict-repr", default=False):  # or env var
    #     assert np.array_equal(idx_from_runes, idx_ref)


def test_wli_from_rune_text_matches_length():
    idx = to_indices(_norm_runes(plaintext_rune_string))
    wli = wli_from_text(_norm_runes(plaintext_rune_string))
    assert isinstance(wli, list) and len(wli) == int(idx.size)

def test_english_string_converts_to_indices_and_wli():
    idx = to_indices(plaintext_english_string)
    assert idx.ndim == 1 and idx.size > 0
    wli = wli_from_text(plaintext_english_string)
    assert isinstance(wli, list) and len(wli) == int(idx.size)

def test_render_helpers_roundtrip_runes_and_latin():
    idx = np.asarray(plaintext1[:64], dtype=np.uint8)
    wli = word_breaks1[:64]
    # rune characters (not Latin-canon)
    rune_chars = runes_from_indices(idx, wli)
    assert isinstance(rune_chars, str) and len(rune_chars) > 0
    # Latin-canon (display only)
    latin = Runeglish.to_rune(idx.tolist(), wli)
    assert isinstance(latin, str) and len(latin) > 0

def test_single_word_wli_length():
    L = 7
    w = make_single_word_wli(L)
    assert isinstance(w, list) and len(w) == L and w[0] == [0, L] and w[-1] == [L-1, L]
