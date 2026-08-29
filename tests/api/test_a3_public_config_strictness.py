from __future__ import annotations
from rdp import api
import pytest

def _map2(plaintext: int, key: int) -> int:
    return (plaintext + key) % 29

def test_typed_cipher_constructors_and_extension_contract() -> None:
    assert api.CipherSpec.vigenere().kind is api.advanced.CipherKind.VIGENERE
    assert api.CipherSpec.columnar(columns=4).kind is api.advanced.CipherKind.COLUMNAR
    custom = api.experimental.define_cipher_map(_map2, name="demo", alphabet_size=29)
    assert isinstance(custom, api.CipherSpec)

def test_typed_cipher_constructors_reject_invalid_dimensions() -> None:
    with pytest.raises((TypeError, ValueError)):
        api.CipherSpec.columnar(columns=0)
    with pytest.raises((TypeError, ValueError)):
        api.CipherSpec.rail_fence(minimum_rails=5, maximum_rails=3)
    with pytest.raises((TypeError, ValueError)):
        api.CipherSpec.periodic_substitution(period=0)

def test_final_key_space_constructors_are_complete_and_strict() -> None:
    assert api.KeySpec.repeating(length=4).kind is api.advanced.KeyKind.REPEATING
    assert api.KeySpec.permutation(length=4).kind is api.advanced.KeyKind.PERMUTATION
    assert api.KeySpec.scalar(minimum=0, maximum=8).kind is api.advanced.KeyKind.SCALAR
    with pytest.raises((TypeError, ValueError)):
        api.KeySpec.repeating_range(minimum_length=5, maximum_length=3)

def test_secondary_cipher_parser_is_only_for_serialized_configuration() -> None:
    parsed = api.CipherSpec.from_name("vigenere", parameters={"alphabet_size": 29})
    assert parsed == api.CipherSpec.vigenere(alphabet_size=29)
    with pytest.raises(api.advanced.UnknownComponentError):
        api.CipherSpec.from_name("hill", parameters={})

def test_runspec_rejects_cipher_key_dimension_conflicts() -> None:
    with pytest.raises(api.advanced.CipherKeyMismatchError):
        api.RunSpec(
            problem_input=api.RuneIndexInput(indices=(0, 1, 2)),
            cipher=api.CipherSpec.periodic_substitution(period=3),
            key_space=api.KeySpec.repeating(length=2),
            solver=api.SolverSpec.beam_search(width=2, rounds=1),
        )
