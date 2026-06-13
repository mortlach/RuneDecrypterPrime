from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

Classification = Literal["candidate", "not_candidate", "needs_review"]

MANIFEST_RELPATH = "artifacts/run_artifacts_manifest.json"


@dataclass(frozen=True, slots=True)
class RunArtifactManifestRow:
    relpath: str
    artifact_kind: str
    required: bool
    present: bool
    portable_classification: Classification
    export_classification: Classification
    notes: str | None = None

    def __post_init__(self) -> None:
        _validate_relpath(self.relpath)
        if not isinstance(self.artifact_kind, str) or not self.artifact_kind:
            raise ValueError("artifact_kind must be a non-empty string")
        if type(self.required) is not bool:
            raise TypeError("required must be a bool")
        if type(self.present) is not bool:
            raise TypeError("present must be a bool")
        _validate_classification(self.portable_classification, "portable_classification")
        _validate_classification(self.export_classification, "export_classification")
        if self.notes is not None and not isinstance(self.notes, str):
            raise TypeError("notes must be a string or None")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "relpath": self.relpath,
            "artifact_kind": self.artifact_kind,
            "required": self.required,
            "present": self.present,
            "portable_classification": self.portable_classification,
            "export_classification": self.export_classification,
            "notes": self.notes,
        }


def write_run_artifacts_manifest(
    *,
    run_dir: Path,
    include_solver_report: bool = False,
) -> str:
    if not isinstance(run_dir, Path):
        raise TypeError("run_dir must be a Path")
    if type(include_solver_report) is not bool:
        raise TypeError("include_solver_report must be a bool")

    run_root = run_dir.resolve()
    _require_existing_file(run_root, "META.json")
    _require_existing_file(run_root, "config/logging.json")

    rows = _build_v1_rows(run_root, include_solver_report=include_solver_report)
    payload = {
        "manifest_version": "api_run_artifacts.v1",
        "rows": [row.to_json_dict() for row in rows],
    }

    manifest_path = (run_root / MANIFEST_RELPATH).resolve()
    if not manifest_path.is_relative_to(run_root):
        raise ValueError("run artifact manifest path must be under run_dir")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return MANIFEST_RELPATH


def _build_v1_rows(
    run_root: Path,
    *,
    include_solver_report: bool,
) -> tuple[RunArtifactManifestRow, ...]:
    solver_report_relpath = "artifacts/solver_report.json"
    solver_report_path = run_root / solver_report_relpath
    rows: list[RunArtifactManifestRow] = [
        RunArtifactManifestRow(
            relpath="META.json",
            artifact_kind="run_meta",
            required=True,
            present=True,
            portable_classification="candidate",
            export_classification="candidate",
            notes="privacy-sensitive run metadata",
        ),
        RunArtifactManifestRow(
            relpath="config/logging.json",
            artifact_kind="logging_config",
            required=True,
            present=True,
            portable_classification="candidate",
            export_classification="candidate",
            notes="privacy-sensitive logging configuration snapshot",
        ),
    ]

    if include_solver_report:
        if not solver_report_path.is_file():
            raise FileNotFoundError("required artifact is missing: artifacts/solver_report.json")
        rows.append(_solver_report_row(present=True))
    elif solver_report_path.is_file():
        rows.append(_solver_report_row(present=True))

    _validate_unique_rows(rows)
    return tuple(rows)


def _solver_report_row(*, present: bool) -> RunArtifactManifestRow:
    return RunArtifactManifestRow(
        relpath="artifacts/solver_report.json",
        artifact_kind="solver_report",
        required=False,
        present=present,
        portable_classification="candidate",
        export_classification="candidate",
        notes="stable-readable SolverReport sidecar",
    )


def _require_existing_file(run_root: Path, relpath: str) -> None:
    _validate_relpath(relpath)
    path = (run_root / relpath).resolve()
    if not path.is_relative_to(run_root):
        raise ValueError(f"artifact path escapes run_dir: {relpath}")
    if not path.is_file():
        raise FileNotFoundError(f"required artifact is missing: {relpath}")


def _validate_unique_rows(rows: Iterable[RunArtifactManifestRow]) -> None:
    relpaths: set[str] = set()
    artifact_kinds: set[str] = set()
    for row in rows:
        if row.relpath in relpaths:
            raise ValueError(f"duplicate manifest relpath: {row.relpath}")
        relpaths.add(row.relpath)
        if row.artifact_kind in artifact_kinds:
            raise ValueError(f"duplicate manifest artifact_kind: {row.artifact_kind}")
        artifact_kinds.add(row.artifact_kind)


def _validate_relpath(relpath: str) -> None:
    if not isinstance(relpath, str) or not relpath:
        raise ValueError("relpath must be a non-empty string")
    if "\\" in relpath:
        raise ValueError("relpath must use POSIX separators")
    if relpath.startswith("/"):
        raise ValueError("relpath must be run-relative and stay under run_dir")
    path = Path(relpath)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("relpath must be run-relative and stay under run_dir")


def _validate_classification(value: str, field_name: str) -> None:
    allowed = {"candidate", "not_candidate", "needs_review"}
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")


__all__ = [
    "MANIFEST_RELPATH",
    "RunArtifactManifestRow",
    "write_run_artifacts_manifest",
]
