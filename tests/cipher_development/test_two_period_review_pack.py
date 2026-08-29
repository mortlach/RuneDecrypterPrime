from __future__ import annotations
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import pytest
from cipher_development.two_period_overlay import review_pack

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _synthetic_pack09_run(root: Path) -> Path:
    run = root / "synthetic_pack09_run"
    _write_json(
        run / "artifacts/experiment_manifest.json",
        {
            "experiment": {
                "experiment_id": review_pack.PACK09_EXPERIMENT_ID,
                "benchmark_id": "synthetic_pack09",
            }
        },
    )
    _write_json(
        run / "artifacts/experiment_result.json",
        {
            "experiment_id": review_pack.PACK09_EXPERIMENT_ID,
            "status": "completed",
            "decision": "refine",
            "stop_reason": "done",
            "reference_evaluation": {"synthetic_terminal_only": True},
        },
    )
    _write_json(
        run / "artifacts/experiment_e/required_artifacts.json",
        {"schema": "synthetic.pack09.required.v1", "paths": []},
    )
    for relative in review_pack._required_artifacts(run):
        path = run / relative
        if not path.exists():
            _write_json(path, {"schema": "synthetic.pack09.artifact.v1"})
    return run


def test_fixture_manifest_is_the_real_tree_source_authority() -> None:
    rows = review_pack.fixture_source_records(REPO_ROOT)
    manifest = json.loads(
        (REPO_ROOT / review_pack.FIXTURE_MANIFEST).read_text(encoding="utf-8")
    )
    expected = {row["path"] for row in manifest["retained_sources"]}
    assert {row["path"] for row in rows} == expected
    assert all(((REPO_ROOT / row["path"]).is_file() for row in rows))


def test_pack09_packages_synthetic_external_run_end_to_end(tmp_path: Path) -> None:
    run = _synthetic_pack09_run(tmp_path / "external-runs")
    output = tmp_path / "external-review-packs"
    result = review_pack.write_review_pack(REPO_ROOT, run, output_root=output)
    assert result.pack_complete is True
    assert result.review_ready is True
    assert result.path.parent == output.resolve()
    with ZipFile(result.path) as archive:
        names = set(archive.namelist())
        assert "review_manifest.json" in names
        assert "file_inventory.sha256" in names
        assert f"source/{review_pack.FIXTURE_MANIFEST.as_posix()}" in names
        manifest = json.loads(archive.read("review_manifest.json"))
        assert manifest["source_authority"] == review_pack.FIXTURE_MANIFEST.as_posix()
        assert manifest["pack_complete"] is True
        inventory = archive.read("file_inventory.sha256").decode("ascii").splitlines()
        for line in inventory:
            expected_hash, member = line.split("  ", 1)
            assert hashlib.sha256(archive.read(member)).hexdigest() == expected_hash


def test_pack09_review_pack_requires_explicit_external_roots(tmp_path: Path) -> None:
    run = _synthetic_pack09_run(tmp_path / "external-runs")
    with pytest.raises(ValueError, match="absolute external"):
        review_pack.write_review_pack(REPO_ROOT, Path("relative"), output_root=tmp_path)
    with pytest.raises(ValueError, match="outside the repository"):
        review_pack.write_review_pack(
            REPO_ROOT, run, output_root=REPO_ROOT / "output/review-packs"
        )


def test_review_pack_rejects_non_pack09_runs(tmp_path: Path) -> None:
    run = _synthetic_pack09_run(tmp_path / "external-runs")
    manifest_path = run / "artifacts/experiment_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["experiment"]["experiment_id"] = "historical_runner"
    _write_json(manifest_path, payload)
    with pytest.raises(ValueError, match="supports only Pack 09"):
        review_pack.write_review_pack(
            REPO_ROOT, run, output_root=tmp_path / "external-review-packs"
        )


def test_packaging_failure_does_not_mask_scientific_error(tmp_path: Path) -> None:
    error = RuntimeError("scientific failure")
    result = review_pack.write_review_pack_after_run(
        REPO_ROOT,
        tmp_path / "missing-run",
        output_root=tmp_path / "external-review-packs",
        original_error=error,
    )
    assert result is None
    assert any(("review-pack generation failed" in note for note in error.__notes__))
