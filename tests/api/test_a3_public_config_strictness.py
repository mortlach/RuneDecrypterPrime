from __future__ import annotations

import json

import numpy as np
import pytest

from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.api.maps_api import define_cipher
from rune_decrypter_prime.api.run_spec import NormalizedInput, RunSpec
from rune_decrypter_prime.api.wrappers.by_name import by_name, _WRAPPER_ALLOWED_FIELDS
from rune_decrypter_prime.core import solver_engine as compatibility_engine
from rune_decrypter_prime.core.engine import engine as canonical_engine
from rune_decrypter_prime.core.types import Direction, SolverName
from rune_decrypter_prime.ciphers import registry as cipher_registry
from rune_decrypter_prime.core.config import SolverConfig

pytestmark = pytest.mark.tier_a


def _map2(pt: int, key: int) -> int:
    return (pt + key) % 29


def _map3(pt: int, a: int, b: int) -> int:
    return (pt + a + b) % 29


def test_cipher_spec_direct_construction_matches_factory_validation() -> None:
    direct = CipherSpec(name="demo", kind="user_map2", function=_map2)
    built = CipherSpec.user_map2(_map2, name="demo")
    assert direct.kind == built.kind == "user_map2"
    assert direct.N == built.N == 29

    with pytest.raises(ValueError, match="unsupported CipherSpec.kind"):
        CipherSpec(name="bad", kind="mystery")
    with pytest.raises(TypeError, match="callable"):
        CipherSpec(name="bad", kind="user_map2", function=None)
    with pytest.raises(ValueError, match="requires a table"):
        CipherSpec(name="bad", kind="lookup", table=None)
    with pytest.raises(TypeError, match="integer"):
        CipherSpec.user_map2(_map2, N=29.5)
    with pytest.raises(ValueError, match="cannot define function/table"):
        CipherSpec(name="bad", kind="wrapper", wrapper_core="vigenere", function=_map2)
    with pytest.raises(ValueError, match="must have N rows"):
        CipherSpec.from_lookup([[0, 1], [1, 0]], N=29)
    with pytest.raises(ValueError, match="device"):
        CipherSpec._wrapper(name="bad", core_name="vigenere").__class__(
            name="bad", kind="wrapper", wrapper_core="vigenere", device="quantum"
        )


def test_key_spec_factory_and_direct_validation_are_consistent() -> None:
    assert KeySpec(plan="repeat", params={"len": 4}) == KeySpec.repeat(len=4)
    assert KeySpec(plan="perm", params={"len": 4}) == KeySpec.permutation(len=4)

    with pytest.raises(ValueError, match="does not accept parameter"):
        KeySpec(plan="repeat", params={"len": 4, "typo": 1})
    with pytest.raises(TypeError, match="JSON-portable"):
        KeySpec.block(size=4, pattern=object())
    with pytest.raises(ValueError, match="min <= max"):
        KeySpec.repeat(len=4).align(offset=("search", 2, -2))
    with pytest.raises(ValueError, match="tuple mode"):
        KeySpec(plan="repeat", params={"len": 4}, _align_offset=("guess", -1, 1))

    bad = [
        lambda: KeySpec.repeat(len=3.5),
        lambda: KeySpec.repeat_range(min=5, max=3),
        lambda: KeySpec.block(size=0),
        lambda: KeySpec.keystream(fn=None),
        lambda: KeySpec.matrix(n=1),
        lambda: KeySpec.scalar(max_val=0),
        lambda: KeySpec(plan="unknown", params={}),
    ]
    for make in bad:
        with pytest.raises((TypeError, ValueError)):
            make()


def test_beam_restarts_are_positive_and_canonical() -> None:
    assert SolverSpec.beam(restarts="3").params["restarts"] == 3
    with pytest.raises(ValueError, match="restarts must be greater than zero"):
        SolverSpec.beam(restarts=0)
    with pytest.raises(TypeError, match="restarts must be an integer"):
        SolverSpec.beam(restarts=True)


def test_every_key_spec_plan_emits_json_portable_telemetry() -> None:
    def stream_fn(length: int, *, offset: int = 0) -> np.ndarray:
        return np.arange(length, dtype=np.uint8) + np.uint8(offset)

    specs = [
        KeySpec.repeat(len=3),
        KeySpec.repeat_range(min=2, max=5),
        KeySpec.block(size=4, pattern=[0, 1, 0, 1]),
        KeySpec.otp(stream=[1, 2, 3]),
        KeySpec.const(value=7),
        KeySpec.keystream(fn=stream_fn, params={"offset": 2}),
        KeySpec.permutation(len=5),
        KeySpec.periodic_structured(period=3, alphabet_size=29),
        KeySpec.periodic_columnar(period=3, columns=4, alphabet_size=29),
        KeySpec.matrix2x2(A=29),
        KeySpec.matrix(n=3, A=29),
        KeySpec.affine(A=29),
        KeySpec.scalar(max_val=8),
    ]
    for spec in specs:
        payload = spec.to_telemetry()
        assert json.loads(json.dumps(payload)) == payload

    ks = specs[5].to_telemetry()
    assert "fn" not in ks
    assert ks["runtime_callable"]["qualname"].endswith("stream_fn")


def test_keystream_runtime_params_must_be_durable() -> None:
    with pytest.raises(TypeError, match="JSON-portable"):
        KeySpec.keystream(fn=lambda n: np.zeros(n, dtype=np.uint8), params={"bad": object()})


_WRAPPER_CASES = {
    "vigenere": {"key_len": 3},
    "caesar": {},
    "affine": {},
    "xor-mod": {},
    "beaufort": {},
    "variant-vigenere": {},
    "columnar": {"key_length": 4},
    "railfence": {"rails": 3},
    "autokey": {"seed_len": 3},
    "route": {"cols": 4},
    "double_transposition": {"key_len1": 3, "key_len2": 4},
    "blockperm": {"block_size": 4},
    "foursquare": {},
    "mono": {},
    "substitution": {},
    "periodic_substitution": {"period": 3},
    "periodic_columnar": {"period": 3, "columns": 4},
    "scheduled_stream_lookup": {"streams": [{"name": "A", "kind": "periodic", "period": 3}]},
    "periodic_plus_sequence": {"period": 3, "sequence": [1, 2, 3]},
    "periodic_plus_primes": {"period": 3},
    "two_period_vigenere": {"period_a": 3, "period_b": 5},
    "two_period_arithmetic": {"period_a": 3, "period_b": 5},
}


def test_every_registered_wrapper_rejects_unknown_fields() -> None:
    assert set(_WRAPPER_CASES) == set(by_name._REG)
    for name, kwargs in _WRAPPER_CASES.items():
        by_name.cipher(name, **kwargs)
        with pytest.raises(TypeError, match="does not accept option"):
            by_name.cipher(name, **kwargs, definitely_not_a_real_option=1)


def test_wrapper_alias_conflicts_fail_instead_of_being_silently_resolved() -> None:
    for name, kwargs in _WRAPPER_CASES.items():
        allowed = _WRAPPER_ALLOWED_FIELDS[name]
        if {"N", "alphabet_size"}.issubset(allowed):
            with pytest.raises(ValueError, match="N and alphabet_size"):
                by_name.cipher(name, **kwargs, N=29, alphabet_size=26)

    with pytest.raises(ValueError, match="columnar aliases"):
        by_name.cipher("columnar", key_len=4, cols=5)
    with pytest.raises(ValueError, match="periodic_columnar aliases"):
        by_name.cipher("periodic_columnar", period=3, columns=4, cols=5)
    with pytest.raises(ValueError, match="railfence fixed rails"):
        by_name.cipher("railfence", rails=3, min_rails=4)
    with pytest.raises(ValueError, match="min_rails cannot exceed"):
        by_name.cipher("railfence", min_rails=5, max_rails=3)
    with pytest.raises(ValueError, match="caesar.key_len must be 1"):
        by_name.cipher("caesar", key_len=2)


def test_wrapper_aliases_with_same_value_canonicalise() -> None:
    assert by_name.cipher("vigenere", N=29, alphabet_size=29).N == 29
    assert by_name.cipher("columnar", key_len=4, cols=4).extra["key_length"] == 4
    assert by_name.cipher("periodic_columnar", period=3, columns=4, cols=4).extra["columns"] == 4


def test_wrapper_integer_options_do_not_truncate_lossy_values() -> None:
    with pytest.raises(TypeError, match="integer"):
        by_name.cipher("vigenere", N=29.5)
    with pytest.raises(TypeError, match="integer"):
        by_name.cipher("periodic_substitution", period=3.5)
    with pytest.raises(ValueError, match="must be > 0"):
        by_name.cipher("vigenere", key_len=0)
    with pytest.raises(ValueError, match="must be >= 2"):
        by_name.cipher("railfence", min_rails=1)
    with pytest.raises(TypeError, match="default_key must be bool"):
        by_name.cipher("vigenere", default_key=1)


def test_every_registered_wrapper_resolves_to_a_registered_runtime_cipher() -> None:
    for name, kwargs in _WRAPPER_CASES.items():
        spec = by_name.cipher(name, **kwargs)
        assert callable(cipher_registry.get(spec.name)), name




def test_wrapper_canonicalisation_survives_runspec_without_option_loss() -> None:
    cipher = by_name.cipher(
        "periodic_columnar", period=3, cols=4, N=29, order="col_then_sub"
    )
    spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=[0, 1, 2, 3]),
        cipher=cipher,
        key=KeySpec.periodic_columnar(period=3, columns=4, alphabet_size=29),
        solver=SolverSpec.sa(iters=1, seed=0),
        encoding_dir=Direction.LTR,
    )
    assert spec.cipher.N == 29
    assert spec.cipher.extra["period"] == 3
    assert spec.cipher.extra["columns"] == 4
    assert spec.cipher.extra["order"] == "col_then_sub"


def test_registered_default_key_builders_do_not_use_broken_len_or_positional_calls() -> None:
    cases = [
        ("route", {"cols": 4}),
        ("blockperm", {"block_size": 4}),
        ("double_transposition", {"key_len1": 3, "key_len2": 4}),
        ("foursquare", {}),
    ]
    for name, kwargs in cases:
        _spec, key = by_name.cipher_with_key(name, default_key=True, **kwargs)
        assert key is not None


def test_define_cipher_forwards_key_len_to_named_wrapper_default_key_plan() -> None:
    spec, key = define_cipher(name="columnar", default_key=True, key_len=6)
    assert spec.extra["key_length"] == 6
    assert key == KeySpec.permutation(len=6)

    with pytest.raises(TypeError, match="integer"):
        define_cipher(name="vigenere", default_key=True, key_len=3.5)


def test_hill_is_rejected_at_the_public_v1_boundary() -> None:
    assert "hill" not in by_name._REG
    with pytest.raises(NotImplementedError, match="not a supported RDP V1"):
        by_name.cipher("hill")


def test_compatibility_solver_table_matches_canonical_supported_solver_names() -> None:
    assert set(compatibility_engine._SOLVER_TABLE) == set(canonical_engine._SOLVER_TABLE)
    assert SolverName.KAEDING in compatibility_engine._SOLVER_TABLE
    with pytest.raises(ValueError, match="solver"):
        SolverConfig(name="definitely_not_a_solver")
