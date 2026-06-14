from __future__ import annotations

import pytest

from rune_decrypter_prime.api.artifact_agreement import (
    AGREEMENT_VERSION,
    ArtifactAgreementRow,
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
    assert [row.relpath for row in rows] == [
        "META.json",
        "config/logging.json",
        "artifacts/solver_report.json",
        "artifacts/run_artifacts_manifest.json",
    ]
    assert [row.artifact_kind for row in rows] == [
        "run_meta",
        "logging_config",
        "solver_report",
        "run_artifacts_manifest",
    ]


def test_manifest_agreement_excludes_manifest_itself_and_reviews_solver_report() -> None:
    rows_by_kind = agreement_manifest_row_by_kind_v1()
    solver_row = rows_by_kind["solver_report"]

    assert set(rows_by_kind) == {"run_meta", "logging_config", "solver_report"}
    assert "run_artifacts_manifest" not in rows_by_kind
    assert solver_row.required is False
    assert solver_row.portable_classification == "candidate"
    assert solver_row.export_classification == "candidate"
    assert solver_row.review_required is True


@pytest.mark.parametrize("bad_relpath", ["", "/absolute.json", "../outside.json", "a/../b.json", "a\\b.json"])
def test_rejects_unsafe_relpaths(bad_relpath: str) -> None:
    with pytest.raises(ValueError):
        validate_artifact_relpath(bad_relpath)


def test_rejects_duplicate_agreement_rows() -> None:
    row = ArtifactAgreementRow(
        relpath="META.json",
        artifact_kind="run_meta",
        required=True,
        portable_classification="candidate",
        export_classification="candidate",
        review_required=True,
    )
    duplicate_relpath = ArtifactAgreementRow(
        relpath="META.json",
        artifact_kind="other",
        required=True,
        portable_classification="candidate",
        export_classification="candidate",
        review_required=True,
    )
    duplicate_kind = ArtifactAgreementRow(
        relpath="other.json",
        artifact_kind="run_meta",
        required=True,
        portable_classification="candidate",
        export_classification="candidate",
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
        "assets/runtime_index.bin",
        "output/generated.zip",
        "artifacts/index.sqlite",
    ],
)
def test_large_or_runtime_artifacts_are_not_v1_export_candidates(relpath: str) -> None:
    assert classify_unregistered_artifact_path_v1(relpath) == "not_candidate"


def test_unknown_safe_path_needs_review_not_candidate() -> None:
    assert classify_unregistered_artifact_path_v1("artifacts/new_sidecar.json") == "needs_review"


def test_manifest_row_must_match_agreement() -> None:
    with pytest.raises(ValueError, match="manifest relpath"):
        assert_manifest_row_allowed_v1(
            relpath="artifacts/wrong.json",
            artifact_kind="solver_report",
            portable_classification="candidate",
            export_classification="candidate",
        )

    with pytest.raises(ValueError, match="not in the V1 agreement"):
        assert_manifest_row_allowed_v1(
            relpath="artifacts/unknown.json",
            artifact_kind="unknown",
            portable_classification="candidate",
            export_classification="candidate",
        )
