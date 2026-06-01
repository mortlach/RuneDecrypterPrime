from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_full_raw_language_asset_pack_v1 as pack,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prepare_provenance(tmp_path: Path, *, status: str = "pass", include_strict: bool = True) -> None:
    prov = tmp_path / pack.SHARD_PROVENANCE_DIR_REL
    payload_a = tmp_path / "payload" / "normal.csv.gz"
    payload_b = tmp_path / "payload" / "strict.csv.gz"
    payload_a.parent.mkdir(parents=True, exist_ok=True)
    payload_a.write_text("normal\n", encoding="utf-8")
    payload_b.write_text("strict\n", encoding="utf-8")
    output_rows = [
        {
            "ngram_order": 2,
            "dictionary_cut": "normal",
            "direction": "fwd",
            "output_file": "payload/normal.csv.gz",
            "bytes": payload_a.stat().st_size,
            "aggregate_rows": 3,
            "dictionary_kept_rows": 4,
            "count_sum": 5,
        }
    ]
    if include_strict:
        output_rows.append(
            {
                "ngram_order": 2,
                "dictionary_cut": "strict",
                "direction": "fwd",
                "output_file": "payload/strict.csv.gz",
                "bytes": payload_b.stat().st_size,
                "aggregate_rows": 6,
                "dictionary_kept_rows": 7,
                "count_sum": 8,
            }
        )
    write_json(
        prov / "shard_provenance_manifest.json",
        {
            "status": status,
            "full_raw_ngram_rebuild_confirmed": status == "pass",
            "run_root": "run_root",
            "sample_line_limit_per_order": None,
            "completed_shards": 2,
            "total_shards": 2,
            "missing_shards": 0,
            "failed_shards": 0,
            "missing_output_files": 0,
            "missing_required_output_combos": 0 if include_strict else 1,
            "output_count_by_order_cut_direction": [
                {"ngram_order": 2, "dictionary_cut": "normal", "direction": "fwd", "row_count": 1},
                {"ngram_order": 2, "dictionary_cut": "strict", "direction": "fwd", "row_count": 1},
            ]
            if include_strict
            else [{"ngram_order": 2, "dictionary_cut": "normal", "direction": "fwd", "row_count": 1}],
            "aggregate_rows": 9,
            "dictionary_kept_rows": 11,
        },
    )
    write_csv(prov / "output_file_rows.csv", output_rows, list(output_rows[0]))
    write_csv(prov / "shard_rows.csv", [{"status": "pass"}], ["status"])
    write_csv(prov / "missing_shard_rows.csv", [], ["ngram_order"])
    write_csv(prov / "missing_required_output_combo_rows.csv", [], ["ngram_order"])
    write_csv(
        prov / "phrase_length_distribution_rows.csv",
        [{"ngram_order": 2, "dictionary_cut": "normal", "direction": "fwd", "phrase_token_length": 2, "row_count": 3}],
        ["ngram_order", "dictionary_cut", "direction", "phrase_token_length", "row_count"],
    )
    write_csv(
        prov / "word_length_distribution_rows.csv",
        [{"ngram_order": 2, "dictionary_cut": "normal", "direction": "fwd", "word_position": 1, "word_token_length": 1, "row_count": 3}],
        ["ngram_order", "dictionary_cut", "direction", "word_position", "word_token_length", "row_count"],
    )


def test_asset_pack_refuses_non_pass_provenance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "REQUIRED_ORDERS", (2,))
    prepare_provenance(tmp_path, status="running_or_interrupted")

    manifest = pack.build_language_asset_pack(asset_home=tmp_path / "assets/ngram_hamming/phaseB_full_raw_v1")

    assert manifest["asset_status"] == "blocked"
    assert "shard provenance status is not pass" in manifest["blocked_reasons"]


def test_asset_pack_refuses_missing_strict_cut(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "REQUIRED_ORDERS", (2,))
    prepare_provenance(tmp_path, include_strict=False)

    manifest = pack.build_language_asset_pack(asset_home=tmp_path / "assets/ngram_hamming/phaseB_full_raw_v1")

    assert manifest["asset_status"] == "blocked"
    assert "strict cut is missing" in manifest["blocked_reasons"]


def test_asset_pack_writes_repo_relative_posix_paths_and_clears_stale_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "REQUIRED_ORDERS", (2,))
    prepare_provenance(tmp_path)
    asset_home = tmp_path / "assets/ngram_hamming/phaseB_full_raw_v1"
    stale = asset_home / "stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old\n", encoding="utf-8")

    manifest = pack.build_language_asset_pack(asset_home=asset_home)

    assert manifest["asset_status"] == "review_ready_candidate"
    assert not stale.exists()
    assert manifest["files"]
    assert all("\\" not in row["path"] for row in manifest["files"])
    assert all(not Path(row["path"]).is_absolute() for row in manifest["files"])
    assert (asset_home / "asset_manifest.json").exists()
    assert (asset_home / "README.md").exists()
