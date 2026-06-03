from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1 as build,
)


FIELDNAMES = (
    "n",
    "dictionary_cut",
    "encoding_direction",
    "rune_key_hex",
    "rune_joined",
    "rune_words",
    "rune_lengths",
    "rune_token_ids",
    "word_token_ids",
    "wli",
    "count",
    "log_count",
    "phrase_count",
    "top_latin_ngram",
    "top_latin_count",
    "latin_examples",
    "source_file",
)


def write_payload(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELDNAMES))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})


def row(*, word_token_ids: list[list[int]], count: float = 1.0, log_count: float = 0.5) -> dict[str, object]:
    rune_token_ids = [token for word in word_token_ids for token in word]
    return {
        "n": len(word_token_ids),
        "dictionary_cut": "normal",
        "encoding_direction": "fwd",
        "rune_lengths": json.dumps([len(word) for word in word_token_ids]),
        "rune_token_ids": json.dumps(rune_token_ids),
        "word_token_ids": json.dumps(word_token_ids),
        "count": count,
        "log_count": log_count,
        "phrase_count": 1,
        "top_latin_ngram": "fixture",
    }


def seed_source(tmp_path: Path, *, asset_mode: str = "full") -> None:
    payload_rel = (
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "phaseB_ngram_hamming_full_raw_asset_shards_v1/order_2/fixture/normal_fwd/ngram2.csv.gz"
    )
    write_payload(
        tmp_path / payload_rel,
        [
            row(word_token_ids=[[1], [2, 3]], count=2.0, log_count=0.7),
            row(word_token_ids=[[1], [2, 3]], count=3.0, log_count=1.1),
            row(word_token_ids=[[1, 2], [3]], count=5.0, log_count=1.7),
        ],
    )
    asset_home = tmp_path / "assets/ngram_hamming/phaseB_full_raw_v1"
    asset_home.mkdir(parents=True)
    (asset_home / "asset_manifest.json").write_text(
        json.dumps(
            {
                "asset_id": "phaseB_ngram_hamming_full_raw_v1",
                "asset_mode": asset_mode,
                "files": [
                    {
                        "role": "shard_payload",
                        "path": payload_rel,
                        "ngram_order": 2,
                        "dictionary_cut": "normal",
                        "direction": "fwd",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    validation = tmp_path / build.SOURCE_VALIDATION_MANIFEST_REL
    validation.parent.mkdir(parents=True)
    validation.write_text(json.dumps({"status": "pass"}) + "\n", encoding="utf-8")


def read_compact_rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_compact_builder_preserves_word_structured_identity_and_aggregates_duplicates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(build, "REPO_ROOT", tmp_path)
    seed_source(tmp_path)

    manifest = build.build_compact_lookup_asset(output_dir=tmp_path / "out")

    assert manifest["asset_status"] == "built"
    assert manifest["old_phrase_index_v1_used"] is False
    assert manifest["sample_asset_used"] is False
    assert manifest["row_count_before_dedup"] == 3
    assert manifest["row_count_after_dedup"] == 2
    assert manifest["duplicate_identity_count"] == 1
    compact_path = tmp_path / manifest["files"][0]["path"]
    rows = read_compact_rows(compact_path)
    assert len(rows) == 2
    assert {row["word_token_tuple"] for row in rows} == {"[[1],[2,3]]", "[[1,2],[3]]"}
    duplicate_row = next(row for row in rows if row["source_row_count"] == "2")
    assert duplicate_row["duplicate_row_count"] == "1"
    assert float(duplicate_row["sum_count"]) == 5.0
    assert float(duplicate_row["max_count"]) == 3.0
    metadata = json.loads((tmp_path / build.ASSET_META_DIR_REL / "asset_manifest.json").read_text(encoding="utf-8"))
    assert metadata["payload_storage_mode"] == "local_output_payload_due_large_size"
    assert metadata["payload_manifest"] == "out/compact_asset_manifest.json"
    assert (tmp_path / build.ASSET_META_DIR_REL / "README.md").exists()


def test_compact_builder_blocks_sample_mode_source(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(build, "REPO_ROOT", tmp_path)
    seed_source(tmp_path, asset_mode="sample")

    manifest = build.build_compact_lookup_asset(output_dir=tmp_path / "out")

    assert manifest["asset_status"] == "blocked"
    assert "source asset mode is not full" in manifest["blocked_reasons"]
