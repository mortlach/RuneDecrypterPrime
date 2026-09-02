from rdp import api
import numpy as np
import pytest
from rdp.core.config.cipher import CipherConfig
from rdp.core.problem.runtime import DecryptionProblem
from rdp.core.types import freeze_parameter_items
from rdp.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rdp.ciphers.substitution_cipher import SubstitutionCipher
from rune_decrypter_prime.solvers.kaeding_periodic_structured import KaedingPeriodicStructuredSolver
pytestmark = pytest.mark.tier_a

class ZeroScorer:

    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)

    def batch_score_with_raw(self, pts, wli=None):
        zeros = np.zeros((len(pts),), dtype=np.float64)
        return (zeros, zeros.copy())

    def score(self, pt, wli=None):
        return 0.0

    def score_with_raw(self, pt, wli=None):
        return (0.0, 0.0)

def _make_periodic_problem(period: int=2, A: int=5):
    key_len = period * A
    cfg = CipherConfig(ciphertext=[0, 1, 2, 3, 4], wli_data=[], key_length=key_len, name='periodic_substitution', period=period, alphabet_size=A, keyops_hints={'period': period, 'A': A})
    cipher = PeriodicSubstitutionCipher(cfg)
    return DecryptionProblem(cipher=cipher, scorer=ZeroScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())

def test_kaeding_emits_progress_fields():
    problem = _make_periodic_problem()
    solver = KaedingPeriodicStructuredSolver(problem, opt_cfg={'steps': 4, 'restarts': 1, 'inner_batch': 4, 'col_every': 0}, rng=np.random.default_rng(0))
    sol = solver.solve()
    tel = getattr(sol, 'meta', {}).get('telemetry', {})
    progress = tel.get('solver_progress', [])
    assert progress, 'Expected solver_progress events'
    assert any(('block' in ev for ev in progress))
    assert any(('restart' in ev for ev in progress))
    assert set(tel['kaeding']['per_phase']) == {'0', '1'}
    freeze_parameter_items(tel, 'telemetry')

def test_kaeding_forwards_progress_callback():
    received = []
    problem = _make_periodic_problem()
    solver = KaedingPeriodicStructuredSolver(
        problem,
        opt_cfg={'steps': 4, 'restarts': 1, 'inner_batch': 4, 'col_every': 0},
        rng=np.random.default_rng(0),
        progress_callback=lambda payload, key: received.append((payload, key)),
    )

    solver.solve()

    assert received
    assert received[-1][0]['pct'] == 100

def test_kaeding_rejects_non_structured_keyops():
    cfg = CipherConfig(ciphertext=[0, 1, 2], wli_data=[], key_length=3, name='substitution', alphabet_size=3)
    cipher = SubstitutionCipher(cfg)
    problem = DecryptionProblem(cipher=cipher, scorer=ZeroScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())
    solver = KaedingPeriodicStructuredSolver(problem, opt_cfg={'steps': 1, 'restarts': 1, 'inner_batch': 2}, rng=np.random.default_rng(0))
    with pytest.raises(ValueError, match='periodic_structured'):
        solver.solve()
