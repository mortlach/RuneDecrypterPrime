from __future__ import annotations
from rdp import api
import numpy as np
from rune_decrypter_prime.utils.runeglish import Runeglish

def build_mono_ciphertext(plaintext: str, *, direction: api.TextDirection=api.TextDirection.RIGHT_TO_LEFT, cipher_seed: int=12345) -> tuple[str, list[list[int]], np.ndarray, np.ndarray]:
    """
    Encode plaintext into runes/WLI, encrypt with a deterministic mono key,
    and return (ciphertext_runes, wli, plaintext_idx, key_forward).
    """
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(plaintext, direction=direction)
    pt_idx = np.asarray(pt_idx, dtype=np.uint8)
    rng = np.random.default_rng(cipher_seed)
    key_forward = rng.permutation(29).astype(np.uint8)
    mono = api.CipherSpec.substitution(alphabet_size=29)
    ct_idx = api.encrypt(tuple(int(value) for value in pt_idx), cipher=mono, key=tuple(int(value) for value in key_forward))
    ct_runes = Runeglish.to_rune(list(ct_idx), wli)
    return (ct_runes, wli, pt_idx, key_forward)

def invert_permutation(key: np.ndarray) -> np.ndarray:
    inv = np.empty_like(key)
    inv[key] = np.arange(key.size, dtype=np.uint8)
    return inv

def noisy_permutation_seeds(key: np.ndarray, *, swaps: int, count: int, seed: int, include_true: bool=False) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    seeds: list[list[int]] = []
    if include_true:
        seeds.append(key.tolist())
    for _ in range(count):
        cand = key.copy()
        for __ in range(max(1, swaps)):
            i, j = rng.integers(0, cand.size, size=2)
            if i != j:
                cand[i], cand[j] = (cand[j], cand[i])
        seeds.append(cand.tolist())
    return seeds

def plaintext_match_rate(found_idx, reference_idx) -> float:
    found = np.asarray(found_idx, dtype=np.uint8).ravel()
    ref = np.asarray(reference_idx, dtype=np.uint8).ravel()
    n = min(found.size, ref.size)
    if n == 0:
        return 0.0
    return float(np.mean(found[:n] == ref[:n]))
