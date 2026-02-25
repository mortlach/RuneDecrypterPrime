from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.benchmarks.scoring.span_hamming_nose.bench_span_hamming_nose_suite import _sample_header
from tools.benchmarks.scoring.span_hamming_nose.merge_span_hamming_nose_shards import (
    MergeConfig,
    run_merge,
)
from tools.benchmarks.scoring.span_hamming_nose.schema import PlanRow, write_plan_csv


pytestmark = pytest.mark.tier_a


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_samples(path: Path, rows: list[dict[str, str]]) -> None:
    header = _sample_header()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: str(row.get(k, "")) for k in header})


def _sample_row(*, sample_id: str, row_id: str, generator: str, span_raw: float) -> dict[str, str]:
    row = {k: "" for k in _sample_header()}
    row.update(
        {
            "sample_id": sample_id,
            "row_id": row_id,
            "direction": "ltr",
            "length_bucket": "20",
            "generator": generator,
            "book_id": "book_a_fwd",
            "book_path": "book_a_fwd.npz",
            "start": "0",
            "text_length": "20",
            "stride": "200",
            "batch_index": "1",
            "seed_local": "1",
            "span_raw": str(span_raw),
            "coverage": "1.0",
            "quality": "1.0",
            "n_chars": "20",
            "chars_covered": "20",
            "n_intervals_selected": "1",
            "length_bins": "[3,4]",
            "span_raw_by_len": "[0.5,0.5]",
            "coverage_by_len": "[0.5,0.5]",
            "quality_by_len": "[1.0,1.0]",
            "selected_intervals_by_len": "[1,0]",
            "chars_covered_by_len": "[20,0]",
            "n_windows_total": "10",
            "n_windows_scored": "10",
            "n_candidates_considered": "10",
            "n_candidates_pruned_cap": "0",
            "char1_score": "0.1",
            "char2_score": "0.2",
            "char3_score": "0.3",
            "char4_score": "0.4",
        }
    )
    return row


def test_merge_shards_writes_combined_outputs(tmp_path: Path) -> None:
    shard0 = tmp_path / "runA__shard0of2"
    shard1 = tmp_path / "runA__shard1of2"
    out_dir = tmp_path / "merged_out"
    for d in (shard0, shard1):
        d.mkdir(parents=True, exist_ok=True)

    shared_cfg = {
        "suite_version": "span_hamming_nose_v2",
        "token_key": "pt_nose_data",
        "global_seed": 12345,
        "tokenized_dir": "assets_packed/tokenized_pg",
        "directions": ["ltr"],
        "length_buckets": [20],
        "min_stride": 200,
        "stride_factor": 1.0,
        "max_windows_per_book_by_l": {"20": 1},
        "max_windows_fallback": 50,
        "generators": ["REAL", "RAND_UNIGRAM"],
        "corrupt_pcts": [],
        "enable_char_baselines": False,
        "span_config": {"len_min": 3, "len_max": 14, "max_hd": 2},
        "corpus_list_hash": "abc123",
        "resolved_books": [
            {
                "book_id": "book_a_fwd",
                "path": "book_a_fwd.npz",
                "direction": "ltr",
                "n_tokens": 1000,
            }
        ],
        "shard_count": 2,
        "shard_strategy": "book_hash_mod",
    }
    cfg0 = dict(shared_cfg)
    cfg0.update({"shard_index": 0, "shard_books": shared_cfg["resolved_books"]})
    cfg1 = dict(shared_cfg)
    cfg1.update({"shard_index": 1, "shard_books": shared_cfg["resolved_books"]})
    _write_json(shard0 / "run_config.json", cfg0)
    _write_json(shard1 / "run_config.json", cfg1)

    write_plan_csv(
        shard0 / "plan.csv",
        [
            PlanRow(
                row_idx=0,
                row_id="row_0",
                direction="ltr",
                length_bucket=20,
                book_id="book_a_fwd",
                book_path="book_a_fwd.npz",
                start=0,
                text_length=20,
                stride=200,
            )
        ],
    )
    write_plan_csv(
        shard1 / "plan.csv",
        [
            PlanRow(
                row_idx=1,
                row_id="row_1",
                direction="ltr",
                length_bucket=20,
                book_id="book_a_fwd",
                book_path="book_a_fwd.npz",
                start=200,
                text_length=20,
                stride=200,
            )
        ],
    )
    _write_samples(
        shard0 / "samples.csv",
        [_sample_row(sample_id="s0", row_id="row_0", generator="REAL", span_raw=0.8)],
    )
    _write_samples(
        shard1 / "samples.csv",
        [_sample_row(sample_id="s1", row_id="row_1", generator="RAND_UNIGRAM", span_raw=0.4)],
    )

    merge_cfg = MergeConfig(
        shard_run_dirs=[shard0, shard1],
        shard_parent_dir=tmp_path,
        shard_group_prefix=None,
        output_root=tmp_path,
        run_dir=out_dir,
        write_merged_samples=True,
        dedupe_by_sample_id=True,
    )
    merged = run_merge(merge_cfg)
    assert merged == out_dir

    assert (out_dir / "run_config.json").exists()
    assert (out_dir / "plan.csv").exists()
    assert (out_dir / "summary.csv").exists()
    assert (out_dir / "calibration.json").exists()
    assert (out_dir / "book_manifest.csv").exists()
    assert (out_dir / "samples.csv").exists()

    merged_cfg_json = json.loads((out_dir / "run_config.json").read_text(encoding="utf-8"))
    assert int(merged_cfg_json["source_shard_count"]) == 2
    assert int(merged_cfg_json["merged_samples_rows"]) == 2

