from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig, InterruptorConfig, ScoringConfig
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import Direction, KEY_DTYPE
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
pytestmark = pytest.mark.tier_a

class ZeroScorer:

    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)

def test_interruptors_exact_are_reinserted():
    ct = np.array([5, 6, 7], dtype=np.uint8)
    cfg = CipherConfig(ciphertext=ct, wli_data=[], key_length=1, device='cpu', encoding_dir=Direction.LTR, name='vigenere', interruptors_cfg=api.InterruptorConfig.exact([1]))
    cipher = RuneVigenereCipher(cfg)
    problem = DecryptionProblem(cipher=cipher, scorer=ZeroScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())
    key = np.array([1], dtype=KEY_DTYPE)
    pt = problem.resolve_plaintext(key)
    assert pt is not None
    assert pt.tolist() == [4, 6, 6]

def test_interruptor_symbols_fixed_from_ciphertext():
    ct = np.array([7, 1, 22, 5], dtype=np.uint8)
    interrupt_idx = [1, 3]
    cfg = CipherConfig(ciphertext=ct, wli_data=[], key_length=1, device='cpu', encoding_dir=Direction.LTR, name='vigenere', interruptors_cfg=api.InterruptorConfig.exact(interrupt_idx))
    cipher = RuneVigenereCipher(cfg)
    problem = DecryptionProblem(cipher=cipher, scorer=ZeroScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())
    key = np.array([3], dtype=KEY_DTYPE)
    pt = problem.resolve_plaintext(key)
    assert pt is not None
    assert int(pt[1]) == int(ct[1])
    assert int(pt[3]) == int(ct[3])
    assert int(pt[0]) != int(ct[0])
