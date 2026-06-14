from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from rune_decrypter_prime.ciphers.scheduled_stream_lookup_cipher import (
    ScheduledStreamLookupCipher,
    validate_operation_degeneracy,
    validate_schedule_for_streams,
    validate_streams_v1,
)

pytestmark = pytest.mark.tier_a


def _periodic_stream(period: int = 3) -> dict[str, object]:
    return {"name": "A", "kind": "periodic", "period": period}


def test_xor_and_lookup_require_explicit_degeneracy_allow() -> None:
    with pytest.raises(ValueError, match="requires degeneracy='allow'"):
        validate_operation_degeneracy("xor_mod", "forbid")

    with pytest.raises(ValueError, match="requires degeneracy='allow'"):
        validate_operation_degeneracy("lookup", "forbid")

    assert validate_operation_degeneracy("xor_mod", "allow") == ("xor_mod", "allow")
    assert validate_operation_degeneracy("lookup", "allow") == ("lookup", "allow")


def test_fixed_stream_rejects_text_values_instead_of_splitting_characters() -> None:
    with pytest.raises(ValueError, match="not text"):
        validate_streams_v1(
            [{"name": "B", "kind": "fixed", "values": "12"}],
            alphabet_size=29,
        )


def test_fixed_stream_rejects_out_of_range_values_without_modulo() -> None:
    with pytest.raises(ValueError, match="outside 0..28"):
        validate_streams_v1(
            [{"name": "B", "kind": "fixed", "values": [0, 29]}],
            alphabet_size=29,
        )


def test_fixed_stream_accepts_numpy_integer_values() -> None:
    streams = validate_streams_v1(
        [{"name": "B", "kind": "fixed", "values": np.asarray([1, 2, 3])}],
        alphabet_size=29,
    )

    assert streams[0]["values"] == [1, 2, 3]


def test_two_stream_schedules_require_two_stream_specs() -> None:
    assert validate_schedule_for_streams("overlay", [_periodic_stream()]) == "overlay"

    with pytest.raises(ValueError, match="requires two streams"):
        validate_schedule_for_streams("alternating", [_periodic_stream()])

    with pytest.raises(ValueError, match="requires two streams"):
        validate_schedule_for_streams("ragged_overlap", [_periodic_stream()])


def test_backward_end_fixed_stream_uses_end_anchor_without_hidden_modulo() -> None:
    spec = SimpleNamespace(
        streams=[
            {
                "name": "A",
                "kind": "fixed",
                "values": [10, 11, 12],
                "direction": "backward",
                "anchor": "end",
                "repeat": False,
            }
        ],
        schedule="overlay",
        operation="add",
    )
    cfg = SimpleNamespace(
        ciphertext=[0, 0, 0],
        wli_data=[],
        key_length=0,
        name="scheduled_stream_lookup",
        spec=spec,
        alphabet_size=29,
        text_transposition="ltr",
        key_transposition="ltr",
        initial_text_permutation_indices=None,
        device="cpu",
    )
    cipher = ScheduledStreamLookupCipher(cfg)
    keys = np.empty((1, 0), dtype=int)

    ciphertext = cipher._core_encrypt_batch(np.asarray([0, 0, 0], dtype=int), keys)
    plaintext = cipher._core_decrypt_batch(ciphertext[0], keys)

    assert ciphertext.tolist() == [[12, 11, 10]]
    assert plaintext.tolist() == [[0, 0, 0]]
