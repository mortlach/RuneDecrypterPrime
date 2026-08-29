from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.solvers.beam import BeamSolver
from rune_decrypter_prime.solvers.ga import GASolver
from rune_decrypter_prime.solvers.hybrid import HybridSolver
from rune_decrypter_prime.solvers.kaeding_periodic_structured import KaedingPeriodicStructuredSolver
from rune_decrypter_prime.solvers.sa import SASolver
pytestmark = pytest.mark.tier_a

class _ZeroScorer:

    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)

    def batch_score_with_raw(self, pts, wli=None):
        zeros = np.zeros((len(pts),), dtype=np.float64)
        return (zeros, zeros.copy())

    def score(self, pt, wli=None):
        return 0.0

    def score_with_raw(self, pt, wli=None):
        return (0.0, 0.0)

def _problem() -> DecryptionProblem:
    ct = np.array([0, 1, 2, 3], dtype=np.uint8)
    wli = [[i, 4] for i in range(4)]
    cfg = CipherConfig(ciphertext=ct, wli_data=wli, key_length=2, name='vigenere', encoding_dir=Direction.LTR)
    return DecryptionProblem(cipher=RuneVigenereCipher(cfg), scorer=_ZeroScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())

def _kaeding_problem() -> DecryptionProblem:
    period, alphabet_size = (2, 5)
    cfg = CipherConfig(ciphertext=[0, 1, 2, 3, 4], wli_data=[], key_length=period * alphabet_size, name='periodic_substitution', period=period, alphabet_size=alphabet_size, keyops_hints={'period': period, 'A': alphabet_size})
    return DecryptionProblem(cipher=PeriodicSubstitutionCipher(cfg), scorer=_ZeroScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())

def test_normal_solver_completion_has_producer_owned_reason() -> None:
    cases = ((BeamSolver, {'beam_width': 2, 'rounds': 1, 'plateau_rounds': 0, 'progress_pct': 0}, 'max_rounds_reached'), (GASolver, {'pop_size': 4, 'generations': 1, 'plateau_rounds': 0, 'progress_pct': 0}, 'max_generations_reached'), (SASolver, {'iters': 1, 'plateau_rounds': 0, 'progress_pct': 0}, 'max_iterations_reached'), (HybridSolver, {'use_beam': False, 'ga.pop_size': 4, 'ga.generations': 1, 'sa.iters': 1, 'plateau_rounds': 0, 'progress_pct': 0}, 'configured_work_limit_reached'))
    for index, (solver_cls, params, expected_reason) in enumerate(cases):
        solver = solver_cls(_problem(), opt_cfg=params, rng=np.random.default_rng(index + 1), verbose=False, log_interval=9999)
        solution = solver.solve()
        assert solution.stop_reason == expected_reason

def test_beam_restarts_report_score_selected_restart_metadata() -> None:
    solver = BeamSolver(_problem(), opt_cfg={'beam_width': 2, 'rounds': 1, 'restarts': 3, 'plateau_rounds': 0, 'progress_pct': 0}, rng=np.random.default_rng(7), verbose=False, log_interval=9999)
    solution = solver.solve()
    beam = solution.meta['beam']
    assert solution.stop_reason == 'max_rounds_reached'
    assert beam['restarts'] == 3
    assert beam['selected_restart'] == 0
    assert beam['restart_scores'] == [0.0, 0.0, 0.0]

def test_kaeding_normal_completion_has_producer_owned_reason() -> None:
    solver = KaedingPeriodicStructuredSolver(_kaeding_problem(), opt_cfg={'steps': 1, 'restarts': 1, 'inner_batch': 2, 'col_every': 0, 'plateau_rounds': 0, 'progress_pct': 0}, rng=np.random.default_rng(5), verbose=False, log_interval=9999)
    solution = solver.solve()
    assert solution.stop_reason == 'max_steps_reached'
