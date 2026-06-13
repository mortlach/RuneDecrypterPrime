# tests/_helpers/vigenere_case.py
from __future__ import annotations
import numpy as np

from rune_decrypter_prime.data.cipher_tests.baseline_registry import BASELINE
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1

A = 29  # CICADA29 alphabet size used across the suite


def enc_vigenere_idx(pt: np.ndarray, key: np.ndarray) -> np.ndarray:
    """Index-space Vigenère encryption (mod A)."""
    L, K = pt.size, key.size
    cols = np.arange(L, dtype=np.int64) % K
    return ((pt.astype(np.int16) + key[cols].astype(np.int16)) % A).astype(np.uint8)


def build_vigenere_known_key_case(rng_seed: int):
    """
    Returns the exact argument set the harness runner expects for a Vigenère roundtrip:
      plaintext_idx, wli_data, make_key, encrypt_fn, key_length, known_key
    All derived from the global BASELINE (seed, key_length).
    """
    K = int(BASELINE.get("key_length", 7))
    rng = np.random.default_rng(int(rng_seed))
    known_key = rng.integers(0, A, size=K, dtype=np.uint8)

    def make_key(_: np.random.Generator) -> np.ndarray:
        return known_key.copy()

    def encrypt_fn(pt: np.ndarray, key: np.ndarray) -> np.ndarray:
        return enc_vigenere_idx(pt, key)

    pt_idx = np.asarray(plaintext1, dtype=np.uint8)
    return pt_idx, word_breaks1, make_key, encrypt_fn, K, known_key
