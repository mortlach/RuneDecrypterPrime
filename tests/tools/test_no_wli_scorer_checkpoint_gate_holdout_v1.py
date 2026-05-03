from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_scorer_checkpoint_gate_holdout_v1 as mod,
)


def _row(
    *,
    outcome: str,
    rule_id: str = "r1",
    artifact: str = "a1",
    fixture: str = "411",
    search: str = "7001",
    fired: int = 1,
    text_pair: str = "tp1",
    candidate_pair: str = "cp1",
) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "artifact_path": artifact,
        "fixture_seed": fixture,
        "search_seed": search,
        "gate_fired": str(fired),
        "outcome": outcome,
        "text_pair_key": text_pair,
        "candidate_pair_key": candidate_pair,
    }


def test_metrics_counts_unique_rescue_and_break_pairs() -> None:
    rows = [
        _row(outcome="rescue", text_pair="tp1"),
        _row(outcome="rescue", text_pair="tp1"),
        _row(outcome="break", text_pair="tp2"),
        _row(outcome="same_correct", fired=0, text_pair="tp3"),
    ]
    out = mod._metrics(rows)
    assert out["pair_count"] == 4
    assert out["gate_fired_count"] == 3
    assert out["rescue_count"] == 2
    assert out["break_count"] == 1
    assert out["net_count"] == 1
    assert out["unique_misranked_rescue_pair_count"] == 1
    assert out["unique_control_break_pair_count"] == 1


def test_heldout_split_rows_mark_negative_cells() -> None:
    rows = [
        _row(outcome="break", artifact="a1", text_pair="b1"),
        _row(outcome="break", artifact="a1", text_pair="b2"),
        _row(outcome="rescue", artifact="a2", text_pair="r1"),
    ]
    out = mod._heldout_split_rows("r1", rows, "artifact", mod._artifact_cell)
    by_key = {row["split_key"]: row for row in out}
    assert by_key["a1"]["heldout_status"] == "negative"
    assert by_key["a1"]["heldout_negative"] == 1
    assert by_key["a1"]["heldout_break_only"] == 1
    assert by_key["a2"]["heldout_status"] == "nonnegative"


def test_rule_status_requires_no_negative_heldout_cells() -> None:
    aggregate = {
        "break_count": 2,
        "unique_control_break_pair_count": 2,
        "rescue_count": 40,
        "unique_misranked_rescue_pair_count": 12,
    }
    split_rows = [
        {"split_type": "fixture_search", "heldout_negative": 0},
        {"split_type": "artifact", "heldout_negative": 0},
    ]
    assert mod._rule_status(aggregate, split_rows) == "strict_holdout_pass"
    split_rows.append({"split_type": "artifact", "heldout_negative": 1})
    assert mod._rule_status(aggregate, split_rows) == "heldout_negative_cell"


def test_summarise_rule_carries_prior_status_and_worst_splits() -> None:
    rows = []
    for idx in range(12):
        rows.append(
            _row(
                outcome="rescue",
                artifact=f"a{idx % 6}",
                fixture=str(400 + (idx % 4)),
                text_pair=f"r{idx}",
            )
        )
    for idx in range(2):
        rows.append(_row(outcome="break", artifact="bad", fixture="999", text_pair=f"b{idx}"))
    prior = {"review_status": "split_stable_candidate", "split_stable_candidate": "1"}
    summary, splits = mod._summarise_rule("r1", rows, prior)
    assert summary["prior_review_status"] == "split_stable_candidate"
    assert summary["rescue_count"] == 12
    assert summary["break_count"] == 2
    assert summary["worst_artifact_net"] == -2
    assert summary["negative_artifact_split_count"] == 1
    assert any(row["heldout_status"] == "negative" for row in splits)
