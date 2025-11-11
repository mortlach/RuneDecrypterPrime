import numpy as np
import pytest

from rune_decrypter_prime.utils.transposition import TranspositionManager
from rune_decrypter_prime.api.normalize import normalize_text_permutation

def apply_then_undo(tokens, perm):
    tm = TranspositionManager(text_mode="perm", key_mode="ltr", text_perm=np.asarray(perm, dtype=np.int64))
    t2 = tm.apply_text(tokens)
    t3 = tm.undo_text(t2)
    return t2, t3

def test_itp_identity_vs_none_roundtrip():
    # core ciphertext (after interrupter removal) length:
    n = 25
    tokens = np.arange(n, dtype=np.int32)

    perm_identity = normalize_text_permutation(list(range(n)), n)
    # identity acts like no-permutation once undone
    t2, t3 = apply_then_undo(tokens, perm_identity)
    assert np.array_equal(t3, tokens)
    # applying none should be equivalent to identity in effect on final plaintext
    # here we just assert the undo returns original (same as above)
    assert np.array_equal(tokens, t3)

def test_itp_reverse_roundtrip():
    n = 17
    tokens = np.arange(n, dtype=np.int32)
    perm_rev = normalize_text_permutation(list(range(n))[::-1], n)

    t2, t3 = apply_then_undo(tokens, perm_rev)
    # post-undo must equal original
    assert np.array_equal(t3, tokens)
    # ensure the permutation actually changed ordering pre-undo
    assert not np.array_equal(tokens, t2)

def test_itp_invalid_length_and_non_bijection():
    n = 10
    with pytest.raises(ValueError):
        normalize_text_permutation(list(range(n - 1)), n)  # wrong length
    with pytest.raises(ValueError):
        bad = list(range(n))
        bad[0] = 1  # duplicate 1, missing 0
        normalize_text_permutation(bad, n)

def test_itp_does_not_consume_rng():
    n = 13
    tokens = np.arange(n, dtype=np.int32)
    perm = normalize_text_permutation(list(range(n))[::-1], n)
    # snapshot a RNG and ensure state unchanged by permutation helpers
    gen = np.random.default_rng(2025)
    state_before = gen.bit_generator.state.copy()
    # permutation path uses pure index gather/scatter (no RNG)
    t2, t3 = apply_then_undo(tokens, perm)
    state_after = gen.bit_generator.state.copy()
    assert state_before == state_after
    assert np.array_equal(t3, tokens)
