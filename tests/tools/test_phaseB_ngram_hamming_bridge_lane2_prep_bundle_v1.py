from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1 as bundle,
)


def write_repo_file(tmp_path: Path, rel_path: str, text: str) -> None:
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_prep_bundle_copies_component_context_and_source_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(bundle, "REPO_ROOT", tmp_path)
    component_files = (
        "component_a.json",
        "component_b.json",
    )
    context_files = ("context.md",)
    source_files = ("script.py",)
    monkeypatch.setattr(bundle, "COMPONENT_FILES_REL", component_files)
    monkeypatch.setattr(bundle, "CONTEXT_FILES_REL", context_files)
    monkeypatch.setattr(bundle, "SOURCE_FILES_REL", source_files)
    write_repo_file(tmp_path, "component_a.json", json.dumps({"status": "blocked", "bridge_broad_scan_ready": False}))
    write_repo_file(tmp_path, "component_b.json", json.dumps({"completed_shards": 5, "total_shards": 10}))
    write_repo_file(tmp_path, "context.md", "# context\n")
    write_repo_file(tmp_path, "script.py", "print('x')\n")

    manifest = bundle.build_prep_bundle(output_dir=tmp_path / "out")

    assert manifest["status"] == "pass"
    assert len(manifest["copied_files"]) == 4
    assert not manifest["missing_files"]
    assert (tmp_path / "out" / "10_component_outputs" / "component_a.json").exists()
    assert (tmp_path / "out" / "20_context" / "context.md").exists()
    assert (tmp_path / "out" / "30_source" / "script.py").exists()
    assert (tmp_path / "out" / "README.md").exists()


def test_prep_bundle_reports_missing_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(bundle, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(bundle, "COMPONENT_FILES_REL", ("missing.json",))
    monkeypatch.setattr(bundle, "CONTEXT_FILES_REL", ())
    monkeypatch.setattr(bundle, "SOURCE_FILES_REL", ())

    manifest = bundle.build_prep_bundle(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["missing_files"] == ["missing.json"]


def test_prep_bundle_includes_ngram_hamming_dependency_closure() -> None:
    required = {
        "src/rune_decrypter_prime/scoring/ngram_hamming/reference.py",
        "src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py",
        "src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py",
        "src/rune_decrypter_prime/scoring/ngram_hamming/__init__.py",
    }

    assert required <= set(bundle.SOURCE_FILES_REL)
