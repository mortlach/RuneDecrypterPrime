from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from rdp import api
from rdp.core.config.solution import Solution


def _request(logging: api.LoggingConfig | None = None) -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.RuneIndexInput(indices=(0,)),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=1),
        solver=api.SolverSpec.beam_search(width=1, rounds=0),
        logging=logging,
        telemetry_enabled=False,
    )


def _patch_execution(monkeypatch: pytest.MonkeyPatch, run_dir: Path) -> None:
    run_module = importlib.import_module("rdp.api.run")
    monkeypatch.setattr(
        run_module,
        "execute_run",
        lambda **_kwargs: Solution(key=[1], plaintext=[0], score=1.0),
    )
    monkeypatch.setattr(run_module, "get_run_dir", lambda: run_dir)
    (run_dir / "config").mkdir(parents=True)
    (run_dir / "artifacts").mkdir(parents=True)
    (run_dir / "META.json").write_text("{}\n", encoding="utf-8")
    (run_dir / "config" / "logging.json").write_text("{}\n", encoding="utf-8")


def test_run_without_logging_writes_no_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_execution(monkeypatch, tmp_path)
    api.run(_request())
    assert not (tmp_path / "artifacts" / "run_artifacts_manifest.json").exists()


def test_run_writes_requested_solver_report_and_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_execution(monkeypatch, tmp_path)
    api.run(
        _request(
            api.LoggingConfig(
                write_solver_report=True,
                write_artifact_manifest=True,
            )
        )
    )
    assert (tmp_path / "artifacts" / "solver_report.json").is_file()
    payload = json.loads(
        (tmp_path / "artifacts" / "run_artifacts_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["manifest_version"] == "api_run_artifacts.v1"
    assert [row["relpath"] for row in payload["rows"]] == [
        "META.json",
        "config/logging.json",
        "artifacts/solver_report.json",
    ]


@pytest.mark.parametrize(
    "field", ("write_solver_report", "write_display_summary", "write_artifact_manifest")
)
def test_logging_artifact_flags_require_exact_bool(field: str) -> None:
    with pytest.raises(TypeError, match=field):
        api.LoggingConfig(**{field: 1})
