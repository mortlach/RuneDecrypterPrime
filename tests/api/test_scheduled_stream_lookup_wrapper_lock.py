from __future__ import annotations

from rune_decrypter_prime.api.wrappers.by_name import by_name
from rune_decrypter_prime.ciphers import registry as cipher_registry


def test_scheduled_stream_aliases_remain_api_wrappers_not_core_cipher_names() -> None:
    assert cipher_registry.has("scheduled_stream_lookup")
    for alias in (
        "two_period_vigenere",
        "two_period_arithmetic",
        "periodic_plus_primes",
        "periodic_plus_sequence",
    ):
        assert not cipher_registry.has(alias)


def test_periodic_plus_primes_alias_maps_to_canonical_engine() -> None:
    spec, key = by_name.cipher_with_key("periodic_plus_primes", period=13, default_key=True)

    assert spec.name == "scheduled_stream_lookup"
    assert key.period_hint() == 13
    assert spec.extra["streams"][1]["kind"] == "primes"


def test_two_period_vigenere_alias_maps_to_canonical_engine() -> None:
    spec, key = by_name.cipher_with_key("two_period_vigenere", period_a=13, period_b=31, default_key=True)

    assert spec.name == "scheduled_stream_lookup"
    assert key.period_hint() == 44
