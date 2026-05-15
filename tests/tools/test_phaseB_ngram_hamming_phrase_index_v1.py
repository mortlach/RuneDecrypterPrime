from __future__ import annotations

import gzip
import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_phrase_index_v1 as builder,
)


def test_phrase_identity_uses_word_boundaries() -> None:
    left = builder.PhraseEntry(
        phrase_id="",
        direction="fwd",
        dictionary_cut="normal",
        ngram_order=2,
        word_token_ids=((12, 3), (4,)),
        rune_token_ids=(12, 3, 4),
    )
    right = builder.PhraseEntry(
        phrase_id="",
        direction="fwd",
        dictionary_cut="normal",
        ngram_order=2,
        word_token_ids=((12,), (3, 4)),
        rune_token_ids=(12, 3, 4),
    )

    assert builder.phrase_identity(left) != builder.phrase_identity(right)


def test_build_phrase_index_manifest_passes() -> None:
    manifest = builder.build_phrase_index()

    assert manifest["status"] == "pass"
    assert manifest["phrase_entry_count"] > 0
    assert "canonical_word_token_ids" in manifest["phrase_identity_key"]
    assert manifest["profile_eligibility_summary_path"].endswith("phrase_profile_eligibility_summary.csv")
    assert any(row["profile_id"] == "P1_word_analogue_len7_hd2" for row in manifest["profile_eligibility_summary"])
    assert manifest["core_fwd_invalid_row_count"] == 0
    assert manifest["invalid_rows_block_core_fwd"] is True


def test_phrase_index_jsonl_contains_word_structured_entries() -> None:
    manifest = builder.build_phrase_index()
    path = builder.REPO_ROOT / manifest["phrase_index_path"]

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        first = json.loads(next(handle))

    assert first["word_token_ids"]
    assert first["rune_token_ids"]
    assert first["word_lengths"] == [len(word) for word in first["word_token_ids"]]
    assert "sum_count" in first
    assert "max_count" in first
    assert "max_log_count" in first
