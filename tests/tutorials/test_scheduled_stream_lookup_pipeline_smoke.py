from __future__ import annotations

import pytest

from rune_decrypter_prime.utils.scheduled_stream_lookup_tutorial_utils import (
    concat_keys,
    encode_plaintext,
    key_period13,
    key_period31,
    mask_from_segments,
    run_seeded_pipeline_smoke,
    sample_sequence,
)

pytestmark = pytest.mark.tier_a


def test_pipeline_smoke_generic_sequence() -> None:
    run_seeded_pipeline_smoke(
        title="PIPELINE SMOKE scheduled_stream_lookup: generic P13 plus supplied sequence",
        cipher_name="scheduled_stream_lookup",
        cipher_kwargs=dict(
            streams=[
                {"name": "A", "kind": "periodic", "period": 13},
                {"name": "S", "kind": "sequence", "values": sample_sequence(64)},
            ],
            schedule="overlay",
            operation="add",
            alphabet_size=29,
        ),
        key_values=key_period13(),
        expected_key_len=13,
    )


def test_pipeline_smoke_periodic_plus_sequence_preset() -> None:
    run_seeded_pipeline_smoke(
        title="PIPELINE SMOKE scheduled_stream_lookup: periodic_plus_sequence preset",
        cipher_name="periodic_plus_sequence",
        cipher_kwargs=dict(period=13, sequence=sample_sequence(64), alphabet_size=29),
        key_values=key_period13(),
        expected_key_len=13,
    )


def test_pipeline_smoke_periodic_plus_primes_preset() -> None:
    run_seeded_pipeline_smoke(
        title="PIPELINE SMOKE scheduled_stream_lookup: P13 plus generated primes preset",
        cipher_name="periodic_plus_primes",
        cipher_kwargs=dict(period=13, prime_offset=0, alphabet_size=29),
        key_values=key_period13(),
        expected_key_len=13,
    )


def test_pipeline_smoke_two_period_overlay_preset() -> None:
    run_seeded_pipeline_smoke(
        title="PIPELINE SMOKE scheduled_stream_lookup: overlaid P13 + P31 preset",
        cipher_name="two_period_vigenere",
        cipher_kwargs=dict(period_a=13, period_b=31, alphabet_size=29),
        key_values=concat_keys(key_period13(), key_period31()),
        expected_key_len=44,
    )


def test_pipeline_smoke_two_period_segmented_preset() -> None:
    pt_idx, _wli, _pt_runes = encode_plaintext()
    mask = mask_from_segments(len(pt_idx), [("A", 0, 120), ("B", 120, 240), ("A", 240, None)])

    run_seeded_pipeline_smoke(
        title="PIPELINE SMOKE scheduled_stream_lookup: segmented P13/P31/P13 preset",
        cipher_name="two_period_vigenere",
        cipher_kwargs=dict(
            period_a=13,
            period_b=31,
            alphabet_size=29,
            schedule="mask",
            mask=mask,
        ),
        key_values=concat_keys(key_period13(), key_period31()),
        expected_key_len=44,
    )
