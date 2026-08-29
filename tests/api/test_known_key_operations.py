from __future__ import annotations

import importlib

import pytest

from rdp.api import CipherSpec, decrypt, encrypt
from rune_decrypter_prime.core.component_contracts import (
    InvalidConcreteKeyError,
    NonInvertibleCipherError,
)


PLAINTEXT = tuple(range(12))


@pytest.mark.parametrize(
    ("cipher", "key"),
    (
        (CipherSpec.vigenere(), (1, 2, 3)),
        (CipherSpec.autokey(), (1, 2, 3)),
        (CipherSpec.columnar(columns=3), (2, 0, 1)),
        (CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8), (7,)),
        (CipherSpec.substitution(), tuple(reversed(range(29)))),
        (
            CipherSpec.periodic_substitution(period=2),
            tuple(range(29)) + tuple(reversed(range(29))),
        ),
        (
            CipherSpec.periodic_columnar(period=2, columns=3),
            tuple(range(29)) + tuple(reversed(range(29))) + (2, 0, 1),
        ),
        (
            CipherSpec.two_period_vigenere(first_period=2, second_period=3),
            (1, 2, 3, 4, 5),
        ),
        (CipherSpec.periodic_with_fixed_stream((1, 2, 3), period=2), (1, 2)),
        (CipherSpec.periodic_with_prime_stream(period=2), (1, 2)),
        (
            CipherSpec.two_period_streams(first_period=2, second_period=3),
            (1, 2, 3, 4, 5),
        ),
    ),
)
def test_all_supported_cipher_families_round_trip(
    cipher: CipherSpec,
    key: tuple[int, ...],
) -> None:
    ciphertext = encrypt(PLAINTEXT, cipher=cipher, key=key)

    assert type(ciphertext) is tuple
    assert decrypt(ciphertext, cipher=cipher, key=key) == PLAINTEXT


def test_rail_fence_key_is_a_semantic_count() -> None:
    ciphertext = encrypt(
        PLAINTEXT,
        cipher=CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8),
        key=(7,),
    )

    assert ciphertext == (0, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6)


def test_public_keys_are_strict_concrete_keys() -> None:
    with pytest.raises(TypeError):
        encrypt(PLAINTEXT, cipher=CipherSpec.vigenere(), key=[1, 2, 3])
    with pytest.raises(InvalidConcreteKeyError):
        encrypt(PLAINTEXT, cipher=CipherSpec.columnar(columns=3), key=(1,))


def test_known_key_operations_do_not_construct_solver_or_scorer(monkeypatch) -> None:
    module = importlib.import_module("rdp.api.known_key")
    real_builder = module.build_cipher
    calls: list[str] = []

    def capture_builder(config):
        calls.append(config.name)
        return real_builder(config)

    monkeypatch.setattr(module, "build_cipher", capture_builder)
    encrypt(PLAINTEXT, cipher=CipherSpec.vigenere(), key=(1, 2, 3))

    assert calls == ["vigenere"]
    assert "solver" not in module.__dict__
    assert "scorer" not in module.__dict__


def test_missing_runtime_operation_raises_typed_error(monkeypatch) -> None:
    module = importlib.import_module("rdp.api.known_key")
    monkeypatch.setattr(module, "build_cipher", lambda _config: object())

    with pytest.raises(NonInvertibleCipherError) as exc_info:
        encrypt(PLAINTEXT, cipher=CipherSpec.vigenere(), key=(1, 2, 3))

    assert exc_info.value.issues[0].code == "cipher_operation_unavailable"
