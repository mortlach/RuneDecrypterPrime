# rune_decrypter_prime/ciphers/vigenere_family_cipher.py
from __future__ import annotations
import numpy as np
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin, ArrayU8

class _RepeatVectorOps:
    """
    Key: length-K vector with values in [0..A-1], repeated across text.
    Satisfies GA: random/mutate/crossover.
    """
    def __init__(self, K: int, A: int):
        if K <= 0: raise ValueError("RepeatVectorOps requires K > 0")
        self.K = int(K); self.A = int(A)

    def random(self, rng) -> np.ndarray:
        return rng.integers(0, self.A, size=self.K, dtype=np.int64)

    def mutate(self, rng, key: np.ndarray) -> np.ndarray:
        k = key.astype(np.int64, copy=True)
        i = int(rng.integers(0, self.K))
        # small +/- step modulo A
        delta = int(rng.integers(1, max(2, self.A//8)))
        if rng.random() < 0.5:
            k[i] = (k[i] + delta) % self.A
        else:
            k[i] = (k[i] - delta) % self.A
        return k

    def crossover(self, rng, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        cut = int(rng.integers(1, self.K))
        child = np.empty_like(a, dtype=np.int64)
        child[:cut] = a[:cut]; child[cut:] = b[cut:]
        return child

class VigenereFamilyCipher(CipherPipelineMixin):
    """
    Generalized stream-add/sub/xor families over modulus A.

    mode:
      'vigenere'         : ct = (pt + k) % A
      'caesar'           : same but K=1
      'variant_vigenere' : ct = (pt - k) % A
      'beaufort'         : ct = (k - pt) % A
      'xor_mod'          : ct = (pt ^ k) % A  (bitwise xor then mod, for demo)

    Key: repeat vector of length K in [0..A-1].
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", text_transposition),
            key_transposition=getattr(cfg, "key_transposition", key_transposition),
        )
        self.cfg  = cfg
        self.mode = str(getattr(cfg, "mode", "vigenere")).lower()
        K = int(getattr(cfg, "key_length", 0) or 1)
        if self.mode == "caesar":
            K = 1
        if K <= 0:
            raise ValueError("VigenereFamily requires key_length K > 0")
        self.K = K
        self.keyops = _RepeatVectorOps(K, self.A)

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(ct_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            out[b] = self._decrypt_single(ct_tr, np.asarray(keys_tr[b], dtype=np.int64))
        return out

    def _core_encrypt_batch(self, pt_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        L = int(pt_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            out[b] = self._encrypt_single(pt_tr, np.asarray(keys_tr[b], dtype=np.int64))
        return out

    # scalar
    def _decrypt_single(self, ct: np.ndarray, key_vec: np.ndarray) -> np.ndarray:
        A = self.A; L = int(ct.size); K = int(key_vec.size)
        k = np.resize(key_vec, L).astype(np.int64, copy=False)
        c = ct.astype(np.int64, copy=False)
        if self.mode == "vigenere":
            # pt = (ct - k) % A
            x = (c - k) % A
        elif self.mode == "variant_vigenere":
            # pt = (ct + k) % A   (inverse of pt - k)
            x = (c + k) % A
        elif self.mode == "beaufort":
            # ct = (k - pt) % A => pt = (k - ct) % A
            x = (k - c) % A
        elif self.mode == "xor_mod":
            # model xor as (pt ^ k) % A => inverse is itself (involutive), then % A
            x = (np.bitwise_xor(c, k)) % A
        elif self.mode == "caesar":
            x = (c - k) % A
        else:
            raise ValueError(f"Unsupported mode '{self.mode}'")
        return x.astype(np.uint8, copy=False)

    def _encrypt_single(self, pt: np.ndarray, key_vec: np.ndarray) -> np.ndarray:
        A = self.A; L = int(pt.size); K = int(key_vec.size)
        k = np.resize(key_vec, L).astype(np.int64, copy=False)
        p = pt.astype(np.int64, copy=False)
        if self.mode == "vigenere":
            x = (p + k) % A
        elif self.mode == "variant_vigenere":
            x = (p - k) % A
        elif self.mode == "beaufort":
            x = (k - p) % A
        elif self.mode == "xor_mod":
            x = (np.bitwise_xor(p, k)) % A
        elif self.mode == "caesar":
            x = (p + k) % A
        else:
            raise ValueError(f"Unsupported mode '{self.mode}'")
        return x.astype(np.uint8, copy=False)
