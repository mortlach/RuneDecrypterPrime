from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    rescore_historical_pairwise_candidates_v1 as rescore,
)


def _candidate(
    *,
    artifact: str,
    candidate_hash: str,
    text_hash: str,
    tokens: str,
    stored_score: float,
    truth: float,
) -> dict[str, object]:
    return {
        "artifact_path": artifact,
        "token_count": len(tokens.split()),
        "token_sequence_text": tokens,
        "partial_text_hash": text_hash,
        "candidate_hash": candidate_hash,
        "score": stored_score,
        "truth_match": truth,
        "fixture_seed": "411",
        "search_seed": "0",
    }


def test_numeric_token_validation_rejects_outside_base29() -> None:
    assert rescore.validate_numeric_tokens("0 1 28")

    for bad in ("", "0 29", "-1 0", "1 x"):
        try:
            rescore.validate_numeric_tokens(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected invalid token sequence to fail: {bad!r}")


def test_score_correct_handles_missing_and_ties_explicitly() -> None:
    assert rescore._score_correct(winner_score=0.2, challenger_score=0.1) == 1
    assert rescore._score_correct(winner_score=0.1, challenger_score=0.2) == 0
    assert rescore._score_correct(winner_score=0.1, challenger_score=0.1) == ""
    assert rescore._score_correct(winner_score="", challenger_score=0.1) == ""


def test_pair_rows_keep_stored_and_current_scores_separate() -> None:
    rows = [
        _candidate(
            artifact="artifact.json",
            candidate_hash="truth_better",
            text_hash="text_a",
            tokens="1 2 3 1 2 3",
            stored_score=0.1,
            truth=0.9,
        ),
        _candidate(
            artifact="artifact.json",
            candidate_hash="stored_better",
            text_hash="text_b",
            tokens="4 5 6 7 8 9",
            stored_score=0.2,
            truth=0.8,
        ),
    ]
    rescored = {
        ("artifact.json", "text_a"): {
            "current_score": 0.3,
            "features_present": "current_score",
            "features_missing": "",
            "missing_reason": "",
        },
        ("artifact.json", "text_b"): {
            "current_score": 0.05,
            "features_present": "current_score",
            "features_missing": "",
            "missing_reason": "",
        },
    }

    pair_rows = rescore._pair_rows(rows, rescored)

    assert len(pair_rows) == 1
    pair = pair_rows[0]
    assert pair["winner_token_hash"] == "text_a"
    assert pair["winner_stored_score"] == 0.1
    assert pair["winner_current_score"] == 0.3
    assert pair["stored_score_correct"] == 0
    assert pair["current_score_correct"] == 1
    assert pair["stored_current_agree"] == 0


def test_missing_current_scores_are_reported_not_zeroed() -> None:
    rows = [
        _candidate(
            artifact="artifact.json",
            candidate_hash="truth_better",
            text_hash="text_a",
            tokens="1 2 3 1 2 3",
            stored_score=0.3,
            truth=0.9,
        ),
        _candidate(
            artifact="artifact.json",
            candidate_hash="challenger",
            text_hash="text_b",
            tokens="4 5 6 7 8 9",
            stored_score=0.2,
            truth=0.8,
        ),
    ]
    rescored = {
        ("artifact.json", "text_a"): {
            "current_score": "",
            "features_present": "",
            "features_missing": "current_score",
            "missing_reason": "synthetic missing",
        },
        ("artifact.json", "text_b"): {
            "current_score": 0.2,
            "features_present": "current_score",
            "features_missing": "",
            "missing_reason": "",
        },
    }

    pair = rescore._pair_rows(rows, rescored)[0]
    missingness = rescore._missingness_rows([pair])

    assert pair["winner_current_score"] == ""
    assert pair["current_score_correct"] == ""
    assert pair["current_score_missing_reason"] == "synthetic missing"
    assert missingness[0]["missing_reason"] == "synthetic missing"


def test_summary_reports_unique_counts_and_dominant_fraction() -> None:
    pair_rows = [
        {
            "winner_token_hash": "a",
            "challenger_token_hash": "b",
            "winner_candidate_hash": "ca",
            "challenger_candidate_hash": "cb",
            "artifact_path": "one.json",
            "fixture_seed": "411",
            "search_seed": "0",
            "stored_score_correct": 1,
            "current_score_correct": 0,
            "stored_current_agree": 0,
        },
        {
            "winner_token_hash": "a",
            "challenger_token_hash": "b",
            "winner_candidate_hash": "ca",
            "challenger_candidate_hash": "cb",
            "artifact_path": "two.json",
            "fixture_seed": "411",
            "search_seed": "0",
            "stored_score_correct": 0,
            "current_score_correct": 0,
            "stored_current_agree": 1,
        },
    ]

    summary = rescore.build_summary(pair_rows, elapsed_seconds=1.0)

    assert summary["pair_count"] == 2
    assert summary["unique_numeric_text_pair_count"] == 1
    assert summary["unique_candidate_hash_pair_count"] == 1
    assert summary["dominant_text_pair_fraction"] == 1.0
    assert summary["stored_score_correct_count"] == 1
    assert summary["current_score_misranked_count"] == 2
    assert summary["runtime_behavior_changed"] is False


def test_truth_fields_are_not_in_frozen_scorer_config() -> None:
    forbidden = {"truth_match", "truth_gap", "target_plaintext_idx", "oracle"}
    assert forbidden.isdisjoint(set(rescore.FROZEN_CURRENT_SCORER_CFG))
