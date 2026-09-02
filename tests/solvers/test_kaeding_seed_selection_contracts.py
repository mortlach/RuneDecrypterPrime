from __future__ import annotations
from rdp import api
import hashlib
import numpy as np
import pytest
from rdp.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rdp.core.config.cipher import CipherConfig
from rdp.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.solvers.kaeding_periodic_structured import KaedingPeriodicStructuredSolver
pytestmark = pytest.mark.tier_a

class _NoopScorer:

    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)

    def batch_score_with_raw(self, pts, wli=None):
        z = np.zeros((len(pts),), dtype=np.float64)
        return (z, z.copy())

    def score(self, pt, wli=None):
        return 0.0

    def score_with_raw(self, pt, wli=None):
        return (0.0, 0.0)

class _SeedMetricProblem:
    """
    Minimal problem facade for Kaeding seed-selection contracts.

    raw score  -> key[0]  (higher is better)
    pct score  -> -key[0] (higher is better)
    """

    def __init__(self, *, period: int=2, alphabet_size: int=5):
        key_len = int(period * alphabet_size)
        cfg = CipherConfig(ciphertext=[0, 1, 2, 3, 4], wli_data=[], key_length=key_len, name='periodic_substitution', period=period, alphabet_size=alphabet_size, keyops_hints={'period': period, 'A': alphabet_size})
        base = DecryptionProblem(cipher=PeriodicSubstitutionCipher(cfg), scorer=_NoopScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig())
        self.keyops = base.keyops
        self.cipher = base.cipher
        self.ciphertext = base.ciphertext
        self.wli_data = None
        self.c_cfg = base.c_cfg
        self.scorer = _NoopScorer()
        self.telemetry = {}

    def evaluate_keys_with_raw(self, keys, *, batch_hint: bool=True, require_raw: bool=False):
        arr = np.asarray(keys, dtype=np.int64)
        if arr.ndim == 1:
            arr = arr[None, :]
        raw = arr[:, 0].astype(np.float64)
        pct = -raw
        return (pct, raw)

    def evaluate_keys(self, keys, *, batch_hint: bool=True):
        pct, _raw = self.evaluate_keys_with_raw(keys, batch_hint=batch_hint)
        return pct

    def resolve_plaintext(self, key):
        return self.cipher.decrypt(ciphertext=self.ciphertext, key=key)

def _key_hash16(key_like) -> str:
    arr = np.asarray(key_like, dtype=np.int16).reshape(-1)
    return hashlib.sha1(arr.tobytes()).hexdigest()[:16]

def _run_solver(problem, *, seed_keys, metric: str, restarts: int=1, seed_restarts: int=1):
    solver = KaedingPeriodicStructuredSolver(problem, opt_cfg={'steps': 1, 'restarts': int(restarts), 'inner_batch': 1, 'col_every': 0, 'use_raw_score': True, 'seed_selection_metric': metric, 'seed_restarts': int(seed_restarts), 'top_k': 0}, rng=np.random.default_rng(20260214), seed_keys=seed_keys)
    sol = solver.solve()
    tel = sol.meta.get('telemetry', {}).get('kaeding', {})
    return tel

def test_kaeding_seed_selection_metric_switches_seed_pick_when_raw_pct_disagree():
    problem = _SeedMetricProblem()
    seed_hi_raw = np.asarray([4, 1, 2, 3, 0, 0, 1, 2, 3, 4], dtype=np.int16)
    seed_hi_pct = np.asarray([0, 1, 2, 3, 4, 0, 1, 2, 3, 4], dtype=np.int16)
    seeds = [seed_hi_raw, seed_hi_pct]
    tel_raw = _run_solver(problem, seed_keys=seeds, metric='raw', restarts=1, seed_restarts=1)
    tel_pct = _run_solver(problem, seed_keys=seeds, metric='pct', restarts=1, seed_restarts=1)
    assert tel_raw.get('seed_selection_metric') == 'raw'
    assert tel_pct.get('seed_selection_metric') == 'pct'
    assert tel_raw.get('seed_selected_hash') == _key_hash16(seed_hi_raw)
    assert tel_pct.get('seed_selected_hash') == _key_hash16(seed_hi_pct)
    assert tel_raw.get('seed_selected_hash') != tel_pct.get('seed_selected_hash')

def test_kaeding_seed_restarts_uses_ordered_seed_schedule_before_random():
    problem = _SeedMetricProblem()
    seed_raw_4 = np.asarray([4, 1, 2, 3, 0, 0, 1, 2, 3, 4], dtype=np.int16)
    seed_raw_3 = np.asarray([3, 1, 2, 4, 0, 0, 1, 2, 3, 4], dtype=np.int16)
    seed_raw_0 = np.asarray([0, 1, 2, 3, 4, 0, 1, 2, 3, 4], dtype=np.int16)
    seeds = [seed_raw_0, seed_raw_3, seed_raw_4]
    tel = _run_solver(problem, seed_keys=seeds, metric='raw', restarts=3, seed_restarts=2)
    hashes = list(tel.get('restart_start_hashes', []))
    assert tel.get('seed_restarts_used') == 2
    assert tel.get('seed_restarts_config') == 2
    assert len(hashes) == 3
    assert hashes[0] == _key_hash16(seed_raw_4)
    assert hashes[1] == _key_hash16(seed_raw_3)

def test_kaeding_seed_selection_metric_rejects_unknown_value():
    problem = _SeedMetricProblem()
    seed = np.asarray([0, 1, 2, 3, 4, 0, 1, 2, 3, 4], dtype=np.int16)
    with pytest.raises(ValueError, match='seed_selection_metric'):
        _run_solver(problem, seed_keys=[seed], metric='bogus', restarts=1, seed_restarts=1)
