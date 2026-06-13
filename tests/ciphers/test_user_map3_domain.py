from __future__ import annotations

from types import SimpleNamespace
import numpy as np
import pytest

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.ciphers.generic_map_cipher import GenericMapCipher
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem


pytestmark = pytest.mark.tier_a


class _ZeroScorer:
    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)


def test_user_map3_domain():
    A = 5

    def f(pt, k1, k2):
        return (pt + k1 + k2) % A

    spec = SimpleNamespace(kind="user_map3", N=A, function=f)
    cfg = CipherConfig(
        ciphertext=[0],
        wli_data=[],
        key_length=1,
        name="user_map3",
    )
    setattr(cfg, "spec", spec)

    cipher = GenericMapCipher(cfg)
    problem = DecryptionProblem(cipher=cipher, scorer=_ZeroScorer(), c_cfg=cfg, s_cfg=ScoringConfig())

    keyops = problem.keyops
    mod = getattr(keyops, "mod", getattr(getattr(keyops, "caps", None), "traits", {}).get("mod", None))
    assert mod == A * A
