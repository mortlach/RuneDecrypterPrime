from __future__ import annotations
from rdp import api
import hashlib
from types import SimpleNamespace
import numpy as np
import pytest
from rdp.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rdp.core.config.cipher import CipherConfig
from rdp.core.problem.runtime import DecryptionProblem
from rdp.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, Stat
from rdp.keyops.vector import VectorKeyOps
from rdp.solvers.hybrid import HybridSolver
from rdp.solvers.kaeding_periodic_structured import KaedingPeriodicStructuredSolver
from rdp.solvers.sa import SASolver
pytestmark = pytest.mark.tier_a

class _TraceProblem:

    def __init__(self, *, key_length: int=2, modulus: int=7) -> None:
        self.keyops = VectorKeyOps(key_length, mod=modulus)
        self.c_cfg = SimpleNamespace(device=Device.CPU, encoding_dir=Direction.LTR, wli_data=None)
        self.scorer = SimpleNamespace(objective=ObjectiveSpec(ObjectiveFamily.PCT, Stat.LOGP, 1))
        self.telemetry = {}
        self.target = np.arange(key_length, dtype=np.int16) + 3
        self.evaluation_count = 0
        self._trace = hashlib.sha256()

    def evaluate_keys(self, keys):
        batch = np.asarray(keys, dtype=np.int16).reshape(-1, self.keyops.K)
        self.evaluation_count += int(batch.shape[0])
        self._trace.update(np.asarray(batch, dtype='<i2').tobytes())
        return -np.sum((batch - self.target) ** 2, axis=1, dtype=np.float64)

    def resolve_plaintext(self, key):
        return np.asarray(key, dtype=np.uint8).reshape(-1)

    @property
    def trace_hash(self) -> str:
        return self._trace.hexdigest()

def _solution_contract(solution, problem):
    return {'key': np.asarray(solution.key, dtype=np.int16).tolist(), 'plaintext': np.asarray(solution.plaintext, dtype=np.uint8).tolist(), 'score': float(solution.score), 'stop_reason': solution.stop_reason, 'evaluations': int(problem.evaluation_count), 'trace_hash': problem.trace_hash}

def _run_sa(seed: int):
    problem = _TraceProblem()
    solution = SASolver(problem, opt_cfg={'iters': 18, 'T0': 1.2, 'Tmin': 0.05, 'cool': 0.85}, rng=np.random.default_rng(seed), seed_keys=[[0, 0]], verbose=False, log_interval=0).solve()
    return _solution_contract(solution, problem)

def _run_hybrid(seed: int):
    problem = _TraceProblem()
    solution = HybridSolver(problem, opt_cfg={'use_beam': True, 'beam_width': 3, 'rounds': 1, 'expand.parent_mode': 'all', 'ga': {'pop_size': 5, 'generations': 3, 'mut_prob': 0.4}, 'sa': {'iters': 7, 'T0': 0.8, 'Tmin': 0.05, 'cool': 0.8}}, rng=np.random.default_rng(seed), seed_keys=[[0, 0]], verbose=False, log_interval=0).solve()
    contract = _solution_contract(solution, problem)
    contract['from_phase'] = solution.meta['from_phase']
    return contract

def test_sa_seeded_whole_route_replays_contractual_result_and_work():
    first = _run_sa(5105)
    second = _run_sa(5105)
    assert first == second
    assert first['stop_reason'] == 'max_iterations_reached'
    assert first['evaluations'] > 1
    assert _run_sa(5106)['trace_hash'] != first['trace_hash']

def test_hybrid_seeded_whole_route_replays_contractual_result_and_work():
    first = _run_hybrid(5205)
    second = _run_hybrid(5205)
    assert first == second
    assert first['stop_reason'] == 'configured_work_limit_reached'
    assert first['evaluations'] > 1
    assert _run_hybrid(5206)['trace_hash'] != first['trace_hash']

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

class _KaedingReplayProblem:

    def __init__(self, *, period: int=2, alphabet_size: int=5) -> None:
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
        self.evaluation_count = 0
        self._trace = hashlib.sha256()

    def evaluate_keys_with_raw(self, keys, *, batch_hint: bool=True, require_raw: bool=False):
        batch = np.asarray(keys, dtype=np.int16)
        if batch.ndim == 1:
            batch = batch[None, :]
        self.evaluation_count += int(batch.shape[0])
        self._trace.update(np.asarray(batch, dtype='<i2').tobytes())
        weights = np.arange(1, batch.shape[1] + 1, dtype=np.float64)
        raw = np.sum(batch * weights, axis=1, dtype=np.float64)
        return (raw.copy(), raw)

    def evaluate_keys(self, keys, *, batch_hint: bool=True):
        pct, _raw = self.evaluate_keys_with_raw(keys, batch_hint=batch_hint)
        return pct

    def resolve_plaintext(self, key):
        return self.cipher.decrypt(ciphertext=self.ciphertext, key=key)

    @property
    def trace_hash(self) -> str:
        return self._trace.hexdigest()
_KAEDING_SEEDS = [[0, 1, 2, 3, 4, 0, 1, 2, 3, 4], [4, 1, 2, 3, 0, 0, 1, 2, 3, 4]]

def _run_kaeding(seed: int):
    problem = _KaedingReplayProblem()
    solution = KaedingPeriodicStructuredSolver(problem, opt_cfg={'steps': 4, 'restarts': 3, 'inner_batch': 3, 'block_schedule': 'round_robin', 'slip_every': 0, 'col_every': 0, 'stall_rounds': 0, 'use_raw_score': True, 'seed_selection_metric': 'raw', 'seed_restarts': 2, 'top_k': 2}, rng=np.random.default_rng(seed), seed_keys=_KAEDING_SEEDS, verbose=False, log_interval=0).solve()
    contract = _solution_contract(solution, problem)
    telemetry = solution.meta['telemetry']['kaeding']
    contract.update({'restart_start_hashes': telemetry['restart_start_hashes'], 'seed_selected_hash': telemetry['seed_selected_hash'], 'seed_restarts_used': telemetry['seed_restarts_used'], 'top_keys': telemetry['top_keys']})
    return contract

def test_kaeding_seeded_restart_route_replays_result_work_and_contract_hashes():
    first = _run_kaeding(5305)
    second = _run_kaeding(5305)
    assert first == second
    assert first['stop_reason'] == 'max_steps_reached'
    assert first['evaluations'] > 1
    assert first['seed_restarts_used'] == 2
    assert len(first['restart_start_hashes']) == 3
    different = _run_kaeding(5306)
    assert different['restart_start_hashes'][:2] == first['restart_start_hashes'][:2]
    assert different['restart_start_hashes'][2] != first['restart_start_hashes'][2]
    assert different['trace_hash'] != first['trace_hash']
