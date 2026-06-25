from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from tools import release_review_pack as pack


def _write(path: Path, content: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_release_review_pack_includes_review_contract_files_and_small_data(tmp_path: Path) -> None:
    repo = tmp_path
    zip_path = repo / "output" / "tools" / "review" / "pack.zip"

    _write(repo / "AGENTS.md", "# agent rules\n")
    _write(repo / "README.md", "# readme\n")
    _write(repo / "pyproject.toml", "[project]\nname='x'\n")
    _write(repo / "install.py", "print('install')\n")
    _write(repo / "install.ps1", "Write-Host install\n")
    _write(repo / "setup.py", "from setuptools import setup\n")
    _write(repo / "pytest.ini", "[pytest]\n")
    _write(repo / "MANIFEST.in", "include README.md\n")
    _write(repo / "assets_manifest_v1.json", "{}\n")
    _write(repo / "unexpected_root_patch.py", "print('patch')\n")
    _write(repo / "repair_old_release.py", "print('repair')\n")
    _write(repo / "root_archive.zip", "NOPE\n")
    _write(repo / "src" / "rune_decrypter_prime" / "core.py", "VALUE = 1\n")
    _write(
        repo / "src" / "rune_decrypter_prime" / "data" / "cipher_tests" / "baseline_registry.py",
        "BASELINE = {}\n",
    )
    _write(repo / "tests" / "core" / "test_core.py", "def test_ok():\n    pass\n")
    _write(repo / "docs" / "release_contracts" / "v1" / "d4_contract_closure.md", "# D4\n")
    _write(repo / "tutorials" / "v1" / "run_tutorials.py", "print('tutorials')\n")
    _write(repo / ".github" / "workflows" / "rdp_v1_full_proof.yml", "name: proof\n")
    _write(repo / "tools" / "release_review_pack.py", "# tool copy\n")

    _write(repo / "output" / "test_logs" / "full_pytest.log", "NOPE\n")
    _write(repo / "assets" / "lm2.zst", "NOPE\n")
    _write(repo / "planning" / "private.md", "NOPE\n")
    _write(repo / "src" / "rune_decrypter_prime" / "data" / "large_asset.zst", "NOPE\n")

    summary = pack.make_release_review_pack(
        repo_root=repo,
        output_root=zip_path.parent,
        zip_path_override=zip_path,
        max_file_bytes=4096,
        git_metadata={
            "git_branch": "prelease/v1.0.0_d7",
            "git_commit_sha": "0123456789abcdef",
            "git_working_tree_dirty": False,
        },
    )

    assert zip_path.exists()
    assert summary["included_files_count"] >= 10
    assert Path(str(summary["summary_path"])).exists()
    assert summary["git_branch"] == "prelease/v1.0.0_d7"
    assert summary["git_commit_sha"] == "0123456789abcdef"
    assert summary["git_working_tree_dirty"] is False

    with ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("REVIEW_PACK_MANIFEST.json").decode("utf-8"))

    assert "REVIEW_PACK_README.md" in names
    assert "REVIEW_PACK_MANIFEST.json" in names
    assert "AGENTS.md" in names
    assert "README.md" in names
    assert "pyproject.toml" in names
    assert "install.py" in names
    assert "install.ps1" in names
    assert "setup.py" in names
    assert "pytest.ini" in names
    assert "MANIFEST.in" in names
    assert "assets_manifest_v1.json" in names
    assert "unexpected_root_patch.py" not in names
    assert "repair_old_release.py" not in names
    assert "src/rune_decrypter_prime/core.py" in names
    assert "src/rune_decrypter_prime/data/cipher_tests/baseline_registry.py" in names
    assert "tests/core/test_core.py" in names
    assert "docs/release_contracts/v1/d4_contract_closure.md" in names
    assert "tutorials/v1/run_tutorials.py" in names
    assert ".github/workflows/rdp_v1_full_proof.yml" in names
    assert "tools/release_review_pack.py" in names

    assert "output/test_logs/full_pytest.log" not in names
    assert "assets/lm2.zst" not in names
    assert "planning/private.md" not in names
    assert "src/rune_decrypter_prime/data/large_asset.zst" not in names
    assert "root_archive.zip" not in names
    assert "repair_old_release.py" not in names
    assert manifest["schema"] == "rdp_v1_review_pack_manifest.v1"
    assert manifest["root_file_selection"] == "strict_root_allowlist_filtered_by_review_pack_rules"
    assert manifest["git_branch"] == "prelease/v1.0.0_d7"
    assert manifest["git_commit_sha"] == "0123456789abcdef"
    assert manifest["git_working_tree_dirty"] is False
    excluded = {entry["path"]: entry["reason"] for entry in manifest["excluded_entries"]}
    assert "root_archive.zip" not in excluded
    assert "repair_old_release.py" not in excluded
    assert "unexpected_root_patch.py" not in excluded


def test_release_review_pack_excludes_large_text_files_by_size(tmp_path: Path) -> None:
    repo = tmp_path
    zip_path = repo / "output" / "pack.zip"
    _write(repo / "README.md", "# ok\n")
    _write(repo / "docs" / "small.md", "small\n")
    _write(repo / "docs" / "large.md", "x" * 100)

    pack.make_release_review_pack(
        repo_root=repo,
        output_root=zip_path.parent,
        zip_path_override=zip_path,
        max_file_bytes=32,
        git_metadata={"git_branch": None, "git_commit_sha": None, "git_working_tree_dirty": None},
    )

    with ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("REVIEW_PACK_MANIFEST.json").decode("utf-8"))

    assert "docs/small.md" in names
    assert "docs/large.md" not in names
    excluded = {entry["path"]: entry["reason"] for entry in manifest["excluded_entries"]}
    assert excluded["docs/large.md"] == "too_large>32"


def test_git_metadata_reports_clean_working_tree_as_not_dirty(monkeypatch) -> None:
    def fake_run(args, **kwargs):
        command = tuple(args[-2:])
        if command == ("rev-parse", "HEAD"):
            return SimpleNamespace(returncode=0, stdout="0123456789abcdef\n")
        if command == ("--abbrev-ref", "HEAD"):
            return SimpleNamespace(returncode=0, stdout="prelease/v1.0.0_d7\n")
        if command == ("status", "--porcelain"):
            return SimpleNamespace(returncode=0, stdout="")
        raise AssertionError(args)

    monkeypatch.setattr(pack.subprocess, "run", fake_run)

    assert pack._git_metadata(Path("/repo")) == {
        "git_branch": "prelease/v1.0.0_d7",
        "git_commit_sha": "0123456789abcdef",
        "git_working_tree_dirty": False,
    }
