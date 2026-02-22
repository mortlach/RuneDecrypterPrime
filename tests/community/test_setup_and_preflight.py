from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from tools.benchmarks.community import setup_and_preflight as sp

pytestmark = pytest.mark.tier_a


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def test_manifest_parsing_accepts_required_assets_contract(tmp_path: Path):
    manifest = {
        "assets_root": "assets",
        "packed_root": "assets_packed",
        "required_assets": [
            {
                "final_relpath": "language_model/lmp/sample.bin",
                "sha256": "a" * 64,
                "size_bytes": 12,
                "parts": ["lm/sample.bin.part001", "lm/sample.bin.part002"],
            }
        ],
    }
    p = tmp_path / "assets_manifest_v1.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    raw, read_issues = sp._read_manifest(p)
    assert read_issues == []
    assets, parse_issues = sp._parse_required_assets(raw)
    assert parse_issues == []
    assert len(assets) == 1
    assert assets[0].final_relpath == "language_model/lmp/sample.bin"
    assert assets[0].size_bytes == 12
    assert assets[0].parts == ("lm/sample.bin.part001", "lm/sample.bin.part002")


def test_manifest_parsing_accepts_forward_links():
    manifest = {
        "required_assets": [],
        "forward_links": [
            {
                "link_relpath": "language_model/lmp",
                "target_relpath": "src/rune_decrypter_prime/data/language_model/lmp",
            }
        ],
    }
    links, issues = sp._parse_forward_links(manifest)
    assert issues == []
    assert links == [
        sp.ForwardLink(
            link_relpath="language_model/lmp",
            target_relpath="src/rune_decrypter_prime/data/language_model/lmp",
        )
    ]


def test_recombine_required_assets_success_and_idempotent(tmp_path: Path):
    repo_root = tmp_path
    packed_root = repo_root / "assets_packed" / "lm"
    packed_root.mkdir(parents=True, exist_ok=True)
    part1 = b"hello "
    part2 = b"world"
    (packed_root / "sample.bin.part001").write_bytes(part1)
    (packed_root / "sample.bin.part002").write_bytes(part2)
    full = part1 + part2

    asset = sp.RequiredAsset(
        final_relpath="language_model/lmp/sample.bin",
        sha256=_sha256_bytes(full),
        size_bytes=len(full),
        parts=("lm/sample.bin.part001", "lm/sample.bin.part002"),
    )

    out1 = sp.recombine_required_assets(
        repo_root=repo_root,
        assets_root="assets",
        packed_root="assets_packed",
        required_assets=[asset],
        setup_log=io.StringIO(),
    )
    assert out1["issues"] == []
    assert out1["recombined_assets_count"] == 1
    assert out1["verified_assets_count"] == 1
    final_path = repo_root / "assets" / "language_model" / "lmp" / "sample.bin"
    assert final_path.read_bytes() == full

    out2 = sp.recombine_required_assets(
        repo_root=repo_root,
        assets_root="assets",
        packed_root="assets_packed",
        required_assets=[asset],
        setup_log=io.StringIO(),
    )
    assert out2["issues"] == []
    assert out2["recombined_assets_count"] == 0
    assert out2["already_valid_assets_count"] == 1
    assert out2["verified_assets_count"] == 1


def test_recombine_required_assets_reports_hash_or_size_mismatch(tmp_path: Path):
    repo_root = tmp_path
    packed_root = repo_root / "assets_packed"
    packed_root.mkdir(parents=True, exist_ok=True)
    (packed_root / "bad.part").write_bytes(b"abcdef")

    asset = sp.RequiredAsset(
        final_relpath="language_model/lmp/bad.bin",
        sha256="0" * 64,
        size_bytes=123,  # intentionally wrong
        parts=("bad.part",),
    )
    out = sp.recombine_required_assets(
        repo_root=repo_root,
        assets_root="assets",
        packed_root="assets_packed",
        required_assets=[asset],
        setup_log=io.StringIO(),
    )
    assert out["issues"]
    statuses = [row["status"] for row in out["details"]]
    assert statuses in (["size_mismatch"], ["sha_mismatch"])


def test_apply_forward_links_calls_link_creation(monkeypatch, tmp_path: Path):
    repo_root = tmp_path
    (repo_root / "src" / "rune_decrypter_prime" / "data" / "language_model" / "lmp").mkdir(parents=True, exist_ok=True)
    created: list[tuple[Path, Path]] = []

    def fake_create_link(link_path: Path, target_path: Path) -> None:
        created.append((link_path, target_path))
        link_path.mkdir(parents=True, exist_ok=True)
        (link_path / "_target.txt").write_text(str(target_path), encoding="utf-8")

    monkeypatch.setattr(sp, "_create_link", fake_create_link)
    monkeypatch.setattr(sp, "_paths_equivalent", lambda a, b: a.exists() and b.exists())

    out = sp.apply_forward_links(
        repo_root=repo_root,
        assets_root="assets",
        links=[
            sp.ForwardLink(
                link_relpath="language_model/lmp",
                target_relpath="src/rune_decrypter_prime/data/language_model/lmp",
            )
        ],
        setup_log=io.StringIO(),
    )
    assert out["issues"] == []
    assert out["created_links_count"] == 1
    assert created


def test_apply_forward_links_accepts_existing_materialized_directory(tmp_path: Path):
    repo_root = tmp_path
    target = repo_root / "src" / "rune_decrypter_prime" / "data" / "language_model" / "lmp"
    target.mkdir(parents=True, exist_ok=True)
    existing = repo_root / "assets" / "language_model" / "lmp"
    existing.mkdir(parents=True, exist_ok=True)
    (existing / "index.json").write_text("{}", encoding="utf-8")

    out = sp.apply_forward_links(
        repo_root=repo_root,
        assets_root="assets",
        links=[sp.ForwardLink(link_relpath="language_model/lmp", target_relpath="src/rune_decrypter_prime/data/language_model/lmp")],
        setup_log=io.StringIO(),
    )
    assert out["issues"] == []
    assert out["already_linked_count"] == 1
    assert out["details"][0]["status"] == "already_materialized"


def test_apply_forward_links_replaces_stale_existing_path(monkeypatch, tmp_path: Path):
    repo_root = tmp_path
    target = repo_root / "src" / "rune_decrypter_prime" / "data" / "language_model" / "lmp"
    target.mkdir(parents=True, exist_ok=True)
    stale = repo_root / "assets" / "language_model" / "lmp"
    stale.mkdir(parents=True, exist_ok=True)
    (stale / "rtl").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(sp, "_create_link", lambda link_path, _target_path: link_path.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(
        sp,
        "_paths_equivalent",
        lambda path_a, _path_b: path_a.exists() and not (path_a / "rtl").exists(),
    )

    out = sp.apply_forward_links(
        repo_root=repo_root,
        assets_root="assets",
        links=[sp.ForwardLink(link_relpath="language_model/lmp", target_relpath="src/rune_decrypter_prime/data/language_model/lmp")],
        setup_log=io.StringIO(),
    )
    assert out["issues"] == []
    assert out["created_links_count"] == 1
    assert out["details"][0]["status"] == "linked"


def test_import_fastlm_uses_expected_module_path(monkeypatch, tmp_path: Path):
    seen: list[str] = []

    def fake_import(name: str):
        seen.append(name)
        raise ModuleNotFoundError("test")

    monkeypatch.setattr(sp.importlib, "import_module", fake_import)
    ok, _err = sp._import_fastlm(tmp_path)
    assert ok is False
    assert seen == [sp.FASTLM_MODULE]


def test_ensure_fastlm_reports_missing_when_build_disabled(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "_import_fastlm", lambda _repo: (False, "missing"))
    report = sp.ensure_fastlm(tmp_path, allow_build=False, setup_log=io.StringIO())
    assert report["fastlm_present"] is False
    assert report["build_attempted"] is False
    assert report["issues"]


def test_run_setup_and_preflight_writes_reports_and_ready_marker(monkeypatch, tmp_path: Path):
    manifest = {"assets_root": "assets", "packed_root": "assets_packed", "required_assets": [], "forward_links": []}
    (tmp_path / "assets_manifest_v1.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "assets_packed").mkdir(exist_ok=True)
    (tmp_path / "assets").mkdir(exist_ok=True)

    monkeypatch.setattr(
        sp,
        "ensure_fastlm",
        lambda *_args, **_kwargs: {
            "fastlm_present": True,
            "build_attempted": False,
            "build_succeeded": False,
            "issues": [],
        },
    )
    monkeypatch.setattr(
        sp,
        "run_preflight",
        lambda **_kwargs: {
            "timestamp_utc": "now",
            "success": True,
            "device": "cpu",
            "scoring_backend": "numpy",
            "fastlm_present": True,
            "checks": [],
            "issues": [],
            "probe_details": {},
        },
    )

    rc = sp.run_setup_and_preflight(tmp_path, skip_fastlm_build=True)
    assert rc == 0
    latest = sp.latest_setup_bundle_dir(tmp_path)
    assert latest is not None
    assert (latest / "setup.log").exists()
    assert (latest / "preflight.log").exists()
    assert (latest / "setup_report.json").exists()
    assert (latest / "preflight_report.json").exists()
    assert (latest / "benchmark_ready.json").exists()
    assert not (tmp_path / "setup_report.json").exists()
    assert not (tmp_path / "preflight_report.json").exists()
    assert not (tmp_path / "benchmark_ready.json").exists()


def test_run_setup_and_preflight_fails_when_manifest_invalid(tmp_path: Path):
    (tmp_path / "assets_manifest_v1.json").write_text("{}", encoding="utf-8")
    rc = sp.run_setup_and_preflight(tmp_path, skip_fastlm_build=True)
    assert rc == 1
    out_root = tmp_path / "output" / "tools" / "benchmarks" / "community" / "setup_preflight"
    run_dirs = [p for p in out_root.iterdir() if p.is_dir() and p.name != sp.SETUP_LATEST_DIRNAME]
    assert run_dirs, "expected setup/preflight run directory"
    run_dir = sorted(run_dirs)[-1]
    assert (run_dir / "setup_report.json").exists()
    assert (run_dir / "preflight_report.json").exists()
    assert not (run_dir / "benchmark_ready.json").exists()


def test_latest_setup_bundle_dir_legacy_fallback(tmp_path: Path):
    (tmp_path / "setup.log").write_text("ok\n", encoding="utf-8")
    (tmp_path / "setup_report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "preflight.log").write_text("ok\n", encoding="utf-8")
    (tmp_path / "preflight_report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "benchmark_ready.json").write_text("{}", encoding="utf-8")
    resolved = sp.latest_setup_bundle_dir(tmp_path)
    assert resolved == tmp_path
