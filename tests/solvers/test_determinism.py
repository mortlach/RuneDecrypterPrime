from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.config.solver import SolverConfig
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.solver_engine import build_optimizer
from rune_decrypter_prime.core.types import Direction
pytestmark = pytest.mark.tier_a

class _ZeroScorer:

    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)

def _make_problem():
    ct = np.array([0, 1, 2, 3], dtype=np.uint8)
    wli = [[i, 4] for i in range(4)]
    cfg = CipherConfig(ciphertext=ct, wli_data=wli, key_length=1, name='vigenere', encoding_dir=Direction.LTR)
    cipher = RuneVigenereCipher(cfg)
    return DecryptionProblem(cipher=cipher, scorer=_ZeroScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())

def test_determinism():
    problem = _make_problem()
    solver_cfg = SolverConfig(name='beam', params={'beam_width': 1})
    with pytest.raises(TypeError):
        build_optimizer(problem, solver_cfg, rng=None)
