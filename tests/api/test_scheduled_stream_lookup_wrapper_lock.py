from __future__ import annotations
from rdp import api
from rune_decrypter_prime.ciphers import cipher_runtime_registry

def test_scheduled_public_presets_share_one_runtime_identity() -> None:
    assert cipher_runtime_registry.has('scheduled_stream_lookup')
    for alias in ('two_period_vigenere', 'two_period_arithmetic', 'periodic_plus_primes', 'periodic_plus_sequence'):
        assert not cipher_runtime_registry.has(alias)

def test_periodic_with_prime_stream_owns_its_declared_dimensions() -> None:
    spec = api.CipherSpec.periodic_with_prime_stream(period=13, prime_offset=2)
    key = api.KeySpec.repeating(length=13)

    assert spec.kind is api.advanced.CipherKind.PERIODIC_WITH_PRIME_STREAM
    assert spec.parameters == {'period': 13, 'prime_offset': 2, 'alphabet_size': 29}
    assert key.parameters == {'length': 13}

def test_two_period_vigenere_owns_both_periods() -> None:
    spec = api.CipherSpec.two_period_vigenere(first_period=13, second_period=31)
    key = api.KeySpec.repeating(length=44)

    assert spec.kind is api.advanced.CipherKind.TWO_PERIOD_VIGENERE
    assert spec.parameters['first_period'] == 13
    assert spec.parameters['second_period'] == 31
    assert key.parameters == {'length': 44}
