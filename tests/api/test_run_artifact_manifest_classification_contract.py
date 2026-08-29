from __future__ import annotations
import rdp.api.artifact_agreement
import rdp.api.run_artifact_manifest
import pytest


def test_manifest_row_classification_validation_uses_artifact_agreement_values() -> (
    None
):
    agreement = rdp.api.artifact_agreement.agreement_manifest_row_by_kind_v1()[
        rdp.api.artifact_agreement.ArtifactKind.RUN_META.value
    ]
    row = rdp.api.run_artifact_manifest.RunArtifactManifestRow(
        relpath=agreement.relpath,
        artifact_kind=agreement.artifact_kind,
        required=agreement.required,
        present=True,
        portable_classification=agreement.portable_classification,
        export_classification=agreement.export_classification,
        notes=agreement.notes,
    )
    assert row.relpath is rdp.api.artifact_agreement.KnownArtifactRelpath.RUN_META
    assert row.artifact_kind is rdp.api.artifact_agreement.ArtifactKind.RUN_META
    assert (
        row.portable_classification
        is rdp.api.artifact_agreement.ArtifactClassification.CANDIDATE
    )
    assert (
        row.export_classification
        is rdp.api.artifact_agreement.ArtifactClassification.CANDIDATE
    )
    assert row.to_json_dict()["relpath"] == "META.json"
    assert row.to_json_dict()["artifact_kind"] == "run_meta"
    assert row.to_json_dict()["portable_classification"] == "candidate"
    assert row.to_json_dict()["export_classification"] == "candidate"
    with pytest.raises(ValueError, match="artifact classification"):
        rdp.api.run_artifact_manifest.RunArtifactManifestRow(
            relpath=agreement.relpath,
            artifact_kind=agreement.artifact_kind,
            required=agreement.required,
            present=True,
            portable_classification="invalid_classification",
            export_classification=agreement.export_classification,
        )


def test_manifest_row_public_strings_normalise_to_enum_storage() -> None:
    row = rdp.api.run_artifact_manifest.RunArtifactManifestRow(
        relpath="META.json",
        artifact_kind="run_meta",
        required=True,
        present=True,
        portable_classification="candidate",
        export_classification="candidate",
    )
    assert row.relpath is rdp.api.artifact_agreement.KnownArtifactRelpath.RUN_META
    assert row.artifact_kind is rdp.api.artifact_agreement.ArtifactKind.RUN_META
    assert (
        row.portable_classification
        is rdp.api.artifact_agreement.ArtifactClassification.CANDIDATE
    )
    assert (
        row.export_classification
        is rdp.api.artifact_agreement.ArtifactClassification.CANDIDATE
    )
    assert row.to_json_dict()["relpath"] == "META.json"
