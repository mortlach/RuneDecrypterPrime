from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_bridge_lane2_input_contract_v1 as contract,
)


def test_input_contract_validates_candidate_chunk_rows() -> None:
    row = {
        "candidate_id": "c1",
        "chunk_id": "k1",
        "candidate_role": "known_better",
        "damage_level": "synthetic",
        "rune_token_ids": [1, 2, 3],
        "token_count": 3,
        "source_candidate_path": "synthetic",
        "source_candidate_sha256": "",
        "chunk_start_offset": 0,
        "chunk_end_offset": 3,
    }

    assert contract.validate_candidate_chunk_row(row) == []
    row["token_count"] = 2
    assert "token_count must equal len(rune_token_ids)" in contract.validate_candidate_chunk_row(row)


def test_input_contract_rejects_loose_candidate_chunk_rows() -> None:
    row = {
        "candidate_id": "c1",
        "chunk_id": "k1",
        "candidate_role": "unsupported",
        "damage_level": "real",
        "rune_token_ids": [1, 29],
        "token_count": 2,
        "source_candidate_path": "data/candidates.csv",
        "source_candidate_sha256": "not-a-digest",
        "chunk_start_offset": 3,
        "chunk_end_offset": 4,
    }

    errors = contract.validate_candidate_chunk_row(row)

    assert "candidate_role must be one of known_better, known_worse, baseline, challenger, or null" in errors
    assert "rune_token_ids must be rune token ids in range 0..28" in errors
    assert "chunk_end_offset - chunk_start_offset must equal token_count" in errors
    assert "source_candidate_sha256 must be a 64-character hex digest for real candidate rows" in errors


def test_input_contract_validates_pair_rows() -> None:
    row = {
        "pair_id": "p1",
        "expected_better_id": "a",
        "expected_worse_id": "b",
        "pair_source": "synthetic",
        "baseline_winner": "",
        "comparison_scope": "contract",
    }

    assert contract.validate_pair_input_row(row) == []
    row["expected_worse_id"] = "a"
    assert "expected_better_id and expected_worse_id must differ" in contract.validate_pair_input_row(row)


def test_input_contract_writes_schema_and_synthetic_rows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(contract, "REPO_ROOT", tmp_path)

    manifest = contract.build_input_contract(output_dir=tmp_path / "out")
    schema = json.loads((tmp_path / "out" / "input_schema_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "pass"
    assert manifest["no_real_candidate_scan"] is True
    assert manifest["synthetic_candidate_validation_errors"] == []
    assert manifest["synthetic_pair_validation_errors"] == []
    assert "rune_token_ids" in schema["candidate_chunk_required_fields"]
    assert "pair_id" in schema["pair_input_required_fields"]
