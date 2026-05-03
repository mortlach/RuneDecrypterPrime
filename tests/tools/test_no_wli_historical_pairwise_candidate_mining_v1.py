from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    mine_historical_pairwise_candidates_v1 as mine,
)


def _candidate(
    *,
    artifact: str,
    candidate_hash: str,
    text_hash: str,
    tokens: str,
    score: float,
    truth: float,
) -> dict[str, object]:
    return {
        "artifact_path": artifact,
        "token_count": len(tokens.split()),
        "token_sequence_text": tokens,
        "partial_text_hash": text_hash,
        "candidate_hash": candidate_hash,
        "score": score,
        "truth_match": truth,
        "fixture_seed": "411",
        "search_seed": "0",
    }


def test_repeated_ngram_rate_uses_numeric_base29_tokens_only() -> None:
    assert mine.repeated_ngram_rate("1 2 3 1 2 3", 3) == 2 / 4
    assert mine.repeated_ngram_rate("1 2", 3) == 0.0

    try:
        mine.repeated_ngram_rate("1 2 29", 2)
    except ValueError as exc:
        assert "base-29" in str(exc)
    else:
        raise AssertionError("expected invalid token sequence to fail")


def test_artifact_candidate_text_dedupe_keeps_best_labelled_duplicate() -> None:
    rows = [
        _candidate(
            artifact="a.json",
            candidate_hash="cand",
            text_hash="text",
            tokens="1 2 3",
            score=0.1,
            truth=0.2,
        ),
        _candidate(
            artifact="a.json",
            candidate_hash="cand",
            text_hash="text",
            tokens="1 2 3",
            score=0.2,
            truth=0.3,
        ),
    ]

    deduped = mine.dedupe_artifact_candidate_text(rows)

    assert len(deduped) == 1
    assert deduped[0]["score"] == 0.2
    assert deduped[0]["truth_match"] == 0.3


def test_pair_rows_use_same_artifact_same_length_and_truth_gap() -> None:
    rows = [
        _candidate(
            artifact="a.json",
            candidate_hash="truth_better",
            text_hash="text_a",
            tokens="1 2 3 1 2 3",
            score=0.1,
            truth=0.9,
        ),
        _candidate(
            artifact="a.json",
            candidate_hash="score_better",
            text_hash="text_b",
            tokens="4 5 6 7 8 9",
            score=0.2,
            truth=0.8,
        ),
        _candidate(
            artifact="other.json",
            candidate_hash="ignored_other_artifact",
            text_hash="text_c",
            tokens="1 2 3 4 5 6",
            score=0.5,
            truth=0.1,
        ),
    ]

    pair_rows = mine.build_pair_rows(rows)

    assert len(pair_rows) == 1
    row = pair_rows[0]
    assert row["stored_score_correct"] == 0
    assert row["stored_score_misranked"] == 1
    assert row["truth_better_text_hash"] == "text_a"
    assert row["stored_score_better_text_hash"] == "text_b"
    repeated_by_hash = {
        row["text_a_hash"]: row["repeated_3gram_a"],
        row["text_b_hash"]: row["repeated_3gram_b"],
    }
    assert repeated_by_hash["text_a"] > repeated_by_hash["text_b"]


def test_summary_reports_unique_pairs_and_repetition_split() -> None:
    rows = [
        _candidate(
            artifact="a.json",
            candidate_hash="a",
            text_hash="text_a",
            tokens="1 2 3 1 2 3",
            score=0.1,
            truth=0.9,
        ),
        _candidate(
            artifact="a.json",
            candidate_hash="b",
            text_hash="text_b",
            tokens="4 5 6 7 8 9",
            score=0.2,
            truth=0.8,
        ),
        _candidate(
            artifact="b.json",
            candidate_hash="c",
            text_hash="text_c",
            tokens="1 1 1 1 1 1",
            score=0.5,
            truth=0.3,
        ),
        _candidate(
            artifact="b.json",
            candidate_hash="d",
            text_hash="text_d",
            tokens="1 2 3 4 5 6",
            score=0.1,
            truth=0.2,
        ),
    ]
    pair_rows = mine.build_pair_rows(rows)
    unique_rows = mine.build_unique_text_pair_rows(pair_rows)
    summary = mine.build_summary(
        labelled_rows=rows,
        deduped_rows=rows,
        pair_rows=pair_rows,
        unique_text_pair_rows=unique_rows,
    )

    assert summary["score_tie_removed_pair_count"] == 2
    assert summary["stored_score_correct_count"] == 1
    assert summary["stored_score_misranked_count"] == 1
    assert summary["unique_numeric_text_pair_count"] == 2
    assert summary["unique_misranked_repetition_summary"]["unique_pair_count"] == 1
    assert summary["unique_score_correct_repetition_summary"]["unique_pair_count"] == 1
