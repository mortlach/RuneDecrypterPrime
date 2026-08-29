"""Strict static examples for the canonical V1 public surface."""

from __future__ import annotations

from typing import assert_type

from rdp import api


def canonical_public_examples() -> None:
    cipher = api.CipherSpec.vigenere(alphabet_size=29)
    key_space = api.KeySpec.repeating(length=3)
    solver = api.SolverSpec.beam_search(width=8, rounds=2, seed=7)
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
        cipher=cipher,
        key_space=key_space,
        solver=solver,
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )

    result = api.run(request)
    assert_type(result, api.RunResult)

    key: api.ConcreteKey = (3, 1, 4)
    ciphertext = api.encrypt((0, 1, 2, 3), cipher=cipher, key=key)
    assert_type(ciphertext, api.RuneIndices)
    plaintext = api.decrypt(ciphertext, cipher=cipher, key=key)
    assert_type(plaintext, api.RuneIndices)


def experimental_extension_example() -> None:
    def add_modulo(plaintext: int, key: int) -> int:
        return (plaintext + key) % 29

    cipher = api.experimental.define_cipher_map(
        add_modulo,
        name="example_addition",
        alphabet_size=29,
    )
    assert_type(cipher, api.CipherSpec)
