from __future__ import annotations

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TRACEABILITY_CSV = (
    REPO_ROOT
    / "docs"
    / "release_contracts"
    / "v1"
    / "final_source_to_wp_decision_target_test_chain.csv"
)
REQUIRED_COLUMNS = {
    "source_id",
    "source_material",
    "source_topic",
    "wp_claims_after_repair",
    "corrected_design_decision",
    "target_file_or_boundary",
    "acceptance_tests_from_source_row",
    "acceptance_matrix_links_after_repair",
    "chain_status",
}


def _rows() -> list[dict[str, str]]:
    assert TRACEABILITY_CSV.exists(), f"missing traceability CSV: {TRACEABILITY_CSV}"
    with TRACEABILITY_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        missing_columns = REQUIRED_COLUMNS.difference(reader.fieldnames)
        assert not missing_columns, f"missing traceability columns: {sorted(missing_columns)}"
        return list(reader)


def test_traceability_chain_has_one_row_per_stage1_source() -> None:
    rows = _rows()
    assert len(rows) == 76
    source_ids = [row["source_id"] for row in rows]
    assert len(source_ids) == len(set(source_ids))


def test_every_traceability_row_has_complete_chain() -> None:
    for row in _rows():
        source_id = row["source_id"]
        assert row["source_material"].strip(), source_id
        assert row["source_topic"].strip(), source_id
        assert row["wp_claims_after_repair"].strip(), source_id
        assert row["corrected_design_decision"].strip(), source_id
        assert row["target_file_or_boundary"].strip(), source_id
        has_source_acceptance = bool(row["acceptance_tests_from_source_row"].strip())
        has_matrix_acceptance = bool(row["acceptance_matrix_links_after_repair"].strip())
        assert has_source_acceptance or has_matrix_acceptance, source_id
        assert row["chain_status"] == "ok", source_id


def test_no_stale_source_id_families_remain_in_wp_links() -> None:
    forbidden_fragments = ("W12", "W13", "W14", "W15", "W16", "W17", "W18", "W19", "C01", "C02", "C03", "C04", "C05", "L01", "L02", "L03", "L07", "L08", "L09", "L10", "L11", "L12", "L13", "L14", "L15")
    joined_wp_claims = "\n".join(row["wp_claims_after_repair"] for row in _rows())
    for fragment in forbidden_fragments:
        assert fragment not in joined_wp_claims
