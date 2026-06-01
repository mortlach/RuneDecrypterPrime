from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1 as pack,
)


def write_repo_file(tmp_path: Path, rel_path: str, text: str) -> None:
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(tmp_path: Path, rel_path: str, payload: object) -> None:
    write_repo_file(tmp_path, rel_path, json.dumps(payload, indent=2) + "\n")


def prepare_inputs(
    tmp_path: Path,
    *,
    provenance_status: str,
    completed: int,
    total: int,
    phrase_distribution: str | None = None,
    word_distribution: str | None = None,
) -> None:
    provenance_dir = tmp_path / "prov"
    run_root = tmp_path / "run_root"
    run_root.mkdir(parents=True)
    write_json(
        tmp_path,
        "run_root/shard_build_config.json",
        {"source_file_count": total, "required_orders": [2, 3]},
    )
    write_json(
        tmp_path,
        "run_root/shard_build_manifest.json",
        {
            "status": "running_or_interrupted" if provenance_status != "pass" else "pass",
            "completed_shards": completed,
            "total_shards": total,
        },
    )
    write_json(
        provenance_dir,
        "shard_provenance_manifest.json",
        {
            "status": provenance_status,
            "full_raw_ngram_rebuild_confirmed": provenance_status == "pass",
            "completed_shards": completed,
            "total_shards": total,
            "missing_shards": total - completed,
            "failed_shards": 0,
            "source_bytes_completed": completed * 10,
            "source_bytes_total": total * 10,
            "source_bytes_completed_fraction": completed / total,
            "aggregate_rows": 100,
            "dictionary_kept_rows": 110,
            "output_count_by_order_cut_direction": [
                {"ngram_order": 2, "dictionary_cut": "normal", "direction": "fwd", "row_count": 1}
            ],
            "run_root": "run_root",
        },
    )
    write_repo_file(
        provenance_dir,
        "output_file_rows.csv",
        "ngram_order,dictionary_cut,direction,aggregate_rows,dictionary_kept_rows,count_sum\n"
        "2,normal,fwd,10,11,12\n",
    )
    write_repo_file(provenance_dir, "shard_rows.csv", "status\npass\n")
    write_repo_file(provenance_dir, "missing_shard_rows.csv", "ngram_order\n")
    write_repo_file(provenance_dir, "missing_required_output_combo_rows.csv", "ngram_order\n")
    if phrase_distribution is not None:
        write_repo_file(provenance_dir, "phrase_length_distribution_rows.csv", phrase_distribution)
    if word_distribution is not None:
        write_repo_file(provenance_dir, "word_length_distribution_rows.csv", word_distribution)
    write_repo_file(provenance_dir, "readout.md", "# readout\n")
    write_repo_file(tmp_path, "context.md", "# context\n")
    write_repo_file(tmp_path, "source.py", "print('x')\n")
    write_repo_file(tmp_path, "live.log", "resume_completed_shards=1/2\n")


def test_review_pack_blocks_partial_provenance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "SHARD_PROVENANCE_DIR_REL", "prov")
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ("context.md",))
    monkeypatch.setattr(pack, "SOURCE_FILES_REL", ("source.py",))
    monkeypatch.setattr(pack, "LIVE_LOG_FILES_REL", ("live.log",))
    prepare_inputs(tmp_path, provenance_status="running_or_interrupted", completed=1, total=2)

    manifest = pack.build_review_pack(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["completed_shards"] == 1
    assert manifest["missing_shards"] == 1
    assert "full raw shard provenance status is not pass" in manifest["blocked_reasons"]
    assert (tmp_path / "out" / "review_pack_manifest.json").exists()
    assert (tmp_path / "out" / "review_checklist.csv").exists()
    assert (tmp_path / "out" / "normal_strict_row_counts.csv").exists()


def test_review_pack_blocks_when_required_checks_are_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "SHARD_PROVENANCE_DIR_REL", "prov")
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ("context.md",))
    monkeypatch.setattr(pack, "SOURCE_FILES_REL", ("source.py",))
    monkeypatch.setattr(pack, "LIVE_LOG_FILES_REL", ("live.log",))
    prepare_inputs(tmp_path, provenance_status="pass", completed=2, total=2)

    manifest = pack.build_review_pack(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["full_raw_ngram_rebuild_confirmed"] is True
    assert "one or more required provenance review checks are pending" in manifest["blocked_reasons"]
    assert "phrase_length_distributions" in manifest["pending_review_checks"]
    assert "word_length_distributions" in manifest["pending_review_checks"]
    assert manifest["normal_strict_row_counts"][0]["aggregate_rows"] == 10


def test_review_pack_blocks_when_phrase_distribution_has_only_header(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "SHARD_PROVENANCE_DIR_REL", "prov")
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ("context.md",))
    monkeypatch.setattr(pack, "SOURCE_FILES_REL", ("source.py",))
    monkeypatch.setattr(pack, "LIVE_LOG_FILES_REL", ("live.log",))
    prepare_inputs(
        tmp_path,
        provenance_status="pass",
        completed=2,
        total=2,
        phrase_distribution="ngram_order,dictionary_cut,direction,phrase_token_length,row_count\n",
        word_distribution="ngram_order,dictionary_cut,direction,word_position,word_token_length,row_count\n2,normal,fwd,1,1,10\n",
    )

    manifest = pack.build_review_pack(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert "phrase_length_distributions" in manifest["pending_review_checks"]
    assert "word_length_distributions" not in manifest["pending_review_checks"]


def test_review_pack_blocks_when_word_distribution_has_only_header(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "SHARD_PROVENANCE_DIR_REL", "prov")
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ("context.md",))
    monkeypatch.setattr(pack, "SOURCE_FILES_REL", ("source.py",))
    monkeypatch.setattr(pack, "LIVE_LOG_FILES_REL", ("live.log",))
    prepare_inputs(
        tmp_path,
        provenance_status="pass",
        completed=2,
        total=2,
        phrase_distribution="ngram_order,dictionary_cut,direction,phrase_token_length,row_count\n2,normal,fwd,2,10\n",
        word_distribution="ngram_order,dictionary_cut,direction,word_position,word_token_length,row_count\n",
    )

    manifest = pack.build_review_pack(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert "phrase_length_distributions" not in manifest["pending_review_checks"]
    assert "word_length_distributions" in manifest["pending_review_checks"]


def test_review_pack_becomes_review_ready_when_provenance_and_checks_pass(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "SHARD_PROVENANCE_DIR_REL", "prov")
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ("context.md",))
    monkeypatch.setattr(pack, "SOURCE_FILES_REL", ("source.py",))
    monkeypatch.setattr(pack, "LIVE_LOG_FILES_REL", ("live.log",))
    prepare_inputs(
        tmp_path,
        provenance_status="pass",
        completed=2,
        total=2,
        phrase_distribution="ngram_order,dictionary_cut,direction,phrase_token_length,row_count\n2,normal,fwd,2,10\n",
        word_distribution="ngram_order,dictionary_cut,direction,word_position,word_token_length,row_count\n2,normal,fwd,1,1,10\n",
    )

    manifest = pack.build_review_pack(output_dir=tmp_path / "out")

    assert manifest["status"] == "review_ready"
    assert manifest["full_raw_ngram_rebuild_confirmed"] is True
    assert not manifest["blocked_reasons"]
    assert not manifest["pending_review_checks"]
    assert manifest["phrase_length_distribution_rows"] == 1
    assert manifest["word_length_distribution_rows"] == 1
