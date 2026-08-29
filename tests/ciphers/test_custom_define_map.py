"""Typed experimental map and tutorial-support boundaries."""

from __future__ import annotations

import inspect

import pytest

from rune_decrypter_prime.api import decrypt, encrypt, experimental
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
from rune_decrypter_prime.core.config.cipher import materialize_cipher_config
from rune_decrypter_prime.core.engine.builders import build_cipher
from rune_decrypter_prime.core.types import ComputeDevice, TextDirection
from tutorials.v1.data.two_period_cribs_demo import build_demo_fixture

pytestmark = pytest.mark.tier_a


def test_two_input_map_uses_typed_experimental_contract() -> None:
    spec = experimental.define_cipher_map(
        lambda plaintext, key: (plaintext + key) % 29,
        alphabet_size=29,
        name="addition",
    )

    assert isinstance(spec, CipherSpec)
    assert spec.parameters["definition_kind"] == "function"
    assert "function" not in spec.parameters
    ciphertext = encrypt((0, 1, 2, 3), cipher=spec, key=(7,))
    assert ciphertext == (7, 8, 9, 10)
    assert decrypt(ciphertext, cipher=spec, key=(7,)) == (0, 1, 2, 3)


def test_lookup_map_reuses_generic_runtime() -> None:
    table = tuple(
        tuple((plaintext + key) % 5 for key in range(5))
        for plaintext in range(5)
    )
    spec = experimental.define_cipher_lookup(table, alphabet_size=5)
    config = materialize_cipher_config(
        cipher=spec,
        key_space=KeySpec.repeating(length=2),
        ciphertext=(0, 1, 2, 3),
        word_lengths=None,
        text_direction=TextDirection.RIGHT_TO_LEFT,
        compute_device=ComputeDevice.CPU,
    )

    assert config.name == "generic_map"
    assert type(build_cipher(config)).__name__ == "GenericMapCipher"


def test_experimental_signatures_and_enums_are_exact() -> None:
    parameters = inspect.signature(experimental.define_cipher_map).parameters
    assert parameters["function"].kind is inspect.Parameter.POSITIONAL_ONLY
    assert "per_position_limit" in parameters
    assert "per_pos_limit" not in parameters
    assert set(experimental.DegeneracyPolicy) == {
        experimental.DegeneracyPolicy.ALLOW,
        experimental.DegeneracyPolicy.FORBID,
    }
    assert set(experimental.ResolverMode) == {
        experimental.ResolverMode.EXPAND_BEAM,
        experimental.ResolverMode.FIRST,
    }


def test_three_input_and_raw_enum_options_are_rejected() -> None:
    with pytest.raises(TypeError, match="exactly two"):
        experimental.define_cipher_map(lambda plaintext, first, second: plaintext)
    with pytest.raises(TypeError, match="DegeneracyPolicy"):
        experimental.define_cipher_map(
            lambda plaintext, key: plaintext,
            degeneracy="allow",
        )


def test_interruptor_fixture_is_deterministic_and_keeps_semantic_key() -> None:
    cipher = CipherSpec.two_period_vigenere(first_period=13, second_period=31)

    first = build_demo_fixture(cipher, interruptors=(3, 9))
    second = build_demo_fixture(cipher, interruptors=(3, 9))

    assert first == second
    assert len(first.ciphertext) == 308
    assert len(first.reference_key) == 44
    assert first.reference_interruptors == (3, 9)
