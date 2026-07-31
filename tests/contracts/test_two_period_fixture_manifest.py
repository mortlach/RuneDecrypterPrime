from __future__ import annotations

import ast
import hashlib
import json
import shutil

import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs" / "release_contracts" / "v1" / "two_period_fixture_manifest.json"


def _local_import_closure(entry_point: str) -> set[str]:
    pending = [entry_point]
    closure: set[str] = set()
    while pending:
        relpath = pending.pop()
        if relpath in closure:
            continue
        closure.add(relpath)
        tree = ast.parse((ROOT / relpath).read_text(encoding="utf-8"), filename=relpath)
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
        for module in modules:
            if not module.startswith("cipher_development"):
                continue
            candidate = Path(*module.split(".")).with_suffix(".py").as_posix()
            if (ROOT / candidate).is_file():
                pending.append(candidate)
    return closure


def test_pack09_retained_sources_are_lf_checkout_stable() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "cipher_development/shared/*.py text eol=lf" in attributes
    assert "cipher_development/two_period_overlay/*.py text eol=lf" in attributes

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for row in manifest["retained_sources"]:
        relpath = row["path"]
        assert relpath.startswith((
            "cipher_development/shared/",
            "cipher_development/two_period_overlay/",
        ))
        assert (ROOT / relpath).read_bytes().count(b"\r\n") == 0


def test_fixture_manifest_is_exact_tracked_pack09_closure() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema"] == "rdp_two_period_fixture_manifest.v1"
    assert manifest["entry_point"] == "cipher_development/two_period_overlay/pack09.py"
    retained = {row["path"] for row in manifest["retained_sources"]}
    assert retained == _local_import_closure(manifest["entry_point"])
    for row in manifest["retained_sources"]:
        path = ROOT / row["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
        assert path.suffix == ".py"


def test_fixture_policy_excludes_historical_runners_and_generated_material() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    retained = {row["path"] for row in manifest["retained_sources"]}
    excluded = set(manifest["excluded_historical_sources"])
    assert "cipher_development/two_period_overlay/pack04.py" in excluded
    assert "cipher_development/two_period_overlay/experiment_a.py" in excluded
    assert not retained & excluded
    assert manifest["production_wheel_included"] is False
    assert manifest["curated_source_release_included"] is True
    policy = manifest["generated_material_policy"]
    assert policy["outputs"] == "excluded"
    assert policy["assets"] == "excluded"
    assert policy["binaries"] == "excluded"
    assert policy["caches"] == "excluded"


def test_a1_dependency_review_is_preserved_and_closed() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    review = manifest["dependency_review"]
    assert review == {
        "review_date": "2026-07-30",
        "closure_changed": False,
        "reviewed_changed_dependencies": [
            "cipher_development/shared/archive.py",
            "cipher_development/shared/experiment.py",
            "cipher_development/shared/ledger.py",
            "cipher_development/shared/replay.py",
            "cipher_development/shared/replay_binding.py",
            "cipher_development/shared/replay_evidence.py",
            "cipher_development/shared/replay_execution.py",
            "cipher_development/shared/replay_provenance.py",
        ],
        "decision": "retain_current_closure_and_refresh_hashes",
        "production_package_boundary_changed": False,
    }


def test_refresh_refuses_unmanifested_dependency(tmp_path: Path) -> None:
    from tools.refresh_two_period_fixture_manifest import refresh_manifest

    entry = tmp_path / "cipher_development" / "two_period_overlay" / "pack09.py"
    extra = tmp_path / "cipher_development" / "shared" / "extra.py"
    entry.parent.mkdir(parents=True)
    extra.parent.mkdir(parents=True)
    entry.write_text("import cipher_development.shared.extra\n", encoding="utf-8")
    extra.write_text("VALUE = 1\n", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "entry_point": "cipher_development/two_period_overlay/pack09.py",
            "retained_sources": [{
                "path": "cipher_development/two_period_overlay/pack09.py",
                "sha256": hashlib.sha256(entry.read_bytes()).hexdigest(),
                "role": "entry point",
            }],
        }),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="unmanifested=.*extra.py"):
        refresh_manifest(tmp_path, manifest_path)
