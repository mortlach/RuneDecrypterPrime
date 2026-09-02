from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rdp.ciphers.substitution_cipher import SubstitutionCipher
from rdp.core.config.cipher import CipherConfig
from rdp.core.problem.runtime import DecryptionProblem
from rdp.core.types import Direction
from rdp.solvers.beam import BeamSolver
pytestmark = pytest.mark.tier_a
ALPHABET_SIZE = 29

class _CountingScorer:

    def __init__(self) -> None:
        self.batch_calls: list[int] = []
        self.batch_raw_calls: list[int] = []

    def batch_score(self, pts, wli=None):
        self.batch_calls.append(len(pts))
        return np.asarray([10.0 + i for i in range(len(pts))], dtype=np.float64)

    def batch_score_with_raw(self, pts, wli=None):
        self.batch_raw_calls.append(len(pts))
        pct = np.asarray([20.0 + i for i in range(len(pts))], dtype=np.float64)
        raw = np.asarray([30.0 + i for i in range(len(pts))], dtype=np.float64)
        return (pct, raw)

    def supports_raw(self):
        return True

def _identity_key() -> np.ndarray:
    return np.arange(ALPHABET_SIZE, dtype=np.uint8)

def _swap_key(a: int, b: int) -> np.ndarray:
    k = _identity_key()
    k[a], k[b] = (k[b], k[a])
    return k

def _make_problem(*, ct: list[int], wli, hard_crib: dict, scorer=None) -> DecryptionProblem:
    cfg = CipherConfig(name='substitution', ciphertext=ct, wli_data=wli, key_length=ALPHABET_SIZE, alphabet_size=ALPHABET_SIZE, encoding_dir=Direction.LTR, device='cpu')
    cipher = SubstitutionCipher(cfg)
    s_cfg = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=False, hard_crib=hard_crib, backend=api.advanced.ScorerBackend.NUMPY)
    return DecryptionProblem(cipher=cipher, scorer=scorer or _CountingScorer(), c_cfg=cfg, s_cfg=s_cfg)

def test_fixed_characters_filter_masks_invalid_candidates_and_skips_scoring():
    scorer = _CountingScorer()
    problem = _make_problem(
        ct=[0, 1, 2, 3],
        wli=[],
        hard_crib={"enabled": True, "fixed_characters": {0: [0]}},
        scorer=scorer,
    )
    keys = np.stack([_identity_key(), _swap_key(0, 1)], axis=0)
    scores = problem.evaluate_keys(keys)
    assert np.isfinite(scores[0])
    assert scores[1] == float('-inf')
    assert scorer.batch_calls == [1]
    assert int(problem.telemetry['crib_reject_total']) >= 1
    assert int(problem.telemetry['crib_reject_fixed_char']) >= 1

def test_fixed_characters_filter_applies_to_pct_and_raw_paths():
    scorer = _CountingScorer()
    problem = _make_problem(
        ct=[0, 1, 2, 3],
        wli=[],
        hard_crib={"enabled": True, "fixed_characters": {0: [0]}},
        scorer=scorer,
    )
    keys = np.stack([_identity_key(), _swap_key(0, 1)], axis=0)
    pct, raw = problem.evaluate_keys_with_raw(keys, require_raw=True)
    assert np.isfinite(pct[0]) and np.isfinite(raw[0])
    assert pct[1] == float('-inf')
    assert raw[1] == float('-inf')
    assert scorer.batch_raw_calls == [1]

def test_word_rules_require_wli_when_enabled():
    with pytest.raises(ValueError, match='require WLI'):
        _make_problem(ct=[0, 1, 2, 3], wli=[], hard_crib={'enabled': True, 'per_word_allowed': {0: [[0, 1]]}})

def test_all_rejected_solution_sets_explicit_flag():
    scorer = _CountingScorer()
    problem = _make_problem(
        ct=[0, 0],
        wli=[],
        hard_crib={"enabled": True, "fixed_characters": {0: [1], 1: [2]}},
        scorer=scorer,
    )
    solver = BeamSolver(
        problem,
        opt_cfg={
            "beam_width": 4,
            "rounds": 1,
            "progress_pct": 0,
            "print_progress": False,
        },
        rng=np.random.default_rng(0),
        verbose=False,
        log_interval=9999,
    )
    sol = solver.solve()
    assert sol.score == float('-inf')
    assert sol.stop_reason == 'all_rejected_by_hard_crib'
    assert bool(sol.extras.get('hard_crib_all_rejected', False)) is True
    assert int(problem.telemetry['crib_all_rejected_batches']) >= 1
