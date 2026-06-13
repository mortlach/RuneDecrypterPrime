from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rune_decrypter_prime.ciphers.columnar_transposition_cipher import ColumnarTranspositionCipher
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.solvers.beam import BeamSolver


pytestmark = pytest.mark.tier_a


class _ZeroScorer:
    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)


def _make_problem():
    ct = np.array([0, 1, 2, 3], dtype=np.uint8)
    wli = [[i, 4] for i in range(4)]
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=2,
        name="vigenere",
        encoding_dir=Direction.LTR,
    )
    cipher = RuneVigenereCipher(cfg)
    return DecryptionProblem(cipher=cipher, scorer=_ZeroScorer(), c_cfg=cfg, s_cfg=ScoringConfig())


def _make_perm_problem():
    ct = np.array([0, 1, 2, 3, 4, 5], dtype=np.uint8)
    wli = [[i, 6] for i in range(6)]
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=3,
        name="columnar",
        encoding_dir=Direction.LTR,
    )
    cipher = ColumnarTranspositionCipher(cfg)
    return DecryptionProblem(cipher=cipher, scorer=_ZeroScorer(), c_cfg=cfg, s_cfg=ScoringConfig())


def test_seed_validation():
    problem = _make_problem()
    rng = np.random.default_rng(0)
    bad_seed = [np.array([9, 9, 9], dtype=np.uint8)]

    with pytest.raises(ValueError):
        BeamSolver(problem, opt_cfg={"beam_width": 1}, rng=rng, seed_keys=bad_seed)


def test_seed_validation_rejects_invalid_permutation_seed():
    problem = _make_perm_problem()
    rng = np.random.default_rng(0)
    bad_seed = [np.array([0, 0, 1], dtype=np.uint8)]

    with pytest.raises(ValueError):
        BeamSolver(problem, opt_cfg={"beam_width": 1}, rng=rng, seed_keys=bad_seed)
