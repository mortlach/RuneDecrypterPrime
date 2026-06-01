from __future__ import annotations

import json
import gzip
import csv
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    summarise_phaseB_ngram_hamming_full_raw_asset_shards_v1 as summary,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_run_root(tmp_path: Path) -> Path:
    run_root = tmp_path / "20260530T120414Z__phaseB_ngram_hamming_full_raw_asset_shards_v1"
    write_json(
        run_root / "shard_build_config.json",
        {
            "sample_line_limit_per_order": None,
            "required_orders": [2, 3],
            "required_cuts": ["normal", "strict"],
            "required_directions": ["fwd"],
            "source_rows": [
                {
                    "ngram_order": 2,
                    "shard_index": 1,
                    "source_file_name": "1 2.txt",
                    "source_file_bytes": 100,
                },
                {
                    "ngram_order": 3,
                    "shard_index": 1,
                    "source_file_name": "1 2 3.txt",
                    "source_file_bytes": 200,
                },
            ],
        },
    )
    output_path = (
        tmp_path
        / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        / "phaseB_ngram_hamming_full_raw_asset_shards_v1/"
        / "20260530T120414Z__phaseB_ngram_hamming_full_raw_asset_shards_v1/"
        / "order_2/shard_0001__1_2.txt/normal_fwd/ngram2.csv.gz"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"not a real gzip for this summary test")
    write_json(
        run_root / "order_2/shard_0001__1_2.txt/shard_manifest.json",
        {
            "status": "pass",
            "ngram_order": 2,
            "shard_index": 1,
            "source_file_name": "1 2.txt",
            "source_file_bytes": 100,
            "elapsed_seconds": 1.25,
            "source_stats": [{"lines_seen": 10, "valid_format_rows": 9}],
            "output_files": [
                {
                    "dictionary_cut": "normal",
                    "direction": "fwd",
                    "ngram_order": 2,
                    "output_file": summary.repo_rel(output_path),
                    "bytes": 55,
                    "aggregate_rows": 3,
                    "dictionary_kept_rows": 4,
                    "count_sum": 99,
                }
            ],
        },
    )
    return run_root


def make_output_file(tmp_path: Path, run_root: Path, *, order: int, shard: int, cut: str, name: str) -> Path:
    output_path = (
        tmp_path
        / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        / "phaseB_ngram_hamming_full_raw_asset_shards_v1/"
        / run_root.name
        / f"order_{order}/shard_{shard:04d}__{name}/{cut}_fwd/ngram{order}.csv.gz"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["n", "dictionary_cut", "encoding_direction", "word_token_ids", "count"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "n": order,
                "dictionary_cut": cut,
                "encoding_direction": "fwd",
                "word_token_ids": "[[1], [2]]",
                "count": "1",
            }
        )
    return output_path


def output_row(path: Path, *, order: int, cut: str, aggregate_rows: int = 1) -> dict[str, object]:
    return {
        "dictionary_cut": cut,
        "direction": "fwd",
        "ngram_order": order,
        "output_file": summary.repo_rel(path),
        "bytes": 55,
        "aggregate_rows": aggregate_rows,
        "dictionary_kept_rows": aggregate_rows + 1,
        "count_sum": 99,
    }


def test_shard_provenance_summary_allows_partial_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(summary, "REPO_ROOT", tmp_path)
    run_root = make_run_root(tmp_path)
    output_dir = tmp_path / "out"

    manifest = summary.summarise_shard_provenance(run_root=run_root, output_dir=output_dir)

    assert manifest["status"] == "running_or_interrupted"
    assert manifest["full_raw_ngram_rebuild_confirmed"] is False
    assert manifest["completed_shards"] == 1
    assert manifest["total_shards"] == 2
    assert manifest["missing_shards"] == 1
    assert manifest["output_files"] == 1
    assert manifest["missing_output_files"] == 0
    assert manifest["missing_required_output_combos"] == 3
    assert manifest["phrase_length_distribution_rows"] == 1
    assert manifest["word_length_distribution_rows"] == 2
    assert manifest["length_partition_source_output_files"] == 1
    assert manifest["length_partition_parsed_output_files"] == 1
    assert manifest["length_partition_unparsed_output_files"] == 0
    assert (output_dir / "shard_provenance_manifest.json").exists()
    assert (output_dir / "missing_shard_rows.csv").exists()
    assert (output_dir / "phrase_length_distribution_rows.csv").exists()
    assert (output_dir / "word_length_distribution_rows.csv").exists()


def test_shard_provenance_summary_passes_when_all_expected_shards_exist(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(summary, "REPO_ROOT", tmp_path)
    run_root = make_run_root(tmp_path)
    order2_strict_path = make_output_file(tmp_path, run_root, order=2, shard=1, cut="strict", name="1_2.txt")
    order3_normal_path = make_output_file(tmp_path, run_root, order=3, shard=1, cut="normal", name="1_2_3.txt")
    order3_strict_path = make_output_file(tmp_path, run_root, order=3, shard=1, cut="strict", name="1_2_3.txt")
    order2_manifest = json.loads((run_root / "order_2/shard_0001__1_2.txt/shard_manifest.json").read_text())
    order2_manifest["output_files"].append(output_row(order2_strict_path, order=2, cut="strict", aggregate_rows=7))
    write_json(run_root / "order_2/shard_0001__1_2.txt/shard_manifest.json", order2_manifest)
    write_json(
        run_root / "order_3/shard_0001__1_2_3.txt/shard_manifest.json",
        {
            "status": "pass",
            "ngram_order": 3,
            "shard_index": 1,
            "source_file_name": "1 2 3.txt",
            "source_file_bytes": 200,
            "elapsed_seconds": 2.0,
            "source_stats": [{"lines_seen": 20, "valid_format_rows": 19}],
            "output_files": [
                output_row(order3_normal_path, order=3, cut="normal", aggregate_rows=5),
                output_row(order3_strict_path, order=3, cut="strict", aggregate_rows=6),
            ],
        },
    )

    manifest = summary.summarise_shard_provenance(run_root=run_root, output_dir=tmp_path / "out")

    assert manifest["status"] == "pass"
    assert manifest["full_raw_ngram_rebuild_confirmed"] is True
    assert manifest["completed_shards"] == 2
    assert manifest["missing_required_output_combos"] == 0
    assert manifest["source_bytes_completed"] == 300
    assert manifest["aggregate_rows"] == 21
    assert manifest["phrase_length_distribution_present"] is True
    assert manifest["word_length_distribution_present"] is True
    assert manifest["length_partition_source_output_files"] == 4
    assert manifest["length_partition_parsed_output_files"] == 4
    assert manifest["length_partition_unparsed_output_files"] == 0


def test_shard_provenance_summary_reports_unparsed_length_partitions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(summary, "REPO_ROOT", tmp_path)
    run_root = make_run_root(tmp_path)
    bad_path = make_output_file(tmp_path, run_root, order=3, shard=1, cut="normal", name="not_lengths.txt")
    write_json(
        run_root / "order_3/shard_0001__not_lengths.txt/shard_manifest.json",
        {
            "status": "pass",
            "ngram_order": 3,
            "shard_index": 1,
            "source_file_name": "not lengths.txt",
            "source_file_bytes": 200,
            "elapsed_seconds": 2.0,
            "source_stats": [{"lines_seen": 20, "valid_format_rows": 19}],
            "output_files": [output_row(bad_path, order=3, cut="normal", aggregate_rows=5)],
        },
    )

    manifest = summary.summarise_shard_provenance(run_root=run_root, output_dir=tmp_path / "out")

    assert manifest["length_partition_source_output_files"] == 2
    assert manifest["length_partition_parsed_output_files"] == 1
    assert manifest["length_partition_unparsed_output_files"] == 1
    assert manifest["length_partition_unparsed_aggregate_rows"] == 5
