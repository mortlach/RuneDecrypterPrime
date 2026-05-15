from __future__ import annotations

import json

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    audit_phaseB_ngram_hamming_damage_source_v1 as damage_audit,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_phaseB_ngram_hamming_assets_v1 as asset_validation,
)


def test_damage_source_manifest_is_required_and_verified() -> None:
    manifest = damage_audit.build_damage_manifest()

    assert manifest["status"] == "pass"
    assert manifest["damage_levels_verified"] is True
    assert manifest["damage_models_verified"] is True
    assert manifest["no_new_damage_model_required"] is True
    for level in ("0.20", "0.30", "0.40", "0.50"):
        assert level in manifest["required_damage_levels"]
    assert {row["damage_model"] for row in manifest["damage_models"]} == set(damage_audit.REQUIRED_DAMAGE_MODELS)


def test_damage_source_records_seed_and_chunking_policy() -> None:
    manifest = damage_audit.build_damage_manifest()

    assert manifest["global_seed"] == 20260507
    assert manifest["seed_function"]["name"] == "_stable_int_seed"
    assert manifest["chunking_policy"]["damage_applied_after_chunking"] is True
    assert manifest["chunking_policy"]["chunk_max_tokens"] == 500
    assert manifest["chunking_policy"]["chunking_function"] == "source_word_chunks_for_wli"
    assert manifest["same_damage_generator_verified"] is True
    assert manifest["same_damaged_streams_shared_with_word_hamming"] == "unverified"
    assert manifest["damage_stream_fingerprint_required_before_exact_stream_reuse_claim"] is True


def test_word_token_ids_parses_to_canonical_nested_tuple() -> None:
    parsed = asset_validation.parse_word_token_ids("[[12, 3], [4]]")

    assert parsed == ((12, 3), (4,))


def test_word_token_ids_rejects_non_integer_tokens() -> None:
    with pytest.raises(ValueError, match="not an integer"):
        asset_validation.parse_word_token_ids('[[12, "3"], [4]]')
    with pytest.raises(ValueError, match="not an integer"):
        asset_validation.parse_word_token_ids("[[12, 3.0], [4]]")


def test_word_token_ids_flatten_matches_rune_token_ids() -> None:
    row = {
        "n": "2",
        "dictionary_cut": "normal",
        "encoding_direction": "fwd",
        "rune_token_ids": "[12, 3, 4]",
        "word_token_ids": "[[12, 3], [4]]",
        "rune_lengths": "[2, 1]",
    }

    word_token_ids, rune_token_ids = asset_validation.validate_asset_row(
        row,
        expected_cut="normal",
        expected_direction="fwd",
        expected_order=2,
    )

    assert word_token_ids == ((12, 3), (4,))
    assert rune_token_ids == (12, 3, 4)


def test_same_joined_tokens_different_word_boundaries_do_not_collapse() -> None:
    left = asset_validation.parse_word_token_ids("[[12, 3], [4]]")
    right = asset_validation.parse_word_token_ids("[[12], [3, 4]]")

    assert asset_validation.flatten(left) == asset_validation.flatten(right)
    assert left != right
    assert len({left, right}) == 2


def test_asset_row_rejects_boundary_mismatch() -> None:
    row = {
        "n": "2",
        "dictionary_cut": "normal",
        "encoding_direction": "fwd",
        "rune_token_ids": "[12, 3, 4]",
        "word_token_ids": "[[12, 3], [4]]",
        "rune_lengths": "[1, 2]",
    }

    with pytest.raises(ValueError, match="lengths"):
        asset_validation.validate_asset_row(
            row,
            expected_cut="normal",
            expected_direction="fwd",
            expected_order=2,
        )


def test_asset_row_rejects_non_integer_and_nonpositive_lengths() -> None:
    row = {
        "n": "2",
        "dictionary_cut": "normal",
        "encoding_direction": "fwd",
        "rune_token_ids": "[12, 3, 4]",
        "word_token_ids": "[[12, 3], [4]]",
        "rune_lengths": '[2, "1"]',
    }

    with pytest.raises(ValueError, match="not an integer"):
        asset_validation.validate_asset_row(
            row,
            expected_cut="normal",
            expected_direction="fwd",
            expected_order=2,
        )

    row["rune_lengths"] = "[2, 0]"
    with pytest.raises(ValueError, match="positive"):
        asset_validation.validate_asset_row(
            row,
            expected_cut="normal",
            expected_direction="fwd",
            expected_order=2,
        )


def test_asset_validation_manifest_records_no_rune_key_hex_scanning() -> None:
    manifest = asset_validation.validate_assets()

    assert manifest["uses_rune_key_hex_for_scanning"] is False
    assert manifest["uses_word_token_ids_for_phrase_identity"] is True
    assert manifest["core_fwd_asset_validation_pass"] is True
    assert manifest["status"] == "pass"
    assert "canonical_word_token_ids" in manifest["phrase_identity_key"]
    assert manifest["parser_contract"]["uses_eval"] is False
    assert manifest["parser_contract"]["allows_float_tokens"] is False
    assert manifest["parser_contract"]["allows_string_tokens"] is False
    assert manifest["parser_contract"]["allows_float_lengths"] is False
    assert manifest["parser_contract"]["allows_string_lengths"] is False
    assert manifest["parser_contract"]["allows_nonpositive_lengths"] is False
    assert manifest["token_bounds"]["token_min"] == 0
    assert manifest["token_bounds"]["token_max"] == 28
    assert manifest["token_bounds"]["separator_token_forbidden"] is True
    assert manifest["word_length_patterns"]
    assert manifest["token_length_quantiles"]


def test_asset_manifest_is_json_serialisable() -> None:
    manifest = asset_validation.validate_assets()

    json.dumps(manifest, sort_keys=True)
