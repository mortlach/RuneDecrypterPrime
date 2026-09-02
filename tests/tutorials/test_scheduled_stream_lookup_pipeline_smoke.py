from __future__ import annotations

import pytest

from rdp import api
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.scheduled_stream_lookup_tutorial_utils import (
    build_ciphertext,
    concat_keys,
    encode_plaintext,
    key_period13,
    key_period31,
    mask_from_segments,
    sample_sequence,
)

pytestmark = pytest.mark.tier_a


@pytest.mark.parametrize(
    ("cipher", "key_space", "key"),
    [
        (
            api.CipherSpec.periodic_with_fixed_stream(sample_sequence(64), period=13),
            api.KeySpec.repeating(length=13),
            tuple(key_period13()),
        ),
        (
            api.CipherSpec.periodic_with_prime_stream(period=13),
            api.KeySpec.repeating(length=13),
            tuple(key_period13()),
        ),
        (
            api.CipherSpec.two_period_vigenere(first_period=13, second_period=31),
            api.KeySpec.repeating(length=44),
            tuple(concat_keys(key_period13(), key_period31())),
        ),
        (
            api.CipherSpec.two_period_streams(first_period=13, second_period=31),
            api.KeySpec.repeating(length=44),
            tuple(concat_keys(key_period13(), key_period31())),
        ),
    ],
)
def test_typed_scheduled_tutorial_fixture_round_trip(
    cipher: api.CipherSpec,
    key_space: api.KeySpec,
    key: tuple[int, ...],
) -> None:
    _, _, plaintext, _, _, ciphertext, _, returned_key = build_ciphertext(
        plaintext=plaintext_english_string,
        cipher_spec=cipher,
        key_spec=key_space,
        key_values=key,
        direction=api.TextDirection.RIGHT_TO_LEFT,
    )

    assert returned_key == key
    assert api.decrypt(tuple(ciphertext), cipher=cipher, key=key) == tuple(plaintext)


def test_typed_mask_schedule_fixture_round_trip() -> None:
    plaintext, _, _ = encode_plaintext(plaintext_english_string)
    mask = mask_from_segments(
        len(plaintext),
        (("A", 0, 120), ("B", 120, 240), ("A", 240, None)),
    )
    cipher = api.CipherSpec.two_period_vigenere(
        first_period=13,
        second_period=31,
        schedule=api.advanced.ScheduledStreamSchedule.MASK,
        mask=mask,
    )
    key_space = api.KeySpec.repeating(length=44)
    key = tuple(concat_keys(key_period13(), key_period31()))
    _, _, expected, _, _, ciphertext, _, _ = build_ciphertext(
        plaintext=plaintext_english_string,
        cipher_spec=cipher,
        key_spec=key_space,
        key_values=key,
        direction=api.TextDirection.RIGHT_TO_LEFT,
    )

    assert api.decrypt(tuple(ciphertext), cipher=cipher, key=key) == tuple(expected)
