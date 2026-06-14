from __future__ import annotations

import pytest

from rune_decrypter_prime.api.artifact_agreement import agreement_manifest_row_by_kind_v1
from rune_decrypter_prime.api.run_artifact_manifest import RunArtifactManifestRow


def test_manifest_row_classification_validation_uses_artifact_agreement_values() -> None:
    agreement = agreement_manifest_row_by_kind_v1()["run_meta"]

    row = RunArtifactManifestRow(
        relpath=agreement.relpath,
        artifact_kind=agreement.artifact_kind,
        required=agreement.required,
        present=True,
        portable_classification=agreement.portable_classification,
        export_classification=agreement.export_classification,
        notes=agreement.notes,
    )

    assert row.portable_classification == "candidate"
    assert row.export_classification == "candidate"

    with pytest.raises(ValueError, match="portable_classification"):
        RunArtifactManifestRow(
            relpath=agreement.relpath,
            artifact_kind=agreement.artifact_kind,
            required=agreement.required,
            present=True,
            portable_classification="invalid_classification",
            export_classification=agreement.export_classification,
        )
