import numpy as np
import pytest
from math import factorial
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.utils.seed_utils_periodic_columnar_sub_then_col import enumerate_column_permutations, undo_columnar_with_perm
pytestmark = pytest.mark.tier_a

def _is_perm(values: list[int], n: int) -> bool:
    return sorted(values) == list(range(n))

def test_enumerate_column_permutations_exact_mode_deterministic_order():
    perms1 = enumerate_column_permutations(5, max_exact_columns=7, sample_size=99, seed=1)
    perms2 = enumerate_column_permutations(5, max_exact_columns=7, sample_size=99, seed=1)
    assert perms1 == perms2
    assert len(perms1) == factorial(5)
    assert (0, 1, 2, 3, 4) in perms1
    assert len(perms1) == len(set(perms1))

def test_enumerate_column_permutations_sample_mode_unique_and_deterministic():
    p1 = enumerate_column_permutations(10, max_exact_columns=7, sample_size=64, seed=2026)
    p2 = enumerate_column_permutations(10, max_exact_columns=7, sample_size=64, seed=2026)
    assert p1 == p2
    assert len(p1) >= 64
    assert len(p1) == len(set(p1))
    assert (0, 1, 2, 3, 4, 5, 6, 7, 8, 9) in p1

def test_tail_candidates_can_form_valid_full_keys():
    A = 29
    period = 3
    columns = 7
    rng = np.random.default_rng(77)
    sub_phases = [rng.permutation(A).astype(np.int16) for _ in range(period)]
    sub_block = np.concatenate(sub_phases, axis=0).astype(np.int16)
    tails = enumerate_column_permutations(columns, max_exact_columns=7, sample_size=64, seed=2026)[:16]
    for tail in tails:
        full_key = np.concatenate([sub_block, np.asarray(tail, dtype=np.int16)], axis=0)
        assert int(full_key.size) == period * A + columns
        for p in range(period):
            phase = full_key[p * A:(p + 1) * A].astype(int).tolist()
            assert _is_perm(phase, A)
        tail_list = full_key[period * A:].astype(int).tolist()
        assert _is_perm(tail_list, columns)

def test_undo_columnar_with_perm_matches_cipher_path():
    period = 1
    A = 29
    columns = 7
    key_len = period * A + columns
    cfg = CipherConfig(name='periodic_columnar', ciphertext=[], period=period, columns=columns, alphabet_size=A, key_length=key_len, order='sub_then_col', encoding_dir=Direction.LTR, wli_data=[], device=Device.CPU)
    cipher = PeriodicColumnarCipher(cfg)
    rng = np.random.default_rng(1234)
    pt = rng.integers(0, A, size=317, dtype=np.uint8)
    sub_identity = np.arange(A, dtype=np.int16)
    col_perm = rng.permutation(columns).astype(np.int16)
    key = np.concatenate([sub_identity, col_perm], axis=0).astype(np.int16)
    ct = np.asarray(cipher.encrypt_single(plaintext=pt, key=key), dtype=np.uint8)
    recovered = undo_columnar_with_perm(ct, perm=col_perm.tolist())
    assert np.array_equal(recovered, pt)

def test_undo_columnar_columns_one_is_noop():
    arr = np.asarray([1, 2, 3, 4, 5], dtype=np.uint8)
    out = undo_columnar_with_perm(arr, perm=[0])
    assert np.array_equal(out, arr)

def test_exact_tail_coverage_regression_topn_and_diversity():
    period = 1
    A = 29
    columns = 5
    key_len = period * A + columns
    cfg = CipherConfig(name='periodic_columnar', ciphertext=[], period=period, columns=columns, alphabet_size=A, key_length=key_len, order='sub_then_col', encoding_dir=Direction.LTR, wli_data=[], device=Device.CPU)
    cipher = PeriodicColumnarCipher(cfg)
    rng = np.random.default_rng(4242)
    pt = rng.integers(0, A, size=401, dtype=np.uint8)
    sub_identity = np.arange(A, dtype=np.int16)
    true_tail = np.asarray([2, 4, 1, 0, 3], dtype=np.int16)
    key = np.concatenate([sub_identity, true_tail], axis=0).astype(np.int16)
    ct = np.asarray(cipher.encrypt_single(plaintext=pt, key=key), dtype=np.uint8)
    perms = enumerate_column_permutations(columns, max_exact_columns=7, sample_size=256, seed=2026)
    ranked = []
    for tail in perms:
        rec = undo_columnar_with_perm(ct, perm=tail)
        score = -int(np.count_nonzero(rec != pt))
        ranked.append((score, tail))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top_n = 20
    top_tails = [tail for _score, tail in ranked[:top_n]]
    unique_top = len(set(top_tails))
    assert unique_top > 1
    assert tuple((int(x) for x in true_tail.tolist())) in set(top_tails)
