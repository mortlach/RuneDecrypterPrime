from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_scorer_checkpoint_gate_splits_v1 as mod,
)


def _row(
    *,
    outcome: str,
    artifact: str = "a1",
    fixture: str = "411",
    search: str = "0",
    text_pair: str = "tp1",
    candidate_pair: str = "cp1",
    fired: int = 1,
) -> dict[str, str]:
    return {
        "rule_id": "r1",
        "artifact_path": artifact,
        "fixture_seed": fixture,
        "search_seed": search,
        "text_pair_key": text_pair,
        "candidate_pair_key": candidate_pair,
        "gate_fired": str(fired),
        "outcome": outcome,
    }


def test_metrics_count_rescue_break_unique_pairs() -> None:
    rows = [
        _row(outcome="rescue", text_pair="tp1", candidate_pair="cp1"),
        _row(outcome="rescue", text_pair="tp1", candidate_pair="cp1"),
        _row(outcome="break", text_pair="tp2", candidate_pair="cp2"),
        _row(outcome="same_correct", text_pair="tp3", candidate_pair="cp3", fired=0),
    ]
    out = mod._metrics(rows)
    assert out["pair_count"] == 4
    assert out["gate_fired_count"] == 3
    assert out["rescue_count"] == 2
    assert out["break_count"] == 1
    assert out["net_count"] == 1
    assert out["unique_text_pair_count"] == 3
    assert out["unique_misranked_rescue_pair_count"] == 1
    assert out["unique_control_break_pair_count"] == 1


def test_fixture_search_cell_labels_missing_values() -> None:
    assert mod._fixture_search_cell({"fixture_seed": "411", "search_seed": "7"}) == "411/search7"
    assert mod._fixture_search_cell({}) == "missing_fixture/searchmissing_search"


def test_max_fraction_reports_key_count_fraction() -> None:
    rows = [
        _row(outcome="rescue", artifact="a1"),
        _row(outcome="rescue", artifact="a1"),
        _row(outcome="rescue", artifact="a2"),
        _row(outcome="break", artifact="a2"),
    ]
    count, fraction, key = mod._max_fraction(rows, mod._artifact_cell, outcome="rescue")
    assert count == 2
    assert fraction == 2 / 3
    assert key == "a1"


def test_review_status_identifies_heldout_candidate() -> None:
    metrics = {
        "rescue_count": 40,
        "break_count": 2,
        "unique_misranked_rescue_pair_count": 12,
        "unique_control_break_pair_count": 2,
    }
    base = {"dominant_override_pair_fraction": "0.1"}
    assert (
        mod._review_status(
            metrics,
            base,
            low_break_signal=True,
            split_stable_candidate=True,
        )
        == "split_stable_candidate"
    )


def test_review_status_flags_low_break_split_concentration() -> None:
    metrics = {
        "rescue_count": 40,
        "break_count": 2,
        "unique_misranked_rescue_pair_count": 12,
        "unique_control_break_pair_count": 2,
    }
    base = {"dominant_override_pair_fraction": "0.1"}
    assert (
        mod._review_status(
            metrics,
            base,
            low_break_signal=True,
            split_stable_candidate=False,
        )
        == "low_break_split_concentration_risk"
    )


def test_review_status_flags_many_breaks() -> None:
    metrics = {
        "rescue_count": 100,
        "break_count": 40,
        "unique_misranked_rescue_pair_count": 50,
        "unique_control_break_pair_count": 30,
    }
    base = {"dominant_override_pair_fraction": "0.1"}
    assert mod._review_status(metrics, base) == "too_many_breaks"


def test_rule_robustness_leave_one_artifact_and_low_break() -> None:
    rows = []
    for artifact_idx in range(8):
        rows.extend(
            _row(
                outcome="rescue",
                artifact=f"a{artifact_idx}",
                fixture=str(400 + artifact_idx),
                text_pair=f"r{artifact_idx}_{i}",
            )
            for i in range(5)
        )
    rows.extend(_row(outcome="break", artifact="a2", fixture="402", text_pair=f"b{i}") for i in range(2))
    base = {
        "rule_id": "r1",
        "family": "test",
        "dominant_override_pair_fraction": "0.1",
    }
    out = mod._rule_robustness(rows, base)
    assert out["rescue_count"] == 40
    assert out["break_count"] == 2
    assert out["artifact_count"] == 8
    assert out["artifact_with_rescue_count"] == 8
    assert out["artifact_with_break_count"] == 1
    assert out["leave_one_artifact_min_net"] == 33
    assert out["leave_one_fixture_search_min_net"] == 33
    assert out["low_break_signal"] == 1
    assert out["split_stable_candidate"] == 1
