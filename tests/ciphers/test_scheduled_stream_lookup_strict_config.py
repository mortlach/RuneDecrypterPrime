from __future__ import annotations

import pytest

from rune_decrypter_prime.ciphers.scheduled_stream_lookup_cipher import (
    config_int,
    validate_operation_degeneracy,
    validate_schedule_for_streams,
    validate_streams_v1,
)


def test_rejects_bad_stream_kind_direction_anchor_and_advance() -> None:
    with pytest.raises(ValueError, match="unknown stream kind"):
        validate_streams_v1([{"name": "A", "kind": "banana"}], alphabet_size=29)

    with pytest.raises(ValueError, match="stream direction"):
        validate_streams_v1([{"name": "A", "kind": "periodic", "period": 3, "direction": "sideways"}])

    with pytest.raises(ValueError, match="stream anchor"):
        validate_streams_v1([{"name": "A", "kind": "periodic", "period": 3, "anchor": "middle"}])

    with pytest.raises(ValueError, match="advance='core'"):
        validate_streams_v1([{"name": "A", "kind": "periodic", "period": 3, "advance": "raw"}])


def test_rejects_bad_schedule_and_operation_names() -> None:
    streams = [{"name": "A", "kind": "periodic", "period": 3}]

    with pytest.raises(ValueError, match="unknown scheduled_stream_lookup schedule"):
        validate_schedule_for_streams("diagonal", streams)

    with pytest.raises(ValueError, match="unknown scheduled_stream_lookup operation"):
        validate_operation_degeneracy("multiply", "forbid")


def test_rejects_lossy_integer_coercion() -> None:
    with pytest.raises(ValueError, match="not bool"):
        config_int(True, "period")

    with pytest.raises(ValueError, match="must be an integer"):
        config_int(3.7, "period")

    with pytest.raises(ValueError, match="must be an integer"):
        config_int("", "period")


def test_fixed_stream_values_are_integer_symbols_not_text_or_mod_wrapped() -> None:
    with pytest.raises(ValueError, match="not text"):
        validate_streams_v1([{"name": "B", "kind": "fixed", "values": "abc"}], alphabet_size=29)

    with pytest.raises(ValueError, match="outside 0..28"):
        validate_streams_v1([{"name": "B", "kind": "fixed", "values": [0, 29]}], alphabet_size=29)
