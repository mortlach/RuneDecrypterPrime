from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable


class ArtifactClassification(StrEnum):
    CANDIDATE = "candidate"
    NOT_CANDIDATE = "not_candidate"
    NEEDS_REVIEW = "needs_review"


class ArtifactKind(StrEnum):
    RUN_META = "run_meta"
    LOGGING_CONFIG = "logging_config"
    SOLVER_REPORT = "solver_report"
    RUN_ARTIFACTS_MANIFEST = "run_artifacts_manifest"


class KnownArtifactRelpath(StrEnum):
    RUN_META = "META.json"
    LOGGING_CONFIG = "config/logging.json"
    SOLVER_REPORT = "artifacts/solver_report.json"
    RUN_ARTIFACTS_MANIFEST = "artifacts/run_artifacts_manifest.json"


class ArtifactAgreementVersion(StrEnum):
    V1 = "api_run_artifact_agreement.v1"


class RunArtifactManifestVersion(StrEnum):
    V1 = "api_run_artifacts.v1"


AGREEMENT_VERSION = ArtifactAgreementVersion.V1.value
ALLOWED_CLASSIFICATIONS = frozenset(item.value for item in ArtifactClassification)


def ensure_artifact_classification(value: ArtifactClassification | str) -> ArtifactClassification:
    if isinstance(value, ArtifactClassification):
        return value
    try:
        return ArtifactClassification(str(value))
    except ValueError as exc:
        raise ValueError(f"artifact classification must be one of {sorted(ALLOWED_CLASSIFICATIONS)}") from exc


def ensure_artifact_kind(value: ArtifactKind | str) -> ArtifactKind:
    if isinstance(value, ArtifactKind):
        return value
    try:
        return ArtifactKind(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in ArtifactKind)
        raise ValueError(f"artifact_kind must be one of {allowed}") from exc


def ensure_known_artifact_relpath(value: KnownArtifactRelpath | str) -> KnownArtifactRelpath:
    if isinstance(value, KnownArtifactRelpath):
        return value
    try:
        return KnownArtifactRelpath(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in KnownArtifactRelpath)
        raise ValueError(f"relpath must be one of the V1 known artifact paths: {allowed}") from exc


@dataclass(frozen=True, slots=True)
class ArtifactAgreementRow:
    """V1 review/export contract for a known run artifact.

    The agreement is intentionally separate from the runtime manifest. It says
    which artifacts V1 knows how to review or export; the manifest says which of
    those artifacts were actually written for a particular run.
    """

    relpath: KnownArtifactRelpath | str
    artifact_kind: ArtifactKind | str
    required: bool
    portable_classification: ArtifactClassification | str
    export_classification: ArtifactClassification | str
    review_required: bool
    listed_in_manifest: bool = True
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
        if type(self.review_required) is not bool:
            raise TypeError("review_required must be a bool")
        if type(self.listed_in_manifest) is not bool:
            raise TypeError("listed_in_manifest must be a bool")
        if self.notes is not None and not isinstance(self.notes, str):
            raise TypeError("notes must be a string or None")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "relpath": self.relpath.value,
            "artifact_kind": self.artifact_kind.value,
            "required": self.required,
            "portable_classification": self.portable_classification.value,
            "export_classification": self.export_classification.value,
            "review_required": self.review_required,
            "listed_in_manifest": self.listed_in_manifest,
            "notes": self.notes,
        }


def artifact_agreement_v1() -> tuple[ArtifactAgreementRow, ...]:
    """Return the stable V1 agreement rows in canonical order."""

    rows = (
        ArtifactAgreementRow(
            relpath=KnownArtifactRelpath.RUN_META,
            artifact_kind=ArtifactKind.RUN_META,
            required=True,
            portable_classification=ArtifactClassification.CANDIDATE,
            export_classification=ArtifactClassification.CANDIDATE,
            review_required=True,
            notes="run metadata; review before export",
        ),
        ArtifactAgreementRow(
            relpath=KnownArtifactRelpath.LOGGING_CONFIG,
            artifact_kind=ArtifactKind.LOGGING_CONFIG,
            required=True,
            portable_classification=ArtifactClassification.CANDIDATE,
            export_classification=ArtifactClassification.CANDIDATE,
            review_required=True,
            notes="logging configuration snapshot; review before export",
        ),
        ArtifactAgreementRow(
            relpath=KnownArtifactRelpath.SOLVER_REPORT,
            artifact_kind=ArtifactKind.SOLVER_REPORT,
            required=False,
            portable_classification=ArtifactClassification.CANDIDATE,
            export_classification=ArtifactClassification.CANDIDATE,
            review_required=True,
            notes="stable-readable SolverReport sidecar; review before export",
        ),
        ArtifactAgreementRow(
            relpath=KnownArtifactRelpath.RUN_ARTIFACTS_MANIFEST,
            artifact_kind=ArtifactKind.RUN_ARTIFACTS_MANIFEST,
            required=True,
            portable_classification=ArtifactClassification.CANDIDATE,
            export_classification=ArtifactClassification.CANDIDATE,
            review_required=True,
            listed_in_manifest=False,
            notes="manifest generated by the run; not listed as its own input row",
        ),
    )
    validate_artifact_agreement_rows(rows)
    return rows


def manifest_agreement_rows_v1() -> tuple[ArtifactAgreementRow, ...]:
    """Agreement rows that may appear as rows in run_artifacts_manifest.json."""

    return tuple(row for row in artifact_agreement_v1() if row.listed_in_manifest)


def agreement_row_by_kind_v1() -> dict[str, ArtifactAgreementRow]:
    return {row.artifact_kind.value: row for row in artifact_agreement_v1()}


def agreement_manifest_row_by_kind_v1() -> dict[str, ArtifactAgreementRow]:
    return {row.artifact_kind.value: row for row in manifest_agreement_rows_v1()}


def assert_manifest_row_allowed_v1(
    *,
    relpath: str,
    artifact_kind: str,
    portable_classification: str,
    export_classification: str,
) -> None:
    """Validate that a manifest row matches the V1 agreement."""

    rows = agreement_manifest_row_by_kind_v1()
    row = rows.get(artifact_kind)
    if row is None:
        raise ValueError(f"manifest artifact kind is not in the V1 agreement: {artifact_kind}")
    if relpath != row.relpath.value:
        raise ValueError(
            f"manifest relpath for {artifact_kind} must be {row.relpath.value!r}, got {relpath!r}"
        )
    if portable_classification != row.portable_classification.value:
        raise ValueError(
            f"manifest portable_classification for {artifact_kind} must be "
            f"{row.portable_classification.value!r}, got {portable_classification!r}"
        )
    if export_classification != row.export_classification.value:
        raise ValueError(
            f"manifest export_classification for {artifact_kind} must be "
            f"{row.export_classification.value!r}, got {export_classification!r}"
        )


def validate_artifact_agreement_rows(rows: Iterable[ArtifactAgreementRow]) -> None:
    relpaths: set[KnownArtifactRelpath] = set()
    artifact_kinds: set[ArtifactKind] = set()
    for row in rows:
        if not isinstance(row, ArtifactAgreementRow):
            raise TypeError(f"agreement rows must be ArtifactAgreementRow, got {type(row).__name__}")
        if row.relpath in relpaths:
            raise ValueError(f"duplicate artifact agreement relpath: {row.relpath.value}")
        relpaths.add(row.relpath)
        if row.artifact_kind in artifact_kinds:
            raise ValueError(f"duplicate artifact agreement artifact_kind: {row.artifact_kind.value}")
        artifact_kinds.add(row.artifact_kind)


def classify_unregistered_artifact_path_v1(relpath: str) -> ArtifactClassification:
    """Classify a path that is not part of the small V1 review/export agreement."""

    validate_artifact_relpath(relpath)
    parts = Path(relpath).parts
    prefixes = {"logs", "trace", "traces", "cache", "caches", "assets", "output"}
    if parts and parts[0] in prefixes:
        return ArtifactClassification.NOT_CANDIDATE
    if relpath.endswith((".bin", ".npy", ".npz", ".zst", ".zip", ".sqlite", ".db")):
        return ArtifactClassification.NOT_CANDIDATE
    return ArtifactClassification.NEEDS_REVIEW


def validate_artifact_relpath(relpath: str) -> None:
    if not isinstance(relpath, str) or not relpath:
        raise ValueError("relpath must be a non-empty string")
    if "\\" in relpath:
        raise ValueError("relpath must use POSIX separators")
    if relpath.startswith("/"):
        raise ValueError("relpath must be run-relative and stay under run_dir")
    path = Path(relpath)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("relpath must be run-relative and stay under run_dir")


def validate_classification(value: ArtifactClassification | str, field_name: str) -> None:
    try:
        ensure_artifact_classification(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be one of {sorted(ALLOWED_CLASSIFICATIONS)}") from exc


__all__ = [
    "AGREEMENT_VERSION",
    "ALLOWED_CLASSIFICATIONS",
    "ArtifactAgreementRow",
    "ArtifactAgreementVersion",
    "ArtifactClassification",
    "ArtifactKind",
    "KnownArtifactRelpath",
    "RunArtifactManifestVersion",
    "artifact_agreement_v1",
    "manifest_agreement_rows_v1",
    "agreement_row_by_kind_v1",
    "agreement_manifest_row_by_kind_v1",
    "assert_manifest_row_allowed_v1",
    "validate_artifact_agreement_rows",
    "classify_unregistered_artifact_path_v1",
    "ensure_artifact_classification",
    "ensure_artifact_kind",
    "ensure_known_artifact_relpath",
    "validate_artifact_relpath",
    "validate_classification",
]
