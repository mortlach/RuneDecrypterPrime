from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.substitution_cipher import SubstitutionCipher
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import Direction

pytestmark = pytest.mark.tier_a
ALPHABET_SIZE = 29


def _identity_key() -> np.ndarray:
    return np.arange(ALPHABET_SIZE, dtype=np.uint8)


def _swap_key(a: int, b: int) -> np.ndarray:
    k = _identity_key()
    k[a], k[b] = (k[b], k[a])
    return k


def _make_problem(scorer) -> DecryptionProblem:
    cfg = CipherConfig(
        name="substitution",
        ciphertext=[0, 1, 2, 3],
        wli_data=[],
        key_length=ALPHABET_SIZE,
        alphabet_size=ALPHABET_SIZE,
        encoding_dir=Direction.LTR,
        device="cpu",
    )
    s_cfg = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        backend=api.advanced.ScorerBackend.NUMPY,
    )
    return DecryptionProblem(
        cipher=SubstitutionCipher(cfg), scorer=scorer, c_cfg=cfg, s_cfg=s_cfg
    )


class _BatchOkScorer:
    def batch_score(self, pts, wli=None):
        return np.asarray([100.0 + i for i in range(len(pts))], dtype=np.float64)

    def score(self, pt, wli=None):
        return float(np.mean(np.asarray(pt, dtype=np.float64)))


class _BatchFailScorer:
    def batch_score(self, pts, wli=None):
        raise RuntimeError("synthetic batch failure")

    def score(self, pt, wli=None):
        arr = np.asarray(pt, dtype=np.float64)
        return float(np.mean(arr))


class _BatchRawFailScorer:
    def batch_score_with_raw(self, pts, wli=None):
        raise RuntimeError("synthetic raw batch failure")

    def score_with_raw(self, pt, wli=None):
        arr = np.asarray(pt, dtype=np.float64)
        pct = float(np.mean(arr))
        raw = float(np.sum(arr))
        return (pct, raw)

    def supports_raw(self):
        return True


def test_runtime_counts_batch_calls_without_fallback():
    problem = _make_problem(_BatchOkScorer())
    keys = np.stack([_identity_key(), _swap_key(0, 1)], axis=0)
    scores = problem.evaluate_keys(keys)
    np.testing.assert_allclose(scores, np.asarray([100.0, 101.0], dtype=np.float64))
    assert int(problem.telemetry["score_batch_calls"]) == 1
    assert int(problem.telemetry["score_batch_fallback_scalar"]) == 0
    assert int(problem.telemetry["score_batch_with_raw_calls"]) == 0
    assert int(problem.telemetry["score_batch_with_raw_fallback_scalar"]) == 0


def test_runtime_counts_scalar_fallback_when_batch_score_raises():
    problem = _make_problem(_BatchFailScorer())
    keys = np.stack([_identity_key(), _swap_key(0, 1)], axis=0)
    scores = problem.evaluate_keys(keys)
    assert np.isfinite(scores).all()
    assert int(problem.telemetry["score_batch_calls"]) == 1
    assert int(problem.telemetry["score_batch_fallback_scalar"]) == 1


def test_runtime_counts_scalar_fallback_for_raw_batch_path():
    problem = _make_problem(_BatchRawFailScorer())
    keys = np.stack([_identity_key(), _swap_key(0, 1)], axis=0)
    pct, raw = problem.evaluate_keys_with_raw(keys, require_raw=True)
    assert np.isfinite(pct).all()
    assert np.isfinite(raw).all()
    assert int(problem.telemetry["score_batch_with_raw_calls"]) == 1
    assert int(problem.telemetry["score_batch_with_raw_fallback_scalar"]) == 1
