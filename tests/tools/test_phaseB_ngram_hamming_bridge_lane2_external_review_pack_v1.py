from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_bridge_lane2_external_review_pack_v1 as pack,
)


def write_repo_file(tmp_path: Path, rel_path: str, text: str) -> None:
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_repo_json(tmp_path: Path, rel_path: str, payload: object) -> None:
    write_repo_file(tmp_path, rel_path, json.dumps(payload, indent=2) + "\n")


def write_component_statuses(tmp_path: Path) -> None:
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/contract_pack_manifest.json",
        {"status": "pass"},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1/input_contract_manifest.json",
        {"status": "pass"},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1/synthetic_contract_manifest.json",
        {"status": "pass"},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json",
        {"status": "running_or_interrupted", "completed_shards": 4, "total_shards": 10},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json",
        {"status": "blocked"},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json",
        {"status": "blocked", "bridge_broad_scan_ready": False},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/gated_diagnostic_manifest.json",
        {"status": "blocked"},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/launch_decision_record_manifest.json",
        {"status": "blocked"},
    )


def test_external_review_pack_copies_files_and_builds_zip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ("AGENTS.md", "context.md"))
    monkeypatch.setattr(
        pack,
        "COMPONENT_FILES_REL",
        (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1/contract_pack_manifest.json",
            "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json",
        ),
    )
    monkeypatch.setattr(pack, "SOURCE_FILES_REL", ("source.py",))
    monkeypatch.setattr(pack, "TEST_FILES_REL", ("test_source.py",))
    write_repo_file(tmp_path, "AGENTS.md", "# rules\n")
    write_repo_file(tmp_path, "context.md", "# context\n")
    write_repo_file(tmp_path, "source.py", "print('x')\n")
    write_repo_file(tmp_path, "test_source.py", "def test_x(): pass\n")
    write_component_statuses(tmp_path)

    manifest = pack.build_external_review_pack(
        pack_dir=tmp_path / "review_pack",
        zip_path=tmp_path / "review_pack.zip",
    )

    assert manifest["status"] == "packed_with_blocks"
    assert manifest["completed_shards"] == 4
    assert manifest["bridge_broad_scan_ready"] is False
    assert not manifest["missing_files"]
    assert (tmp_path / "review_pack" / "10_context" / "review_summary.md").exists()
    assert (tmp_path / "review_pack.zip").exists()
    with ZipFile(tmp_path / "review_pack.zip", "r") as archive:
        names = archive.namelist()
    assert "review_pack/PACK_BUILD_SUMMARY.json" in names
    assert "review_pack/10_context/review_questions.md" in names


def test_external_review_pack_reports_missing_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ("missing.md",))
    monkeypatch.setattr(pack, "COMPONENT_FILES_REL", ())
    monkeypatch.setattr(pack, "SOURCE_FILES_REL", ())
    monkeypatch.setattr(pack, "TEST_FILES_REL", ())

    manifest = pack.build_external_review_pack(
        pack_dir=tmp_path / "review_pack",
        zip_path=tmp_path / "review_pack.zip",
    )

    assert manifest["status"] == "blocked"
    assert manifest["missing_files"] == ["missing.md"]


def test_external_review_pack_clears_stale_files_before_rebuild(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ("AGENTS.md",))
    monkeypatch.setattr(pack, "COMPONENT_FILES_REL", ())
    monkeypatch.setattr(pack, "SOURCE_FILES_REL", ())
    monkeypatch.setattr(pack, "TEST_FILES_REL", ())
    write_repo_file(tmp_path, "AGENTS.md", "# rules\n")
    write_component_statuses(tmp_path)
    stale = tmp_path / "review_pack" / "30_source" / "stale.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("# stale\n", encoding="utf-8")

    pack.build_external_review_pack(
        pack_dir=tmp_path / "review_pack",
        zip_path=tmp_path / "review_pack.zip",
    )

    assert not stale.exists()


def test_external_review_pack_includes_ngram_hamming_dependency_closure() -> None:
    required = {
        "src/rune_decrypter_prime/scoring/ngram_hamming/reference.py",
        "src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py",
        "src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py",
        "src/rune_decrypter_prime/scoring/ngram_hamming/__init__.py",
    }

    assert required <= set(pack.SOURCE_FILES_REL)


def test_external_review_pack_zip_contains_ngram_hamming_dependency_closure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pack, "CONTEXT_FILES_REL", ())
    monkeypatch.setattr(pack, "COMPONENT_FILES_REL", ())
    monkeypatch.setattr(pack, "TEST_FILES_REL", ())
    for rel_path in pack.SOURCE_FILES_REL:
        write_repo_file(tmp_path, rel_path, f"# {rel_path}\n")
    write_component_statuses(tmp_path)

    pack.build_external_review_pack(
        pack_dir=tmp_path / "review_pack",
        zip_path=tmp_path / "review_pack.zip",
    )

    required_entries = {
        "review_pack/30_source/src/rune_decrypter_prime/scoring/ngram_hamming/reference.py",
        "review_pack/30_source/src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py",
        "review_pack/30_source/src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py",
        "review_pack/30_source/src/rune_decrypter_prime/scoring/ngram_hamming/__init__.py",
    }
    with ZipFile(tmp_path / "review_pack.zip", "r") as archive:
        names = set(archive.namelist())

    assert required_entries <= names
