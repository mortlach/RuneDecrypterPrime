from __future__ import annotations

import json
from pathlib import Path

from rune_decrypter_prime.api.artifact_agreement import agreement_manifest_row_by_kind_v1
from rune_decrypter_prime.api.run_artifact_manifest import (
    MANIFEST_RELPATH,
    _build_v1_rows,
    _validate_rows_match_agreement,
    write_run_artifacts_manifest,
)


def _write_required_files(run_dir: Path) -> None:
    (run_dir / "config").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "META.json").write_text("{}\n", encoding="utf-8")
    (run_dir / "config" / "logging.json").write_text("{}\n", encoding="utf-8")


def test_manifest_rows_match_v1_artifact_agreement(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / "artifacts" / "solver_report.json").write_text("{}\n", encoding="utf-8")

    rows = _build_v1_rows(tmp_path, include_solver_report=True)
    rows_by_kind = agreement_manifest_row_by_kind_v1()

    assert [row.artifact_kind for row in rows] == ["run_meta", "logging_config", "solver_report"]
    for row in rows:
        agreement = rows_by_kind[row.artifact_kind]
        assert row.relpath == agreement.relpath
        assert row.required == agreement.required
        assert row.portable_classification == agreement.portable_classification
        assert row.export_classification == agreement.export_classification
        assert row.notes == agreement.notes
    _validate_rows_match_agreement(rows)


def test_written_manifest_is_small_agreement_backed_document(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / "artifacts" / "solver_report.json").write_text("{}\n", encoding="utf-8")

    relpath = write_run_artifacts_manifest(run_dir=tmp_path, include_solver_report=True)

    assert relpath == MANIFEST_RELPATH
    payload = json.loads((tmp_path / relpath).read_text(encoding="utf-8"))
    assert payload["manifest_version"] == "api_run_artifacts.v1"
    assert [row["relpath"] for row in payload["rows"]] == [
        "META.json",
        "config/logging.json",
        "artifacts/solver_report.json",
    ]
    assert MANIFEST_RELPATH not in {row["relpath"] for row in payload["rows"]}


def test_logs_trace_and_raw_assets_remain_outside_manifest(tmp_path: Path) -> None:
    _write_required_files(tmp_path)
    (tmp_path / "logs").mkdir()
    (tmp_path / "trace").mkdir()
    (tmp_path / "assets").mkdir()
    (tmp_path / "logs" / "app.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "trace" / "sample.txt").write_text("trace\n", encoding="utf-8")
    (tmp_path / "assets" / "runtime_index.bin").write_bytes(b"asset")

    write_run_artifacts_manifest(run_dir=tmp_path)

    payload = json.loads((tmp_path / MANIFEST_RELPATH).read_text(encoding="utf-8"))
    relpaths = {row["relpath"] for row in payload["rows"]}
    assert "logs/app.jsonl" not in relpaths
    assert "trace/sample.txt" not in relpaths
    assert "assets/runtime_index.bin" not in relpaths
