from __future__ import annotations
from rdp import api
import rdp.api.normalize
import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig
pytestmark = pytest.mark.tier_a

def _split_wli_words(wli):
    words = []
    cur = []
    for pos, length in wli:
        if pos == 0 and cur:
            words.append(cur)
            cur = []
        cur.append((int(pos), int(length)))
    if cur:
        words.append(cur)
    return words

def test_wli_invariants():
    ct, wli = rdp.api.normalize.normalize_ciphertext('AB CD')
    rdp.api.normalize._assert_core_ready(ct, wli)
    assert len(ct) == len(wli)
    words = _split_wli_words(wli)
    assert len(words) == 2
    for word in words:
        word_len = word[0][1]
        assert all((pair[1] == word_len for pair in word))
        assert [pair[0] for pair in word] == list(range(word_len))

def test_wli_string_path_contract_poslen():
    _ct, wli = rdp.api.normalize.normalize_ciphertext('AB CD')
    words = _split_wli_words(wli)
    assert words[0][0][0] == 0
    assert words[1][0][0] == 0

def test_wli_config_contract_is_consistent_with_hamming():
    ct = [0, 1, 2, 3, 4]
    wli_bad = [[0, 2], [1, 2], [2, 5], [3, 5], [4, 5]]
    with pytest.raises(ValueError):
        CipherConfig(ciphertext=ct, wli_data=wli_bad, key_length=1, name='vigenere')

def test_wli_uint8_overflow_guard():
    L = 300
    ct = np.zeros(L, dtype=np.uint8)
    wli = [[i, L] for i in range(L)]
    with pytest.raises(ValueError):
        rdp.api.normalize._assert_core_ready(ct, wli)
