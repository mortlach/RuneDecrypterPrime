from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rune_decrypter_prime.api.artifact_agreement import (
    Classification,
    ArtifactKind,
    KnownArtifactRelpath,
    RunArtifactManifestVersion,
    assert_manifest_row_allowed_v1,
    agreement_manifest_row_by_kind_v1,
    ensure_artifact_classification,
    ensure_artifact_kind,
    ensure_known_artifact_relpath,
    validate_artifact_relpath,
)

MANIFEST_RELPATH = KnownArtifactRelpath.RUN_ARTIFACTS_MANIFEST.value


@dataclass(frozen=True, slots=True)
class RunArtifactManifestRow:
    """Manifest row for a known V1 run artifact.

    Rows record which agreement-backed artifacts were present for a run. Paths
    are known run-relative POSIX relpaths, classifications come from the V1
    artifact agreement, and `present` records observed output state for this
    particular run.
    """

    relpath: KnownArtifactRelpath | str
    artifact_kind: ArtifactKind | str
    required: bool
    present: bool
    portable_classification: Classification | str
    export_classification: Classification | str
    notes: str | None = None

    def __post_init__(self) -> None:
        relpath = ensure_known_artifact_relpath(self.relpath)
        artifact_kind = ensure_artifact_kind(self.artifact_kind)
        portable_classification = ensure_artifact_classification(self.portable_classification)
        export_classification = ensure_artifact_classification(self.export_classification)

        validate_artifact_relpath(relpath.value)
        object.__setattr__(self, "relpath", relpath)
        object.__setattr__(self, "artifact_kind", artifact_kind)
        object.__setattr__(self, "portable_classification", portable_classification)
        object.__setattr__(self, "export_classification", export_classification)

        if type(self.required) is not bool:
            raise TypeError("required must be a bool")
        if type(self.present) is not bool:
            raise TypeError("present must be a bool")
        if self.notes is not None and not isinstance(self.notes, str):
            raise TypeError("notes must be a string or None")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "relpath": self.relpath.value,
            "artifact_kind": self.artifact_kind.value,
            "required": self.required,
            "present": self.present,
            "portable_classification": self.portable_classification.value,
            "export_classification": self.export_classification.value,
            "notes": self.notes,
        }


def write_run_artifacts_manifest(
    *,
    run_dir: Path,
    include_solver_report: bool = False,
) -> str:
    """Write the V1 run artifact manifest under `run_dir`.

    The run directory must already contain `META.json` and
    `config/logging.json`. Optional solver report and display summary artifacts
    are listed when present, and the solver report can be required by setting
    `include_solver_report=True`.

    Returns the run-relative manifest path.
    """

    if not isinstance(run_dir, Path):
        raise TypeError("run_dir must be a Path")
    if type(include_solver_report) is not bool:
        raise TypeError("include_solver_report must be a bool")

    run_root = run_dir.resolve()
    _require_existing_file(run_root, KnownArtifactRelpath.RUN_META.value)
    _require_existing_file(run_root, KnownArtifactRelpath.LOGGING_CONFIG.value)

    rows = _build_v1_rows(run_root, include_solver_report=include_solver_report)
    payload = {
        "manifest_version": RunArtifactManifestVersion.V1.value,
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
    solver_report_relpath = KnownArtifactRelpath.SOLVER_REPORT.value
    solver_report_path = run_root / solver_report_relpath
    display_summary_relpath = KnownArtifactRelpath.RDP_DISPLAY_SUMMARY.value
    display_summary_path = run_root / display_summary_relpath
    rows: list[RunArtifactManifestRow] = [
        _row_from_agreement(ArtifactKind.RUN_META, present=True),
        _row_from_agreement(ArtifactKind.LOGGING_CONFIG, present=True),
    ]

    if include_solver_report:
        if not solver_report_path.is_file():
            raise FileNotFoundError(f"required artifact is missing: {solver_report_relpath}")
        rows.append(_row_from_agreement(ArtifactKind.SOLVER_REPORT, present=True))
    elif solver_report_path.is_file():
        rows.append(_row_from_agreement(ArtifactKind.SOLVER_REPORT, present=True))

    if display_summary_path.is_file():
        rows.append(_row_from_agreement(ArtifactKind.RDP_DISPLAY_SUMMARY, present=True))

    _validate_unique_rows(rows)
    _validate_rows_match_agreement(rows)
    return tuple(rows)


def _row_from_agreement(artifact_kind: ArtifactKind | str, *, present: bool) -> RunArtifactManifestRow:
    artifact_kind_enum = ensure_artifact_kind(artifact_kind)
    agreement = agreement_manifest_row_by_kind_v1().get(artifact_kind_enum.value)
    if agreement is None:
        raise ValueError(f"artifact kind is not in the V1 manifest agreement: {artifact_kind_enum.value}")
    return RunArtifactManifestRow(
        relpath=agreement.relpath,
        artifact_kind=agreement.artifact_kind,
        required=agreement.required,
        present=present,
        portable_classification=agreement.portable_classification,
        export_classification=agreement.export_classification,
        notes=agreement.notes,
    )


def _require_existing_file(run_root: Path, relpath: str) -> None:
    validate_artifact_relpath(relpath)
    path = (run_root / relpath).resolve()
    if not path.is_relative_to(run_root):
        raise ValueError(f"artifact path escapes run_dir: {relpath}")
    if not path.is_file():
        raise FileNotFoundError(f"required artifact is missing: {relpath}")


def _validate_unique_rows(rows: Iterable[RunArtifactManifestRow]) -> None:
    relpaths: set[KnownArtifactRelpath] = set()
    artifact_kinds: set[ArtifactKind] = set()
    for row in rows:
        if row.relpath in relpaths:
            raise ValueError(f"duplicate manifest relpath: {row.relpath.value}")
        relpaths.add(row.relpath)
        if row.artifact_kind in artifact_kinds:
            raise ValueError(f"duplicate manifest artifact_kind: {row.artifact_kind.value}")
        artifact_kinds.add(row.artifact_kind)


def _validate_rows_match_agreement(rows: Iterable[RunArtifactManifestRow]) -> None:
    for row in rows:
        assert_manifest_row_allowed_v1(
            relpath=row.relpath.value,
            artifact_kind=row.artifact_kind.value,
            portable_classification=row.portable_classification.value,
            export_classification=row.export_classification.value,
        )


__all__ = [
    "MANIFEST_RELPATH",
    "RunArtifactManifestRow",
    "write_run_artifacts_manifest",
]
