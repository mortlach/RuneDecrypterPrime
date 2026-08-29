from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.problem import DecryptionProblem
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.solvers.sa import SASolver
pytestmark = pytest.mark.tier_a

class _ZeroScorer:

    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)

def test_sa_elitism_rejected():
    ct = np.array([0, 1, 2, 3], dtype=np.uint8)
    wli = [[i, 4] for i in range(4)]
    cfg = CipherConfig(ciphertext=ct, wli_data=wli, key_length=1, name='vigenere', encoding_dir=Direction.LTR)
    cipher = RuneVigenereCipher(cfg)
    problem = DecryptionProblem(cipher=cipher, scorer=_ZeroScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match='sa_elitism'):
        SASolver(problem, opt_cfg={'sa_elitism': True}, rng=rng)
