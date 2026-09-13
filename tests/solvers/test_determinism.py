from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rdp.core.config.cipher import CipherConfig
from rdp.ciphers.vigenere_cipher import RuneVigenereCipher
from rdp.core.problem.runtime import DecryptionProblem
from rdp.solvers.beam import BeamSolver
from rdp.solvers.ga import GASolver
from rdp.core.types import Direction
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
    with pytest.raises(TypeError):
        BeamSolver(problem, opt_cfg={'beam_width': 1}, rng=None)


def test_beam_repeats_with_same_seed_when_scores_tie():
    def run_once():
        return BeamSolver(
            _make_problem(),
            opt_cfg={"beam_width": 4, "rounds": 4},
            rng=np.random.default_rng(123),
            verbose=False,
            log_interval=0,
        ).solve()

    first = run_once()
    second = run_once()

    np.testing.assert_array_equal(first.key, second.key)
    assert first.score == second.score


def test_ga_repeats_with_same_seed_when_scores_tie():
    def run_once():
        return GASolver(
            _make_problem(),
            opt_cfg={"pop_size": 8, "generations": 4},
            rng=np.random.default_rng(456),
            verbose=False,
            log_interval=0,
        ).solve()

    first = run_once()
    second = run_once()

    np.testing.assert_array_equal(first.key, second.key)
    assert first.score == second.score
