from __future__ import annotations

from types import SimpleNamespace
import numpy as np
import pytest

from rune_decrypter_prime.core.config import CipherConfig, InterruptorConfig
from rune_decrypter_prime.ciphers.generic_map_cipher import GenericMapCipher
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem

pytestmark = pytest.mark.tier_a


class _ZeroScorer:
    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)


def _build_problem_with_pool_wli():
    spec = SimpleNamespace(kind="user_map2", N=29, function=lambda pt, k: (pt + k) % 29)
    ct = np.array([0, 1, 2, 3], dtype=np.uint8)
    wli = [[0, 4], [1, 4], [2, 4], [3, 4]]

    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=wli,
        key_length=1,
        name="user_map2",
        interruptors_cfg=InterruptorConfig(
            mode="pool",
            pool=[0, 1, 2, 3],
            min_count=0,
            max_count=2,
        ),
    )
    setattr(cfg, "spec", spec)
    cipher = GenericMapCipher(cfg)

    return DecryptionProblem(cipher=cipher, scorer=_ZeroScorer(), c_cfg=cfg), ct


def test_interruptor_pool_allows_wli_alignment():
    problem, ct = _build_problem_with_pool_wli()
    scores = problem._score_batch_texts([ct], problem.wli_data)
    assert scores.shape[0] == 1


def test_wli_length_mismatch_raises():
    problem, _ = _build_problem_with_pool_wli()
    bad_pt = np.array([1, 2, 3], dtype=np.uint8)
    with pytest.raises(ValueError, match="WLI length"):
        problem._score_batch_texts([bad_pt], problem.wli_data)
