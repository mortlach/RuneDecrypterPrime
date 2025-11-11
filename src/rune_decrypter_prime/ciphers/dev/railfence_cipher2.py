# rune_decrypter_prime/ciphers/railfence_cipher.py
from __future__ import annotations
import numpy as np
from rune_decrypter_prime.ciphers.ciphers_pipeline import CipherPipelineMixin, ArrayU8


class _ScalarOps:
    def __init__(self, min_val: int, max_val: int):
        if min_val >= max_val:
            raise ValueError("ScalarOps: min_val < max_val required")
        self.min = int(min_val); self.max = int(max_val)

    def random(self, rng) -> np.ndarray:
        v = rng.integers(self.min, self.max+1, dtype=np.int64)
        return np.asarray([int(v)], dtype=np.int64)

    def mutate(self, rng, key: np.ndarray) -> np.ndarray:
        v = int(key[0])
        # small wiggle
        if rng.random() < 0.5 and v > self.min:
            v -= 1
        elif v < self.max:
            v += 1
        return np.asarray([v], dtype=np.int64)

    def crossover(self, rng, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.asarray([int(a[0] if rng.random() < 0.5 else b[0])], dtype=np.int64)

class RailFenceCipher(CipherPipelineMixin):
    """
    Railfence (zig-zag) transposition. Key = rails (integer >= 2).
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="ltr", key_transposition="ltr"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg = cfg
        # allow a sensible search range (2..10) if key_length absent
        rails = int(getattr(cfg, "key_length", 0) or 0)
        if rails >= 2:
            self.fixed_rails = rails
            self.keyops = _ScalarOps(rails, rails)
        else:
            # UI/solver will vary rails
            self.fixed_rails = None
            self.keyops = _ScalarOps(2, int(getattr(cfg, "max_rails", 10)))

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B = keys_tr.shape[0]
        L = int(ct_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            rails = int(keys_tr[b, 0]) if self.fixed_rails is None else int(self.fixed_rails)
            out[b] = self._decrypt_single(ct_tr, rails)
        return out

    @staticmethod
    def _decrypt_single(ct: np.ndarray, rails: int) -> np.ndarray:
        L = int(ct.size)
        if rails <= 1 or rails >= L:
            return ct.copy()

        # 1) Build zigzag order indices
        order = RailFenceCipher._zigzag_order(L, rails)
        # 2) Place CT chars into positions according to the zigzag read order
        pt = np.empty(L, dtype=np.uint8)
        pt[order] = ct  # order describes the order in which PT was read to form CT
        return pt

    @staticmethod
    def _zigzag_order(L: int, rails: int) -> np.ndarray:
        # Generate indices in the order they would be read during encryption.
        # Then at decrypt we invert that mapping by assignment.
        lines = [[] for _ in range(rails)]
        rail = 0; step = 1
        for i in range(L):
            lines[rail].append(i)
            rail += step
            if rail == 0 or rail == rails - 1:
                step *= -1
        order = np.array([i for r in lines for i in r], dtype=np.int64)
        return order
