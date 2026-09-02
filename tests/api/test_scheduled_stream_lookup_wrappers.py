from __future__ import annotations

import pytest

from rdp import api
from rune_decrypter_prime.ciphers import cipher_runtime_registry
from rune_decrypter_prime.core.config.cipher import materialize_cipher_config
from rdp.core.types import KeyOpsFamily


def _cfg(spec: api.CipherSpec, key_space: api.KeySpec):
    return materialize_cipher_config(
        cipher=spec,
        key_space=key_space,
        ciphertext=tuple(range(8)),
        word_lengths=None,
        compute_device=api.ComputeDevice.CPU,
        text_direction=api.TextDirection.LEFT_TO_RIGHT,
    )


def test_engine_registry_exposes_only_real_runtime_identity() -> None:
    assert cipher_runtime_registry.has("scheduled_stream_lookup")
    assert not cipher_runtime_registry.has("two_period_vigenere")
    assert not cipher_runtime_registry.has("periodic_with_prime_stream")


@pytest.mark.parametrize(
    ("cipher", "key_space", "expected_length", "second_stream_kind"),
    [
        (
            api.CipherSpec.two_period_vigenere(first_period=13, second_period=31),
            api.KeySpec.repeating(length=44),
            44,
            "periodic",
        ),
        (
            api.CipherSpec.periodic_with_fixed_stream((3, 4, 5), period=13),
            api.KeySpec.repeating(length=13),
            13,
            "fixed",
        ),
        (
            api.CipherSpec.periodic_with_prime_stream(period=13, prime_offset=2),
            api.KeySpec.repeating(length=13),
            13,
            "primes",
        ),
        (
            api.CipherSpec.two_period_streams(
                first_period=7,
                second_period=11,
                operation=api.advanced.ScheduledStreamOperation.ADD_SUBTRACT,
            ),
            api.KeySpec.repeating(length=18),
            18,
            "periodic",
        ),
    ],
)
def test_scheduled_families_materialize_exact_key_binding(
    cipher: api.CipherSpec,
    key_space: api.KeySpec,
    expected_length: int,
    second_stream_kind: str,
) -> None:
    cfg = _cfg(cipher, key_space)

    assert cfg.name == "scheduled_stream_lookup"
    assert cfg.key_length == expected_length
    assert cfg.keyops_family is KeyOpsFamily.VECTOR
    assert cfg.keyops_hints == {"mod": 29}
    assert cfg.streams[1]["kind"] == second_stream_kind


def test_mask_schedule_is_preserved() -> None:
    cipher = api.CipherSpec.two_period_vigenere(
        first_period=2,
        second_period=3,
        schedule=api.advanced.ScheduledStreamSchedule.MASK,
        mask=(1, 2, 3, 1, 2, 3, 1, 2),
    )
    cfg = _cfg(cipher, api.KeySpec.repeating(length=5))

    assert cfg.mask == (1, 2, 3, 1, 2, 3, 1, 2)


def test_scheduled_key_length_conflict_is_rejected() -> None:
    cipher = api.CipherSpec.two_period_vigenere(first_period=2, second_period=3)

    with pytest.raises(api.advanced.CipherKeyMismatchError, match="length"):
        _cfg(cipher, api.KeySpec.repeating(length=4))
