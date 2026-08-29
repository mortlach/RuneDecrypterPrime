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


def _rows() -> list[dict[str, str]]:
    assert TRACEABILITY_CSV.is_file(), "missing source decision traceability CSV"
    with TRACEABILITY_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_source_row_has_release_decision_and_target_boundary() -> None:
    rows = _rows()
    assert rows
    for row in rows:
        source_id = row["source_id"]
        assert row["corrected_design_decision"].strip(), source_id
        assert row["target_file_or_boundary"].strip(), source_id
        assert row["chain_status"] == "ok", source_id


def test_every_source_row_has_acceptance_evidence_or_matrix_link() -> None:
    for row in _rows():
        source_id = row["source_id"]
        source_acceptance = row["acceptance_tests_from_source_row"].strip()
        matrix_acceptance = row["acceptance_matrix_links_after_repair"].strip()
        assert source_acceptance or matrix_acceptance, source_id
