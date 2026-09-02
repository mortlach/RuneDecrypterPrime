from __future__ import annotations
from types import SimpleNamespace
import numpy as np
import pytest
from rdp.ciphers.scheduled_stream_lookup_cipher import ScheduledStreamLookupCipher
pytestmark = pytest.mark.tier_a

def _cipher(**kwargs):
    return ScheduledStreamLookupCipher(SimpleNamespace(**kwargs))

def _roundtrip(cipher, key, pt):
    ct = cipher.encrypt(plaintext=pt, key=key)[0]
    got = cipher.decrypt(ciphertext=ct, key=key)[0]
    assert np.array_equal(got, pt)
    return ct

def test_two_period_vigenere_overlay_roundtrip():
    c = _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 3}, {'name': 'B', 'kind': 'periodic', 'period': 5}], schedule='overlay', operation='add', key_length=8)
    pt = np.arange(31, dtype=int) * 2 % 29
    key = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=int)
    ct = _roundtrip(c, key, pt)
    manual = []
    for i, p in enumerate(pt.tolist()):
        ka = int(key[i % 3])
        kb = int(key[3 + i % 5])
        manual.append((int(p) + ka + kb) % 29)
    assert ct.tolist() == manual

def test_periodic_plus_primes_roundtrip():
    c = _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 4}, {'name': 'B', 'kind': 'primes', 'offset': 0}], schedule='overlay', operation='add', key_length=4)
    pt = np.arange(24, dtype=int) * 3 % 29
    key = np.array([1, 5, 9, 13], dtype=int)
    _roundtrip(c, key, pt)

def test_generic_sequence_alias_roundtrip():
    c = _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 3}, {'name': 'S', 'kind': 'sequence', 'values': [5, 7, 11]}], schedule='overlay', operation='add', key_length=3)
    pt = np.arange(20, dtype=int) % 29
    key = np.array([1, 2, 3], dtype=int)
    _roundtrip(c, key, pt)

def test_fixed_stream_roundtrip():
    c = _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 3}, {'name': 'B', 'kind': 'fixed', 'values': [5, 7, 11]}], schedule='overlay', operation='add_sub', key_length=3)
    pt = np.arange(20, dtype=int) % 29
    key = np.array([1, 2, 3], dtype=int)
    _roundtrip(c, key, pt)

def test_fixed_stream_values_are_symbols_not_text():
    with pytest.raises(ValueError, match='not text'):
        _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 3}, {'name': 'B', 'kind': 'fixed', 'values': 'abc'}], schedule='overlay', operation='add', key_length=3)

def test_fixed_stream_values_are_not_modulo_wrapped():
    with pytest.raises(ValueError, match='outside 0..28'):
        _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 3}, {'name': 'B', 'kind': 'fixed', 'values': [1, 29]}], schedule='overlay', operation='add', key_length=3, alphabet_size=29)

def test_alternating_schedule_roundtrip():
    c = _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 2}, {'name': 'B', 'kind': 'periodic', 'period': 3}], schedule='alternating', alternating_start='A', operation='add', key_length=5)
    pt = np.arange(17, dtype=int) * 4 % 29
    key = np.array([1, 2, 10, 11, 12], dtype=int)
    ct = _roundtrip(c, key, pt)
    assert int(ct[0]) == (int(pt[0]) + 1) % 29
    assert int(ct[1]) == (int(pt[1]) + 11) % 29

def test_mask_schedule_roundtrip():
    mask = [1, 1, 2, 2, 3, 3, 1, 2]
    c = _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 2}, {'name': 'B', 'kind': 'periodic', 'period': 3}], schedule='mask', mask=mask, operation='add', key_length=5)
    pt = np.arange(len(mask), dtype=int) % 29
    key = np.array([1, 2, 7, 8, 9], dtype=int)
    _roundtrip(c, key, pt)

def test_xor_mod_requires_degeneracy_allow_and_candidates_include_true_plaintext():
    with pytest.raises(ValueError, match="requires degeneracy='allow'"):
        _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 3}, {'name': 'B', 'kind': 'primes'}], schedule='overlay', operation='xor_mod', key_length=3)
    c = _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 3}, {'name': 'B', 'kind': 'primes'}], schedule='overlay', operation='xor_mod', degeneracy='allow', key_length=3)
    pt = np.arange(30, dtype=int) % 29
    key = np.array([1, 2, 3], dtype=int)
    ct = c.encrypt(plaintext=pt, key=key)[0]
    cands, lens, invalid = c.candidates_for(ct, key, limit=29)
    assert not invalid.any()
    for i, p in enumerate(pt.tolist()):
        assert p in cands[0, i, :int(lens[0, i])].tolist()

def test_bad_configs_rejected():
    with pytest.raises(ValueError, match='period'):
        _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 0}, {'name': 'B', 'kind': 'periodic', 'period': 5}], key_length=5)
    with pytest.raises(ValueError, match='key_length'):
        _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 2}, {'name': 'B', 'kind': 'periodic', 'period': 3}], key_length=4)
    with pytest.raises(ValueError, match="advance='core'"):
        _cipher(name='scheduled_stream_lookup', streams=[{'name': 'A', 'kind': 'periodic', 'period': 3, 'advance': 'raw'}], key_length=3)
