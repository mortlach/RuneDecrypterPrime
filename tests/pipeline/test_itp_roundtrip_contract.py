import rdp.api.normalize
import numpy as np
import pytest
from rune_decrypter_prime.utils.transposition import TranspositionManager

def apply_then_undo(tokens, perm):
    tm = TranspositionManager(text_mode='perm', key_mode='ltr', text_perm=np.asarray(perm, dtype=np.int64))
    t2 = tm.apply_text(tokens)
    t3 = tm.undo_text(t2)
    return (t2, t3)

def test_itp_identity_vs_none_roundtrip():
    n = 25
    tokens = np.arange(n, dtype=np.int32)
    perm_identity = rdp.api.normalize.normalize_text_permutation(list(range(n)), n)
    t2, t3 = apply_then_undo(tokens, perm_identity)
    assert np.array_equal(t3, tokens)
    assert np.array_equal(tokens, t3)

def test_itp_reverse_roundtrip():
    n = 17
    tokens = np.arange(n, dtype=np.int32)
    perm_rev = rdp.api.normalize.normalize_text_permutation(list(range(n))[::-1], n)
    t2, t3 = apply_then_undo(tokens, perm_rev)
    assert np.array_equal(t3, tokens)
    assert not np.array_equal(tokens, t2)

def test_itp_invalid_length_and_non_bijection():
    n = 10
    with pytest.raises(ValueError):
        rdp.api.normalize.normalize_text_permutation(list(range(n - 1)), n)
    with pytest.raises(ValueError):
        bad = list(range(n))
        bad[0] = 1
        rdp.api.normalize.normalize_text_permutation(bad, n)

def test_itp_does_not_consume_rng():
    n = 13
    tokens = np.arange(n, dtype=np.int32)
    perm = rdp.api.normalize.normalize_text_permutation(list(range(n))[::-1], n)
    gen = np.random.default_rng(2025)
    state_before = gen.bit_generator.state.copy()
    t2, t3 = apply_then_undo(tokens, perm)
    state_after = gen.bit_generator.state.copy()
    assert state_before == state_after
    assert np.array_equal(t3, tokens)
