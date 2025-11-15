from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from rune_decrypter_prime.ciphers.bigram_substitution_cipher import BigramSubstitutionCipher


def _cipher(**overrides) -> BigramSubstitutionCipher:
    cfg = SimpleNamespace(
        text_transposition="ltr",
        key_transposition="ltr",
        **overrides,
    )
    return BigramSubstitutionCipher(cfg)


def _random_key(seed: int = 123) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.permutation(29 * 29).astype(np.uint16)


def test_bigram_roundtrip_encrypt_decrypt():
    cipher = _cipher()
    key = _random_key()
    plaintext = np.arange(60, dtype=np.uint8) % cipher.alphabet

    ciphertext = cipher._core_encrypt_batch(plaintext, key)[0]
    recovered = cipher._core_decrypt_batch(ciphertext, key)[0]

    np.testing.assert_array_equal(recovered[: plaintext.size], plaintext)


def test_bigram_pad_value_handles_odd_length():
    cipher = _cipher(pad_value=3)
    key = _random_key()
    plaintext = np.array([5, 7, 9], dtype=np.uint8)

    ciphertext = cipher._core_encrypt_batch(plaintext, key)[0]
    assert ciphertext.size >= plaintext.size
    recovered = cipher._core_decrypt_batch(ciphertext, key)[0]
    np.testing.assert_array_equal(recovered[: plaintext.size], plaintext)


def test_bigram_seed_key_from_crib_matches_alignment():
    cipher = _cipher()
    key = _random_key()
    plaintext = np.arange(40, dtype=np.uint8) % cipher.alphabet
    ciphertext = cipher._core_encrypt_batch(plaintext, key)[0]

    crib = plaintext[:10]
    seeded = cipher.seed_key_from_crib(ciphertext, crib, offset=0, alphabet=cipher.alphabet, rng_seed=7)
    assert seeded.shape[0] == 29 * 29


def test_cipher_parses_bigram_crib_and_sets_hints():
    crib = [(0, 5), (17, 23)]
    cipher = _cipher(bigram_crib=crib)
    assert cipher.crib_ct_codes.tolist() == [0, 17]
    assert cipher.crib_pt_codes.tolist() == [5, 23]
    assert cipher.keyops_family.value == "cribbed_permutation"
    assert cipher.keyops_hints["crib_ct_codes"] == [0, 17]
    assert cipher.keyops_hints["crib_pt_codes"] == [5, 23]


def test_bigram_multi_option_crib_sets_hints():
    crib = [
        {"cipher": 5, "options": [{"plain": 7}, {"plain": 9, "weight": 2.0}]},
    ]
    cipher = _cipher(bigram_crib=crib)
    assert cipher.crib_ct_codes.size == 0
    assert isinstance(cipher.crib_multi, list)
    assert cipher.crib_multi[0]["ct"] == 5
    hints = cipher.keyops_hints
    assert "crib_multi" in hints
    assert hints["crib_multi"][0]["ct"] == 5
    assert hints["crib_multi"][0]["pt_codes"] == [7, 9]
    assert hints["crib_multi"][0]["weights"] == [None, 2.0]
    assert cipher.keyops_family.value == "cribbed_permutation"
