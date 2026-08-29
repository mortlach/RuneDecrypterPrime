from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.core.config import CipherConfig
from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
from rune_decrypter_prime.core.types import Direction, KEY_DTYPE
from rune_decrypter_prime.ciphers.generic_map_cipher import GenericMapCipher

pytestmark = pytest.mark.tier_a


class SumScorer:
    """Simple scorer: prefers higher sum of plaintext symbols."""

    def batch_score(self, pts, wli=None):
        return np.asarray(
            [float(np.sum(np.asarray(p, dtype=np.int64))) for p in pts],
            dtype=np.float64,
        )


def _build_problem(table: np.ndarray, ct: np.ndarray) -> DecryptionProblem:
    spec = api.experimental.define_cipher_lookup(
        table.tolist(),
        alphabet_size=int(table.shape[0]),
        degeneracy=api.experimental.DegeneracyPolicy.ALLOW,
        resolver=api.experimental.ResolverMode.EXPAND_BEAM,
        per_position_limit=29,
        resolver_limit=8193,
        name="lookup",
    )
    cfg = CipherConfig(
        ciphertext=ct,
        wli_data=[],
        key_length=1,
        device="cpu",
        encoding_dir=Direction.LTR,
        name="lookup",
    )
    setattr(cfg, "spec", spec)
    cipher = GenericMapCipher(cfg)
    return DecryptionProblem(
        cipher=cipher, scorer=SumScorer(), c_cfg=cfg, s_cfg=api.ScoringConfig()
    )


def _build_table() -> np.ndarray:
    table = np.empty((29, 1), dtype=object)
    table[0, 0] = 0
    table[1, 0] = 0
    table[2, 0] = 1
    table[3, 0] = 0
    table[4, 0] = 2
    for pt in range(5, 29):
        table[pt, 0] = pt % 24 + 5
    return table


def test_expand_beam_picks_best_candidate():
    table = _build_table()
    ct = np.array([0, 0], dtype=np.uint8)
    problem = _build_problem(table, ct)
    key = np.array([0], dtype=KEY_DTYPE)
    scores = problem.evaluate_keys(key)
    assert scores.shape == (1,)
    assert float(scores[0]) == 6.0
    pt = problem.resolve_plaintext(key)
    assert pt is not None
    assert pt.tolist() == [3, 3]


def test_lookup_multi_valued_entries_are_used():
    table = _build_table()
    ct = np.array([2], dtype=np.uint8)
    problem = _build_problem(table, ct)
    key = np.array([0], dtype=KEY_DTYPE)
    pt = problem.resolve_plaintext(key)
    assert pt is not None
    assert pt.tolist() == [4]


def test_invalid_keys_drop_to_neg_inf():
    table = _build_table()
    ct = np.array([3], dtype=np.uint8)
    problem = _build_problem(table, ct)
    key = np.array([0], dtype=KEY_DTYPE)
    scores = problem.evaluate_keys(key)
    assert scores.shape == (1,)
    assert np.isneginf(scores[0])
