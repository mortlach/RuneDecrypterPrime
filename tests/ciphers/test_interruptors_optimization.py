from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import define_map
from rune_decrypter_prime.ciphers.generic_map_cipher import GenericMapCipher
from rune_decrypter_prime.core.config import CipherConfig, InterruptorConfig
from rune_decrypter_prime.core.problem import DecryptionProblem
from rune_decrypter_prime.core.types import Direction, Device, KeyOpsFamily, KEY_DTYPE

pytestmark = pytest.mark.tier_a


class _ExactMatchScorer:
    def __init__(self, target: np.ndarray):
        self._target = np.asarray(target, dtype=np.uint8).reshape(-1)

    def score(self, pt, wli=None) -> float:
        arr = np.asarray(pt, dtype=np.uint8).reshape(-1)
        return 1.0 if np.array_equal(arr, self._target) else 0.0

    def batch_score(self, pts, wli=None):
        return np.asarray([self.score(p, wli) for p in pts], dtype=np.float64)


def test_interruptor_positions_are_part_of_key_search():
    spec = define_map(
        N=29,
        function=lambda pt, k: (pt + k) % 29,
        degeneracy="forbid",
        resolver="first",
        per_pos_limit=29,
        resolver_limit=8193,
    )

    plaintext = np.array([2, 5, 7, 11, 13, 3, 8, 12, 1, 4, 6, 9], dtype=np.uint8)
    key_core = np.array([3, 1, 4], dtype=np.uint8)
    interruptors = [1, 6]

    enc_cfg = CipherConfig(
        ciphertext=np.zeros_like(plaintext),
        wli_data=[[0, int(plaintext.size)]],
        key_length=int(key_core.size),
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        name=spec.kind,
    )
    setattr(enc_cfg, "spec", spec)
    enc_cipher = GenericMapCipher(enc_cfg)
    ciphertext = enc_cipher.encrypt_single(plaintext=plaintext, key=key_core, interrupt_idx=interruptors)

    pool = [1, 4, 6, 8]
    cfg = CipherConfig(
        ciphertext=ciphertext,
        wli_data=[[0, int(plaintext.size)]],
        key_length=int(key_core.size),
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        name=spec.kind,
        interruptors_cfg=InterruptorConfig(
            mode="pool",
            pool=pool,
            min_count=len(interruptors),
            max_count=len(interruptors),
        ),
    )
    setattr(cfg, "spec", spec)
    cipher = GenericMapCipher(cfg)

    scorer = _ExactMatchScorer(plaintext)
    problem = DecryptionProblem(cipher=cipher, scorer=scorer, c_cfg=cfg)
    assert problem.keyops.caps.traits.get("family") == KeyOpsFamily.COMPOSITE

    key_good = np.concatenate([key_core.astype(KEY_DTYPE), np.array(sorted(interruptors), dtype=KEY_DTYPE)])
    key_bad = np.concatenate([key_core.astype(KEY_DTYPE), np.array([4, 8], dtype=KEY_DTYPE)])

    pt_bad = cipher.decrypt_single(ciphertext=ciphertext, key=key_core, interrupt_idx=[4, 8])
    assert not np.array_equal(pt_bad, plaintext)

    scores = problem.evaluate_keys(np.stack([key_bad, key_good], axis=0))
    assert scores[1] > scores[0]


def test_interruptor_pool_allows_variable_count_with_sentinel():
    spec = define_map(
        N=29,
        function=lambda pt, k: (pt + k) % 29,
        degeneracy="forbid",
        resolver="first",
        per_pos_limit=29,
        resolver_limit=8193,
    )

    plaintext = np.array([2, 5, 7, 11, 13, 3, 8, 12, 1, 4, 6, 9], dtype=np.uint8)
    key_core = np.array([3, 1, 4], dtype=np.uint8)
    interruptors = [2]

    enc_cfg = CipherConfig(
        ciphertext=np.zeros_like(plaintext),
        wli_data=[[0, int(plaintext.size)]],
        key_length=int(key_core.size),
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        name=spec.kind,
    )
    setattr(enc_cfg, "spec", spec)
    enc_cipher = GenericMapCipher(enc_cfg)
    ciphertext = enc_cipher.encrypt_single(plaintext=plaintext, key=key_core, interrupt_idx=interruptors)

    pool = [0, 2, 5, 7]
    cfg = CipherConfig(
        ciphertext=ciphertext,
        wli_data=[[0, int(plaintext.size)]],
        key_length=int(key_core.size),
        encoding_dir=Direction.LTR,
        device=Device.CPU,
        name=spec.kind,
        interruptors_cfg=InterruptorConfig(
            mode="pool",
            pool=pool,
            min_count=0,
            max_count=2,
        ),
    )
    setattr(cfg, "spec", spec)
    cipher = GenericMapCipher(cfg)

    scorer = _ExactMatchScorer(plaintext)
    problem = DecryptionProblem(cipher=cipher, scorer=scorer, c_cfg=cfg)

    key_good = np.concatenate(
        [
            key_core.astype(KEY_DTYPE),
            np.array([interruptors[0], -1], dtype=KEY_DTYPE),
        ]
    )

    scores = problem.evaluate_keys(key_good[None, :])
    assert scores[0] == pytest.approx(1.0)
