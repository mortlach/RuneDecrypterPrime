from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence

import numpy as np

from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime


def _enumerate_wli_context_pairs(max_word_len: int = 14) -> List[List[List[int]]]:
    """
    Enumerate (pos,len) context pairs for adjacent runes within the same word.

    Returns a list of [[pos1,len], [pos2,len]] entries suitable for WLI scoring.
    """
    contexts: List[List[List[int]]] = []
    for word_len in range(2, max_word_len + 1):
        for pos in range(word_len - 1):
            contexts.append([[pos, word_len], [pos + 1, word_len]])
    return contexts


@lru_cache(maxsize=None)
def _pt_batch(alphabet_size: int) -> List[List[int]]:
    batch: List[List[int]] = []
    for code in range(alphabet_size * alphabet_size):
        a = code // alphabet_size
        b = code % alphabet_size
        batch.append([a, b])
    return batch


@lru_cache(maxsize=None)
def build_wli_bigram_prior(
    alphabet_size: int = 29,
    *,
    direction: str = "rtl",
    se_mode: str = "nose",
    max_word_len: int = 14,
    count_weight: float = 1.5,
) -> np.ndarray:
    """
    Compute a WLI-LM-derived prior over plaintext bigrams.

    The prior is proportional to the LM log-probability of observing each bigram
    across enumerated WLI contexts (positions within words up to `max_word_len`).
    """
    num_codes = alphabet_size * alphabet_size
    lm = LanguageModelPrime(include_char=True)
    pt_batch = np.asarray(_pt_batch(alphabet_size), dtype=np.uint8)
    contexts = np.asarray(_enumerate_wli_context_pairs(max_word_len=max_word_len), dtype=np.uint8)

    log_probs, counts = lm.wli_bigram_logp_and_counts(
        pt_batch,
        contexts,
        direction=direction,
        se=se_mode,
        n=2,
    )

    finite = np.isfinite(log_probs)
    if not finite.any():
        return np.full(num_codes, 1.0 / num_codes, dtype=np.float64)

    log_probs[~finite] = log_probs[finite].min() - 20.0
    counts = np.asarray(counts, dtype=np.float64)
    log_weight = log_probs + float(count_weight) * np.log(counts + 1.0)

    finite_weight = np.isfinite(log_weight)
    if not finite_weight.any():
        return np.full(num_codes, 1.0 / num_codes, dtype=np.float64)
    log_weight[~finite_weight] = log_weight[finite_weight].min() - 20.0

    max_lp = float(log_weight.max())
    exp_vals = np.exp(log_weight - max_lp)

    total = float(exp_vals.sum())
    if not np.isfinite(total) or total <= 0.0:
        return np.full(num_codes, 1.0 / num_codes, dtype=np.float64)
    prior = exp_vals / total
    return prior.astype(np.float64, copy=False)


@dataclass
class BigramSeedGenerator:
    """
    Deterministic bigram permutation seed generator using LM-derived priors + optional cribs.
    """

    alphabet_size: int
    plaintext_prior: np.ndarray
    crib_ct_codes: Optional[Sequence[int]] = None
    crib_pt_codes: Optional[Sequence[int]] = None

    def __post_init__(self) -> None:
        self.num_bigrams = self.alphabet_size * self.alphabet_size
        prior = np.asarray(self.plaintext_prior, dtype=float).reshape(-1)
        if prior.shape != (self.num_bigrams,):
            raise ValueError(
                f"plaintext_prior must have shape ({self.num_bigrams},), got {prior.shape}"
            )
        np.clip(prior, 0.0, None, out=prior)
        if not np.isfinite(prior).all():
            raise ValueError("plaintext_prior must contain finite values")
        if prior.sum() == 0.0:
            prior[:] = 1.0
        self.plaintext_prior = prior / prior.sum()

        self.crib_ct_codes = (
            np.asarray(self.crib_ct_codes, dtype=np.int64).ravel()
            if self.crib_ct_codes is not None
            else np.empty(0, dtype=np.int64)
        )
        self.crib_pt_codes = (
            np.asarray(self.crib_pt_codes, dtype=np.int64).ravel()
            if self.crib_pt_codes is not None
            else np.empty(0, dtype=np.int64)
        )
        if self.crib_ct_codes.size != self.crib_pt_codes.size:
            raise ValueError("crib_ct_codes and crib_pt_codes must have the same length")

        if self.crib_ct_codes.size:
            if (self.crib_ct_codes < 0).any() or (self.crib_ct_codes >= self.num_bigrams).any():
                raise ValueError("crib_ct_codes entries must lie within permutation domain [0, A*A)")
            if (self.crib_pt_codes < 0).any() or (self.crib_pt_codes >= self.num_bigrams).any():
                raise ValueError("crib_pt_codes entries must lie within permutation codomain [0, A*A)")
            if np.unique(self.crib_ct_codes).size != self.crib_ct_codes.size:
                raise ValueError("crib_ct_codes contains duplicate positions")
            if np.unique(self.crib_pt_codes).size != self.crib_pt_codes.size:
                raise ValueError("crib_pt_codes contains duplicate values")

        full = np.arange(self.num_bigrams, dtype=np.int64)
        self.free_ct_codes = np.setdiff1d(full, self.crib_ct_codes, assume_unique=True)
        self.free_pt_codes = np.setdiff1d(full, self.crib_pt_codes, assume_unique=True)
        self._preferred_pt_codes = np.argsort(self.plaintext_prior)[::-1]
        self._preferred_pt_count = max(4, min(32, max(1, self.free_pt_codes.size // 4)))

    def cipher_bigram_counts(self, ct_indices: Sequence[int]) -> np.ndarray:
        ct = np.asarray(ct_indices, dtype=np.int64).reshape(-1)
        counts = np.zeros(self.num_bigrams, dtype=np.int64)
        for idx in range(0, ct.size - 1, 2):
            a = int(ct[idx])
            b = int(ct[idx + 1])
            if 0 <= a < self.alphabet_size and 0 <= b < self.alphabet_size:
                code = a * self.alphabet_size + b
                counts[code] += 1
        return counts

    def _sample_single_key(
        self,
        rng: np.random.Generator,
        cipher_counts: np.ndarray,
    ) -> np.ndarray:
        cipher_counts = np.asarray(cipher_counts, dtype=float).reshape(-1)
        key = np.empty(self.num_bigrams, dtype=np.int64)
        if self.crib_ct_codes.size:
            key[self.crib_ct_codes] = self.crib_pt_codes

        # Rank ciphertext bigrams (descending frequency + noise for tie-breaking)
        free_counts = cipher_counts[self.free_ct_codes]
        ct_noise = rng.random(self.free_ct_codes.size)
        ct_order = np.lexsort((ct_noise, -free_counts))

        # Rank plaintext bigrams using LM prior with Gumbel noise for diversity
        weights = self.plaintext_prior[self.free_pt_codes]
        if not np.isfinite(weights).all() or weights.sum() <= 0.0:
            weights = np.ones_like(weights, dtype=float) / max(1, weights.size)
        pt_noise = -np.log(-np.log(rng.random(self.free_pt_codes.size)))
        logits = np.log(weights + 1e-12) + pt_noise
        pt_order = np.argsort(logits)[::-1]
        ordered_pt_codes = self.free_pt_codes[pt_order]

        if ordered_pt_codes.size == 0:
            return key

        preferred_pool: list[int] = []
        free_pt_set = set(int(code) for code in self.free_pt_codes.tolist())
        for code in self._preferred_pt_codes:
            if code in free_pt_set:
                preferred_pool.append(int(code))
            if len(preferred_pool) >= self._preferred_pt_count:
                break

        assigned_ct: set[int] = set()
        assigned_pt: set[int] = set()
        for idx, pt_code in zip(ct_order, preferred_pool):
            ct_code = int(self.free_ct_codes[idx])
            key[ct_code] = pt_code
            assigned_ct.add(int(idx))
            assigned_pt.add(pt_code)

        remaining_pt_codes = [int(code) for code in ordered_pt_codes if int(code) not in assigned_pt]
        top_fraction = 0.3
        top_count = max(1, int(top_fraction * len(remaining_pt_codes)))
        top_pt_codes = remaining_pt_codes[:top_count]
        tail_pt_codes = remaining_pt_codes[top_count:]
        top_ct = max(1, int(top_fraction * max(1, ct_order.size - len(assigned_ct))))

        fill_order = [idx for idx in ct_order if idx not in assigned_ct]
        for rank, ct_idx in enumerate(fill_order):
            use_top = rank < top_ct and len(top_pt_codes) > 0
            pool = top_pt_codes if use_top else tail_pt_codes
            if not pool:
                pool = top_pt_codes if top_pt_codes else tail_pt_codes
            if not pool:
                raise RuntimeError("BigramSeedGenerator exhausted plaintext codes unexpectedly")
            pick_idx = int(rng.integers(0, len(pool)))
            pt_code = pool.pop(pick_idx)
            if use_top and not top_pt_codes and tail_pt_codes:
                top_pt_codes, tail_pt_codes = tail_pt_codes, top_pt_codes
            key[int(self.free_ct_codes[ct_idx])] = pt_code

        return key

    def _random_key(self, rng: np.random.Generator) -> np.ndarray:
        key = np.empty(self.num_bigrams, dtype=np.int64)
        if self.crib_ct_codes.size:
            key[self.crib_ct_codes] = self.crib_pt_codes
        remaining_pt = np.setdiff1d(np.arange(self.num_bigrams, dtype=np.int64), self.crib_pt_codes, assume_unique=True)
        shuffled = rng.permutation(remaining_pt)
        key[self.free_ct_codes] = shuffled[: self.free_ct_codes.size]
        return key

    def generate_seeds(
        self,
        ct_indices: Sequence[int],
        n_seeds: int,
        seed: Optional[int] = None,
        n_random: int = 0,
    ) -> list[list[int]]:
        rng = np.random.default_rng(seed)
        counts = self.cipher_bigram_counts(ct_indices)
        seeds: list[list[int]] = []
        for _ in range(max(0, int(n_seeds))):
            perm = self._sample_single_key(rng, counts)
            seeds.append(perm.astype(int).tolist())
        for _ in range(max(0, int(n_random))):
            seeds.append(self._random_key(rng).astype(int).tolist())
        return seeds
