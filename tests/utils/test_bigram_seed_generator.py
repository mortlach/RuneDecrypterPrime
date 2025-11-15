from __future__ import annotations

import numpy as np

from rune_decrypter_prime.utils.bigram_seed_generator import (
    BigramSeedGenerator,
    build_wli_bigram_prior,
)


def test_bigram_seed_generator_respects_crib():
    alphabet = 5
    num_codes = alphabet * alphabet
    prior = np.ones(num_codes, dtype=float)
    crib_ct = [0, 7]
    crib_pt = [3, 11]
    gen = BigramSeedGenerator(
        alphabet_size=alphabet,
        plaintext_prior=prior,
        crib_ct_codes=crib_ct,
        crib_pt_codes=crib_pt,
    )
    ciphertext = [0, 1, 2, 3, 4, 0, 1, 2]
    seeds = gen.generate_seeds(ciphertext, n_seeds=3, seed=42)
    for seed in seeds:
        assert seed[0] == 3
        assert seed[7] == 11
        assert sorted(seed) == list(range(num_codes))


def test_bigram_seed_generator_counts_bigram_frequency():
    prior = np.ones(9, dtype=float)
    gen = BigramSeedGenerator(alphabet_size=3, plaintext_prior=prior)
    ciphertext = [0, 1, 0, 1, 2, 2, 2, 2]
    counts = gen.cipher_bigram_counts(ciphertext)
    assert counts.tolist() == [0, 2, 0, 0, 0, 0, 0, 0, 2]


def test_build_wli_bigram_prior_is_probability_vector():
    prior = build_wli_bigram_prior(alphabet_size=5, max_word_len=4)
    assert prior.shape == (25,)
    assert np.isfinite(prior).all()
    assert np.isclose(prior.sum(), 1.0)
    positive = prior[prior > 0]
    assert positive.size
    assert prior.max() > positive.mean() * 2
