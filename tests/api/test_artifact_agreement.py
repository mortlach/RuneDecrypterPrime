from __future__ import annotations

import pytest

from rune_decrypter_prime.api.artifact_agreement import (
    AGREEMENT_VERSION,
    ArtifactAgreementRow,
    ArtifactClassification,
    ArtifactKind,
    KnownArtifactRelpath,
    agreement_manifest_row_by_kind_v1,
    artifact_agreement_v1,
    assert_manifest_row_allowed_v1,
    classify_unregistered_artifact_path_v1,
    validate_artifact_agreement_rows,
    validate_artifact_relpath,
)


def test_v1_agreement_names_expected_artifacts() -> None:
    rows = artifact_agreement_v1()

    assert AGREEMENT_VERSION == "api_run_artifact_agreement.v1"
    assert ArtifactClassification.CANDIDATE.value == "candidate"
    assert [row.relpath for row in rows] == [
        KnownArtifactRelpath.RUN_META,
        KnownArtifactRelpath.LOGGING_CONFIG,
        KnownArtifactRelpath.SOLVER_REPORT,
        KnownArtifactRelpath.RDP_DISPLAY_SUMMARY,
        KnownArtifactRelpath.RUN_ARTIFACTS_MANIFEST,
    ]
    assert [row.artifact_kind for row in rows] == [
        ArtifactKind.RUN_META,
        ArtifactKind.LOGGING_CONFIG,
        ArtifactKind.SOLVER_REPORT,
        ArtifactKind.RDP_DISPLAY_SUMMARY,
        ArtifactKind.RUN_ARTIFACTS_MANIFEST,
    ]
    assert [row.to_json_dict()["relpath"] for row in rows] == [
        "META.json",
        "config/logging.json",
        "artifacts/solver_report.json",
        "artifacts/rdp_display_summary.json",
        "artifacts/run_artifacts_manifest.json",
    ]
    assert [row.to_json_dict()["artifact_kind"] for row in rows] == [
        "run_meta",
        "logging_config",
        "solver_report",
        "rdp_display_summary",
        "run_artifacts_manifest",
    ]


def test_artifact_agreement_stores_enums_and_emits_json_strings() -> None:
    row = artifact_agreement_v1()[0]

    assert isinstance(row.portable_classification, ArtifactClassification)
    assert isinstance(row.export_classification, ArtifactClassification)
    assert isinstance(row.artifact_kind, ArtifactKind)
    assert isinstance(row.relpath, KnownArtifactRelpath)
    assert row.to_json_dict()["portable_classification"] == "candidate"
    assert row.to_json_dict()["export_classification"] == "candidate"


def test_manifest_agreement_excludes_manifest_itself_and_reviews_solver_report_and_display_summary() -> None:
    rows_by_kind = agreement_manifest_row_by_kind_v1()
    solver_row = rows_by_kind[ArtifactKind.SOLVER_REPORT.value]
    display_row = rows_by_kind[ArtifactKind.RDP_DISPLAY_SUMMARY.value]

    assert set(rows_by_kind) == {"run_meta", "logging_config", "solver_report", "rdp_display_summary"}
    assert ArtifactKind.RUN_ARTIFACTS_MANIFEST.value not in rows_by_kind
    assert solver_row.required is False
    assert solver_row.portable_classification is ArtifactClassification.CANDIDATE
    assert solver_row.export_classification is ArtifactClassification.CANDIDATE
    assert solver_row.review_required is True
    assert display_row.required is False
    assert display_row.portable_classification is ArtifactClassification.CANDIDATE
    assert display_row.export_classification is ArtifactClassification.CANDIDATE
    assert display_row.review_required is True


@pytest.mark.parametrize("bad_relpath", ["", "/absolute.json", "../outside.json", "a/../b.json", "a\\b.json"])
def test_rejects_unsafe_relpaths(bad_relpath: str) -> None:
    with pytest.raises(ValueError):
        validate_artifact_relpath(bad_relpath)


def test_rejects_duplicate_agreement_rows() -> None:
    row = ArtifactAgreementRow(
        relpath=KnownArtifactRelpath.RUN_META,
        artifact_kind=ArtifactKind.RUN_META,
        required=True,
        portable_classification=ArtifactClassification.CANDIDATE,
        export_classification=ArtifactClassification.CANDIDATE,
        review_required=True,
    )
    duplicate_relpath = ArtifactAgreementRow(
        relpath=KnownArtifactRelpath.RUN_META,
        artifact_kind=ArtifactKind.LOGGING_CONFIG,
        required=True,
        portable_classification=ArtifactClassification.CANDIDATE,
        export_classification=ArtifactClassification.CANDIDATE,
        review_required=True,
    )
    duplicate_kind = ArtifactAgreementRow(
        relpath=KnownArtifactRelpath.LOGGING_CONFIG,
        artifact_kind=ArtifactKind.RUN_META,
        required=True,
        portable_classification=ArtifactClassification.CANDIDATE,
        export_classification=ArtifactClassification.CANDIDATE,
        review_required=True,
    )

    with pytest.raises(ValueError, match="duplicate artifact agreement relpath"):
        validate_artifact_agreement_rows([row, duplicate_relpath])
    with pytest.raises(ValueError, match="duplicate artifact agreement artifact_kind"):
        validate_artifact_agreement_rows([row, duplicate_kind])


@pytest.mark.parametrize(
    "relpath",
    [
        "logs/app.jsonl",
        "trace/sample.txt",
        "traces/sample.txt",
        "assets/runtime_index.bin",
        "output/generated.zip",
        "artifacts/index.sqlite",
    ],
)
def test_large_or_runtime_artifacts_are_not_v1_export_candidates(relpath: str) -> None:
    assert classify_unregistered_artifact_path_v1(relpath) is ArtifactClassification.NOT_CANDIDATE
    assert classify_unregistered_artifact_path_v1(relpath).value == "not_candidate"


def test_unknown_safe_path_needs_review_not_candidate() -> None:
    assert classify_unregistered_artifact_path_v1("artifacts/new_sidecar.json") is ArtifactClassification.NEEDS_REVIEW
    assert classify_unregistered_artifact_path_v1("artifacts/new_sidecar.json").value == "needs_review"


def test_manifest_row_must_match_agreement() -> None:
    with pytest.raises(ValueError, match="manifest relpath"):
        assert_manifest_row_allowed_v1(
            relpath="artifacts/wrong.json",
            artifact_kind=ArtifactKind.SOLVER_REPORT.value,
            portable_classification=ArtifactClassification.CANDIDATE.value,
            export_classification=ArtifactClassification.CANDIDATE.value,
        )

    with pytest.raises(ValueError, match="not in the V1 agreement"):
        assert_manifest_row_allowed_v1(
            relpath="artifacts/unknown.json",
            artifact_kind="unknown",
            portable_classification=ArtifactClassification.CANDIDATE.value,
            export_classification=ArtifactClassification.CANDIDATE.value,
        )


def test_invalid_classification_still_raises() -> None:
    with pytest.raises(ValueError):
        ArtifactAgreementRow(
            relpath=KnownArtifactRelpath.RUN_META,
            artifact_kind=ArtifactKind.RUN_META,
            required=True,
            portable_classification="invalid",
            export_classification=ArtifactClassification.CANDIDATE,
            review_required=True,
        )
