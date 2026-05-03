from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    export_historical_partial_text_review_v1 as hist,
)


def test_rune_token_sequence_validation_requires_base29_numbers() -> None:
    assert hist.is_rune_token_sequence([0, 1, 28])
    assert hist.is_rune_token_sequence(["0", "12", "28"])

    assert not hist.is_rune_token_sequence([])
    assert not hist.is_rune_token_sequence([0, 29])
    assert not hist.is_rune_token_sequence([-1, 0])
    assert not hist.is_rune_token_sequence([True, 1])
    assert not hist.is_rune_token_sequence(["th", 1])


def test_token_text_and_hash_are_numeric_only_and_stable() -> None:
    tokens = [28, 0, 4, 12]

    assert hist.token_sequence_text(tokens) == "28 0 4 12"
    assert hist.partial_text_hash(tokens) == hist.partial_text_hash(["28", "0", "4", "12"])


def test_walk_separates_candidate_partial_from_truth_target() -> None:
    record = {
        "fixture_seed": 411,
        "search_seed": 0,
        "target_plaintext_idx": [1, 2, 3],
        "candidates": [
            {
                "candidate_hash": "abc",
                "final_plaintext_idx": [4, 5, 6],
                "score": -10.0,
            },
            {
                "candidate_hash": "def",
                "plaintext_idx": [7, 8, 9],
                "truth_text": "not-rune-material",
            },
        ],
    }

    fields = list(
        hist._walk_plaintext_fields(
            record,
            path_parts=["root"],
            parent=record,
            root=record,
        )
    )

    field_names = [field_name for _, field_name, _, _ in fields]
    assert field_names.count("target_plaintext_idx") == 1
    assert field_names.count("final_plaintext_idx") == 1
    assert field_names.count("plaintext_idx") == 1

    partial_rows = []
    target_rows = []
    for field_path, field_name, tokens, parent in fields:
        row = {
            "partial_text_hash": hist.partial_text_hash(tokens),
            "token_count": len(tokens),
            "token_sequence_text": hist.token_sequence_text(tokens),
            "data_file": "synthetic.json",
            "field_path": field_path,
            "field_name": field_name,
            "candidate_hash": str(parent.get("candidate_hash", "")),
            "source": "",
            "bundle_path": "",
            "fixture_seed": "411",
            "search_seed": "0",
            "score": parent.get("score", ""),
            "match_ratio": "",
        }
        if field_name in hist.TRUTH_TARGET_KEYS:
            target_rows.append(row)
        else:
            partial_rows.append(row)

    unique_rows = hist.build_unique_rows(partial_rows)
    summary = hist.build_summary(
        partial_rows=partial_rows,
        target_rows=target_rows,
        unique_rows=unique_rows,
        inventory_rows=[],
    )

    assert summary["partial_text_occurrence_count"] == 2
    assert summary["unique_partial_text_count"] == 2
    assert summary["truth_target_occurrence_count"] == 1
    assert summary["unique_truth_target_count"] == 1
    assert {row["token_sequence_text"] for row in unique_rows} == {"4 5 6", "7 8 9"}


def test_unique_rows_cluster_by_numeric_token_hash() -> None:
    text_hash = hist.partial_text_hash([1, 2, 3])
    rows = [
        {
            "partial_text_hash": text_hash,
            "token_count": 3,
            "token_sequence_text": "1 2 3",
            "data_file": "a.json",
            "candidate_hash": "one",
            "source": "alpha",
            "bundle_path": "bundle-a",
            "fixture_seed": "411",
            "search_seed": "0",
            "score": -3.0,
            "match_ratio": 0.1,
        },
        {
            "partial_text_hash": text_hash,
            "token_count": 3,
            "token_sequence_text": "1 2 3",
            "data_file": "b.json",
            "candidate_hash": "two",
            "source": "beta",
            "bundle_path": "bundle-b",
            "fixture_seed": "7001",
            "search_seed": "1",
            "score": -2.0,
            "match_ratio": 0.2,
        },
    ]

    unique_rows = hist.build_unique_rows(rows)

    assert len(unique_rows) == 1
    assert unique_rows[0]["occurrence_count"] == 2
    assert unique_rows[0]["candidate_hash_count"] == 2
    assert unique_rows[0]["fixture_seed_count"] == 2
    assert unique_rows[0]["best_score"] == -2.0
    assert unique_rows[0]["best_match_ratio"] == 0.2
