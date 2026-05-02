from __future__ import annotations

from copy import deepcopy

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_stage35_rank6_route_lineage_confirmation_prep_v1 as prep,
)


def _raw_row(
    *,
    selected_start: float = 0.300,
    shallow_minus_selected: float = 0.100,
) -> dict[str, object]:
    return {
        "fixture_seed": 1411,
        "search_seed": 7005,
        "candidate_rank": 6,
        "candidate_hash": "cand",
        "artifact_relpath": "dummy/best_instance.json",
        "selected_start_match_ratio": selected_start,
        "resume_minus_selected": shallow_minus_selected,
    }


def _artifact(
    *,
    candidate_source: str = "phaseA_selected",
    candidate_source_rank: object = 1,
    novelty_distance: object = 188,
    include_candidate: bool = True,
    include_anchor: bool = True,
) -> dict[str, object]:
    candidate = {
        "candidate_hash": "cand",
        "source": candidate_source,
        "source_rank": candidate_source_rank,
        "novelty_distance_to_anchor": novelty_distance,
        "key": [0, 1, 2, 3],
    }
    anchor = {
        "candidate_hash": "anchor",
        "source": "phaseB_topk",
        "source_rank": 1,
        "novelty_distance_to_anchor": 0,
        "key": [3, 2, 1, 0],
    }
    rows = []
    if include_candidate:
        rows.append(candidate)
    if include_anchor:
        rows.append(anchor)
    return {
        "final_best_key_idx": [0, 1, 2, 3],
        "stage3_diagnostics": {
            "phaseC_anchor_candidate_hash": "anchor",
            "phaseC_candidate_pool_rows": rows,
        },
    }


def test_route_lineage_keep_when_source_rank_1_and_novelty_high() -> None:
    row = prep.classify_rank6_row(_raw_row(), _artifact())

    assert row["row_valid"] == 1
    assert row["route_lineage_keep"] == 1
    assert row["confirmation_group"] == (
        "A_old_reject_route_keep_predicted_recovered_positive"
    )


def test_route_lineage_rejects_source_rank_1_with_low_novelty() -> None:
    row = prep.classify_rank6_row(_raw_row(), _artifact(novelty_distance=159))

    assert row["row_valid"] == 1
    assert row["route_lineage_keep"] == 0
    assert row["confirmation_group"] == "D_both_reject_negative_control"


def test_route_lineage_rejects_later_source_rank_with_high_novelty() -> None:
    row = prep.classify_rank6_row(
        _raw_row(),
        _artifact(candidate_source_rank=3, novelty_distance=191),
    )

    assert row["row_valid"] == 1
    assert row["route_lineage_keep"] == 0
    assert row["confirmation_group"] == "D_both_reject_negative_control"


def test_missing_candidate_row_is_invalid_not_reject() -> None:
    row = prep.classify_rank6_row(_raw_row(), _artifact(include_candidate=False))

    assert row["row_valid"] == 0
    assert row["route_lineage_keep"] == 0
    assert row["confirmation_group"] == "E_invalid_missing_lineage"
    assert "candidate_hash_not_found_in_pool" in str(row["invalid_reason"])


def test_missing_anchor_row_is_invalid_not_reject() -> None:
    row = prep.classify_rank6_row(_raw_row(), _artifact(include_anchor=False))

    assert row["row_valid"] == 0
    assert row["route_lineage_keep"] == 0
    assert row["confirmation_group"] == "E_invalid_missing_lineage"
    assert "anchor_hash_not_found_in_pool" in str(row["invalid_reason"])


def test_missing_source_rank_is_invalid_not_reject() -> None:
    artifact = _artifact()
    del artifact["stage3_diagnostics"]["phaseC_candidate_pool_rows"][0]["source_rank"]

    row = prep.classify_rank6_row(_raw_row(), artifact)

    assert row["row_valid"] == 0
    assert row["route_lineage_keep"] == 0
    assert row["confirmation_group"] == "E_invalid_missing_lineage"
    assert "missing_candidate_source_rank" in str(row["invalid_reason"])


def test_missing_novelty_distance_is_invalid_not_reject() -> None:
    artifact = _artifact()
    del artifact["stage3_diagnostics"]["phaseC_candidate_pool_rows"][0][
        "novelty_distance_to_anchor"
    ]

    row = prep.classify_rank6_row(_raw_row(), artifact)

    assert row["row_valid"] == 0
    assert row["route_lineage_keep"] == 0
    assert row["confirmation_group"] == "E_invalid_missing_lineage"
    assert "missing_candidate_novelty_distance_to_anchor" in str(row["invalid_reason"])


def test_final_best_distance_is_ignored_by_action_safe_rule() -> None:
    artifact_a = _artifact()
    artifact_b = deepcopy(artifact_a)
    artifact_a["final_best_key_idx"] = [0, 1, 2, 3]
    artifact_b["final_best_key_idx"] = [9, 9, 9, 9]

    row_a = prep.classify_rank6_row(_raw_row(), artifact_a)
    row_b = prep.classify_rank6_row(_raw_row(), artifact_b)

    assert row_a["route_lineage_keep"] == 1
    assert row_b["route_lineage_keep"] == 1
    assert row_a["confirmation_group"] == row_b["confirmation_group"]


def test_group_labels_for_old_softened_and_route_lineage_disagreement() -> None:
    group_a = prep.classify_rank6_row(
        _raw_row(selected_start=0.300, shallow_minus_selected=0.100),
        _artifact(),
    )
    group_b = prep.classify_rank6_row(
        _raw_row(selected_start=0.500, shallow_minus_selected=0.100),
        _artifact(novelty_distance=159),
    )
    group_c = prep.classify_rank6_row(
        _raw_row(selected_start=0.500, shallow_minus_selected=0.100),
        _artifact(),
    )
    group_d = prep.classify_rank6_row(
        _raw_row(selected_start=0.300, shallow_minus_selected=0.100),
        _artifact(novelty_distance=159),
    )

    assert group_a["confirmation_group"].startswith("A_")
    assert group_b["confirmation_group"].startswith("B_")
    assert group_c["confirmation_group"].startswith("C_")
    assert group_d["confirmation_group"].startswith("D_")
