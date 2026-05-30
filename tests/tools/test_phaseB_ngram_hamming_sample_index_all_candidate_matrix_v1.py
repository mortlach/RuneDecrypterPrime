from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1 as matrix,
)


def test_sample_index_matrix_configuration_is_all_candidate_order2_only() -> None:
    config = matrix.build_matrix_config()

    assert config["run_label"] == "phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1"
    assert config["run_mode"] == "sample_index_all_candidate_matrix"
    assert config["dataset_status"] == "sample_index_confirmed"
    assert config["dictionary_cuts"] == ["normal"]
    assert config["orders"] == [2]
    assert config["profiles"] == [
        "P0_exact_short",
        "P1_word_analogue_len7_hd2",
        "P2_conservative_len8_hd2",
    ]
    assert config["expected_cell_count"] == 3624


def test_sample_index_matrix_config_does_not_mutate_balanced_runner_config() -> None:
    balanced_before = matrix.base.build_config()

    matrix.build_matrix_config()

    balanced_after = matrix.base.build_config()
    assert balanced_after == balanced_before
    assert balanced_after["run_label"] == "phaseB_ngram_hamming_balanced_readout_v1"
    assert balanced_after["run_mode"] == "balanced_readout"


def test_sample_index_matrix_selects_all_hard_pair_candidates() -> None:
    candidate_rows = matrix.base.read_csv_rows(f"{matrix.base.HARD_PAIR_DIR_REL}/candidate_manifest_resolved.csv")
    chunk_rows = matrix.base.read_csv_rows(f"{matrix.base.HARD_PAIR_DIR_REL}/candidate_chunk_manifest.csv")
    hard_pair_rows = matrix.base.read_csv_rows(f"{matrix.base.HARD_PAIR_DIR_REL}/hard_pair_manifest.csv")
    summary_rows = matrix.base.read_csv_rows(f"{matrix.base.HARD_PAIR_DIR_REL}/pairwise_road_test_summary.csv")
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]] = {}
    for row in chunk_rows:
        if row.get("chunk_status") == "full_chunk":
            chunk_rows_by_candidate.setdefault(row["candidate_id"], []).append(row)
    for rows in chunk_rows_by_candidate.values():
        rows.sort(key=lambda row: matrix.base.parse_int(row.get("chunk_index", "")))
    selection = matrix.select_all_candidates(candidate_rows, chunk_rows_by_candidate, summary_rows)
    preflight = matrix.build_preflight(
        selection["selected_candidates"],
        {row["candidate_id"]: row for row in candidate_rows},
        chunk_rows_by_candidate,
        hard_pair_rows,
    )

    assert len(selection["selected_candidates"]) == 604
    assert selection["selection_config"]["selection_mode"] == "all_hard_pair_candidates_sample_index_matrix"
    assert selection["selection_config"]["asset_provenance_manifest"].endswith("provenance_manifest.json")
    assert selection["missing_strata"] == []
    assert preflight["hard_pair_candidate_stream_verified"] is True


def test_sample_index_matrix_strata_are_recorded() -> None:
    candidate_rows = matrix.base.read_csv_rows(f"{matrix.base.HARD_PAIR_DIR_REL}/candidate_manifest_resolved.csv")
    chunk_rows = matrix.base.read_csv_rows(f"{matrix.base.HARD_PAIR_DIR_REL}/candidate_chunk_manifest.csv")
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]] = {}
    for row in chunk_rows:
        if row.get("chunk_status") == "full_chunk":
            chunk_rows_by_candidate.setdefault(row["candidate_id"], []).append(row)
    selected = matrix.select_all_candidates(candidate_rows, chunk_rows_by_candidate, [])["selected_candidates"]
    strata = {row["selected_stratum"] for row in selected}
    roles = {row["known_better_or_worse_role"] for row in selected}

    assert "known_better_pair_candidate" in strata
    assert "known_worse_pair_candidate" in strata
    assert "mixed_pair_role_candidate" in strata
    assert "known_better" in roles
    assert "known_worse" in roles
