from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import Direction, KEY_DTYPE
pytestmark = pytest.mark.tier_a

class _AssertWliScorer:

    def __init__(self, expected_pt, expected_wli):
        self._expected_pt = np.asarray(expected_pt, dtype=np.uint8)
        self._expected_wli = [list(map(int, pair)) for pair in expected_wli]

    def batch_score(self, pts, wli=None):
        assert wli == self._expected_wli
        assert len(pts) == 1
        pt = np.asarray(pts[0], dtype=np.uint8)
        assert np.array_equal(pt, self._expected_pt)
        return np.zeros((len(pts),), dtype=np.float64)

def _run_permutation_wli_check():
    ct = np.array([1, 2, 3, 4], dtype=np.uint8)
    wli = [[0, 2], [1, 2], [0, 2], [1, 2]]
    perm = [2, 3, 0, 1]
    cfg = CipherConfig(ciphertext=ct, wli_data=wli, key_length=1, name='vigenere', encoding_dir=Direction.LTR, initial_text_permutation_indices=perm)
    cipher = RuneVigenereCipher(cfg)
    scorer = _AssertWliScorer(ct, wli)
    problem = DecryptionProblem(cipher=cipher, scorer=scorer, c_cfg=cfg, s_cfg=api.ScoringConfig())
    key = np.array([0], dtype=KEY_DTYPE)
    _ = problem.evaluate_keys(key)

def test_permutation_wli():
    _run_permutation_wli_check()

def test_wli_alignment_under_text_permutation():
    _run_permutation_wli_check()
