from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    sweep_span_hamming_500_fingerprint_noise_word_ngram_composites_v1 as mod,
)


def test_joined_rows_adds_word_ngram_z_features() -> None:
    span_rows = [
        {"token_hash": "a", "chunk_kind": "prefix", "z_fp_selected_exact": "1", "z_span_err20": "1", "z_span_exact5": "1", "z_noise_short": "0"},
        {"token_hash": "b", "chunk_kind": "prefix", "z_fp_selected_exact": "1", "z_span_err20": "1", "z_span_exact5": "1", "z_noise_short": "0"},
    ]
    component_rows = [
        {"token_hash": "a", "word_ngram_active": "0", "word_ngram_trust_score": "0", "word_ngram_xent": "20", "word_ngram_backoff_xent": "20", "word_ngram_miss_rate": "1", "word_ngram_backoff_used_rate": "0"},
        {"token_hash": "b", "word_ngram_active": "1", "word_ngram_trust_score": "1", "word_ngram_xent": "10", "word_ngram_backoff_xent": "10", "word_ngram_miss_rate": "0", "word_ngram_backoff_used_rate": "0"},
    ]

    rows = mod._joined_rows(span_rows, component_rows)

    assert len(rows) == 2
    assert rows[0]["z_word_ngram_trust_score"] < rows[1]["z_word_ngram_trust_score"]
    assert rows[0]["z_word_ngram_xent"] > rows[1]["z_word_ngram_xent"]


def test_rules_include_word_ngram_only_and_joint_rules() -> None:
    rules = mod._rules()

    assert any(rule.rule_id.startswith("word_ngram_") for rule in rules)
    assert any("plus_word_ngram" in rule.rule_id for rule in rules)
