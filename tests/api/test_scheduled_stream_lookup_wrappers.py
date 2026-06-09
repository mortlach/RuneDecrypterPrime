from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api.wrappers.by_name import by_name
from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
from rune_decrypter_prime.ciphers import registry as cipher_registry
from rune_decrypter_prime.ciphers.scheduled_stream_lookup_cipher import solved_key_length_for_streams
from rune_decrypter_prime.core.types import Device, Direction, KeyOpsFamily


def _cfg(spec, key):
    return build_cipher_config(
        cipher=spec,
        key=key,
        ciphertext=np.arange(8, dtype=np.uint8),
        wli=None,
        device=Device.CPU,
        encoding_dir=Direction.LTR,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )


def test_engine_registry_exposes_only_real_core_cipher_name():
    assert cipher_registry.has("scheduled_stream_lookup")
    assert not cipher_registry.has("two_period_vigenere")
    assert not cipher_registry.has("two_period_arithmetic")
    assert not cipher_registry.has("periodic_plus_primes")
    assert not cipher_registry.has("periodic_plus_sequence")


def test_shared_key_length_contract():
    assert solved_key_length_for_streams(
        [
            {"name": "A", "kind": "periodic", "period": 13},
            {"name": "B", "kind": "periodic", "period": 31},
        ]
    ) == 44
    assert solved_key_length_for_streams(
        [
            {"name": "A", "kind": "periodic", "period": 13},
            {"name": "B", "kind": "primes"},
        ]
    ) == 13
    assert solved_key_length_for_streams(
        [
            {"name": "A", "kind": "periodic", "period": 13},
            {"name": "S", "kind": "sequence", "values": [1, 2, 3]},
        ]
    ) == 13


def test_generic_scheduled_stream_wrapper_key_length_and_metadata():
    spec, key = by_name.cipher_with_key(
        "scheduled_stream_lookup",
        streams=[
            {"name": "A", "kind": "periodic", "period": 5},
            {"name": "S", "kind": "sequence", "values": [3, 4, 5]},
        ],
        operation="add",
        default_key=True,
    )
    cfg = _cfg(spec, key)
    assert cfg.name == "scheduled_stream_lookup"
    assert cfg.key_length == 5
    assert cfg.keyops_family == KeyOpsFamily.VECTOR
    assert cfg.keyops_hints == {"mod": 29}
    assert cfg.streams[1]["kind"] == "sequence"


def test_periodic_plus_sequence_alias_key_length():
    spec, key = by_name.cipher_with_key(
        "periodic_plus_sequence",
        period=13,
        sequence=[1, 2, 3, 4],
        default_key=True,
    )
    cfg = _cfg(spec, key)
    assert cfg.key_length == 13
    assert cfg.streams[1]["kind"] == "sequence"


def test_two_period_vigenere_wrapper_key_length():
    spec, key = by_name.cipher_with_key("two_period_vigenere", period_a=13, period_b=31, default_key=True)
    cfg = _cfg(spec, key)
    assert cfg.name == "scheduled_stream_lookup"
    assert cfg.key_length == 44


def test_periodic_plus_primes_wrapper_key_length():
    spec, key = by_name.cipher_with_key("periodic_plus_primes", period=13, default_key=True)
    cfg = _cfg(spec, key)
    assert cfg.key_length == 13
    assert cfg.streams[1]["kind"] == "primes"


def test_explicit_scheduled_stream_wrapper_preserves_degeneracy_and_limits():
    spec, key = by_name.cipher_with_key(
        "scheduled_stream_lookup",
        streams=[
            {"name": "A", "kind": "periodic", "period": 5},
            {"name": "B", "kind": "primes"},
        ],
        operation="xor_mod",
        degeneracy="allow",
        per_pos_limit=17,
        resolver_limit=1234,
        default_key=True,
    )
    cfg = _cfg(spec, key)
    assert cfg.key_length == 5
    assert cfg.operation == "xor_mod"
    assert cfg.degeneracy == "allow"
    assert cfg.per_pos_limit == 17
    assert cfg.resolver_limit == 1234


def test_two_period_arithmetic_preserves_operation():
    spec, key = by_name.cipher_with_key(
        "two_period_arithmetic",
        period_a=7,
        period_b=11,
        operation="add_sub",
        default_key=True,
    )
    cfg = _cfg(spec, key)
    assert cfg.key_length == 18
    assert cfg.operation == "add_sub"
    assert spec.name == "scheduled_stream_lookup"


def test_bad_stream_specs_rejected_by_config_builder():
    spec, key = by_name.cipher_with_key(
        "scheduled_stream_lookup",
        streams=[
            {"name": "A", "kind": "periodic", "period": 2},
            {"name": "B", "kind": "periodic", "period": 3},
            {"name": "C", "kind": "periodic", "period": 5},
        ],
        default_key=True,
    )
    with pytest.raises(ValueError, match="one or two streams"):
        _cfg(spec, key)

    spec, key = by_name.cipher_with_key(
        "scheduled_stream_lookup",
        streams=[{"name": "A", "kind": "derived", "period": 2}],
        default_key=True,
    )
    with pytest.raises(ValueError, match="unknown stream kind"):
        _cfg(spec, key)
