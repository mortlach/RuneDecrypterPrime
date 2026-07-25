from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

import cipher_development.two_period_overlay.review_pack as review_pack


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_tree(root: Path) -> None:
    required = (
        *review_pack.CAMPAIGN_SOURCE_PATHS,
        *review_pack.SHARED_SOURCE_PATHS,
        *review_pack.TEST_SOURCE_PATHS,
    )
    for relative in required:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"source for {relative.as_posix()}\n", encoding="utf-8")


def _run_fixture(root: Path, *, missing: str | None = None) -> Path:
    _source_tree(root)
    run = root / "output/cipher_development/two_period_overlay/run-001"
    artifacts = run / "artifacts"
    artifacts.mkdir(parents=True)
    _write_json(run / "META.json", {"git": {"commit": "a" * 40, "dirty": False}})
    _write_json(
        artifacts / "experiment_manifest.json",
        {
            "schema": "rdp_cipher_development_experiment_manifest.v1",
            "run_id": "run-001",
            "campaign_id": "two_period_overlay",
            "configuration_hash": "b" * 40,
            "experiment": {
                "campaign_id": "two_period_overlay",
                "experiment_id": "technical_canary_v1",
                "benchmark_id": "alice_308_p13_p17_d16",
                "question": "Does the canary execute?",
                "hypothesis": "The canary completes.",
                "alternative": "The canary fails its contract.",
                "decision_rule": "Canaries always refine.",
                "wli_mode": "with_wli",
                "truth_policy": "benchmark_only",
                "mechanisms": ["candidate_supply"],
                "budget_seconds": 300.0,
                "budget_evaluations": 1000,
                "lesson_ids": ["CSL-001"],
            },
        },
    )
    _write_json(
        artifacts / "experiment_result.json",
        {
            "schema": "rdp_cipher_development_experiment_result.v1",
            "run_id": "run-001",
            "campaign_id": "two_period_overlay",
            "experiment_id": "technical_canary_v1",
            "benchmark_id": "alice_308_p13_p17_d16",
            "status": "completed",
            "decision": "refine",
            "stop_reason": "max_rounds",
            "result_summary": {
                "comparison_count": 2,
                "best_score": 1.25,
                "best_candidate_id": "c" * 40,
                "evaluations": 123,
            },
            "reference_evaluation": {"exact_plaintext": False},
        },
    )
    required = review_pack._required_artifacts("technical_canary_v1")
    for relative in required:
        if relative in {
            "artifacts/experiment_manifest.json",
            "artifacts/experiment_result.json",
            missing,
        }:
            continue
        _write_json(run / relative, {"schema": "fixture.v1", "payload": {}})
    _write_json(
        root / review_pack.VALIDATION_RECEIPT,
        {
            "schema": "rdp.two_period_overlay.local_validation.v1",
            "status": "passed",
            "selected": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0,
            "duration_s": 1.0,
            "source_fingerprint": review_pack._source_fingerprint(root),
        },
    )
    validation = root / review_pack.VALIDATION_ARTIFACT_ROOT
    validation.mkdir(parents=True)
    (validation / "focused_tests.txt").write_text("10 passed\n", encoding="utf-8")
    return run


def _stable_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        review_pack,
        "_git_state",
        lambda repo_root, meta: {
            "recorded_run_commit": "a" * 40,
            "recorded_run_dirty": False,
            "current_commit": "a" * 40,
            "current_branch": "prelease/v1.0.0_o2p",
            "working_tree_clean": True,
            "working_tree_entries": [],
        },
    )
    monkeypatch.setattr(
        review_pack,
        "_environment",
        lambda: {
            "python_version": "3.11.0",
            "python_implementation": "CPython",
            "numpy_version": "2.0.0",
            "platform_system": "TestOS",
            "platform_release": "1",
            "platform_machine": "x86_64",
            "byteorder": "little",
        },
    )


def test_review_pack_is_complete_review_ready_and_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stable_runtime(monkeypatch)
    run = _run_fixture(tmp_path)
    first = review_pack.write_review_pack(tmp_path, run)
    first_bytes = first.path.read_bytes()
    second = review_pack.write_review_pack(tmp_path, run)
    second_bytes = second.path.read_bytes()

    assert first.pack_complete is True
    assert first.review_ready is True
    assert first.missing_artifacts == ()
    assert first.missing_sources == ()
    assert first_bytes == second_bytes
    assert hashlib.sha256(first_bytes).hexdigest() == hashlib.sha256(second_bytes).hexdigest()

    with ZipFile(first.path) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert "REVIEW.md" in names
        assert "review_manifest.json" in names
        assert "file_inventory.sha256" in names
        assert "validation/local/focused_tests.txt" in names
        manifest = json.loads(archive.read("review_manifest.json"))
        assert manifest["schema"] == review_pack.REVIEW_PACK_SCHEMA
        assert manifest["pack_complete"] is True
        assert manifest["review_ready"] is True
        assert manifest["experiment"]["truth_policy"] == "benchmark_only"
        assert str(tmp_path.resolve()).encode() not in first_bytes


def test_nested_replay_context_provenance_is_collected(tmp_path: Path) -> None:
    run = tmp_path / "output/cipher_development/two_period_overlay/run-001"
    provenance = {
        "asset_manifest_complete": True,
        "language_model_assets": [
            {"logical_path": "lm.bin", "sha256": "a" * 64, "size_bytes": 12}
        ],
    }
    for benchmark_id, context_id in (("d00", "a" * 40), ("d16", "b" * 40)):
        _write_json(
            run / f"artifacts/replay_contexts/{benchmark_id}.json",
            {
                "context_id": context_id,
                "payload": {"evaluator_provenance": provenance},
            },
        )

    collected = review_pack._asset_provenance(run)

    assert collected["context_count"] == 2
    assert collected["all_evaluator_provenance_equal"] is True
    assert collected["evaluator_provenance"] == provenance
    assert [item["context_id"] for item in collected["contexts"]] == [
        "a" * 40,
        "b" * 40,
    ]


def test_windows_validation_logs_are_packed_as_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stable_runtime(monkeypatch)
    run = _run_fixture(tmp_path)
    log = tmp_path / review_pack.VALIDATION_ARTIFACT_ROOT / "focused_tests.txt"
    log.write_bytes(
        f"166 passed at {tmp_path.resolve()}\r\n".encode("utf-16")
    )

    result = review_pack.write_review_pack(tmp_path, run)

    with ZipFile(result.path) as archive:
        packed = archive.read("validation/local/focused_tests.txt")
    assert packed.decode("utf-8") == "166 passed at <repo_root>\r\n"
    assert not packed.startswith((b"\xff\xfe", b"\xfe\xff"))


def test_benchmark_canary_review_renders_contract_summary_and_questions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stable_runtime(monkeypatch)
    run = _run_fixture(tmp_path)
    manifest_path = run / "artifacts/experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["experiment"]["experiment_id"] = "benchmark_contract_canary_v1"
    _write_json(manifest_path, manifest)
    result_path = run / "artifacts/experiment_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["experiment_id"] = "benchmark_contract_canary_v1"
    result["result_summary"] = {
        "benchmark_count": 4,
        "repeat_count": 2,
        "all_structural_repeats_equal": True,
    }
    _write_json(result_path, result)
    _write_json(run / "artifacts/benchmark_contract.json", {"benchmarks": []})

    packed = review_pack.write_review_pack(tmp_path, run)

    with ZipFile(packed.path) as archive:
        review = archive.read("REVIEW.md").decode("utf-8")
    assert "- benchmark_count: `4`" in review
    assert "- all_structural_repeats_equal: `True`" in review
    assert "expected affine dimensions derived as `0/4/8/16`" in review
    assert "Did discovery supply enough unique candidates?" not in review


def test_coordinate_supply_review_requires_all_ladder_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stable_runtime(monkeypatch)
    run = _run_fixture(tmp_path)
    manifest_path = run / "artifacts/experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["experiment"]["experiment_id"] = "coordinate_supply_v1"
    manifest["experiment"]["benchmark_id"] = "alice_308_coordinate_supply_d04_d08"
    _write_json(manifest_path, manifest)
    result_path = run / "artifacts/experiment_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["experiment_id"] = "coordinate_supply_v1"
    result["result_summary"] = {
        "benchmark_count": 2,
        "benchmark_ids": list(review_pack._COORDINATE_SUPPLY_BENCHMARK_IDS),
        "minimum_unique_candidates": 16,
        "total_evaluations": 100,
        "total_generated_candidates": 64,
        "total_unique_candidates": 20,
        "all_unique_thresholds_met": False,
        "benchmarks": {},
    }
    _write_json(result_path, result)
    for relative in review_pack._required_artifacts("coordinate_supply_v1"):
        if relative in {
            "artifacts/experiment_manifest.json",
            "artifacts/experiment_result.json",
        }:
            continue
        _write_json(run / relative, {"schema": "fixture.v1"})

    packed = review_pack.write_review_pack(tmp_path, run)

    assert packed.pack_complete is True
    with ZipFile(packed.path) as archive:
        review = archive.read("REVIEW.md").decode("utf-8")
        packed_manifest = json.loads(archive.read("review_manifest.json"))
    assert "- total_generated_candidates: `64`" in review
    assert "every unique coordinate optimum retained" in review
    assert len(packed_manifest["required_artifacts"]) == 13


def test_missing_required_artifact_still_creates_incomplete_pack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stable_runtime(monkeypatch)
    run = _run_fixture(tmp_path, missing="artifacts/final_archive.json")
    result = review_pack.write_review_pack(tmp_path, run)
    assert result.path.is_file()
    assert result.pack_complete is False
    assert result.review_ready is False
    assert result.missing_artifacts == ("artifacts/final_archive.json",)
    with ZipFile(result.path) as archive:
        manifest = json.loads(archive.read("review_manifest.json"))
        assert manifest["missing_artifacts"] == ["artifacts/final_archive.json"]


def test_search_visible_truth_field_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stable_runtime(monkeypatch)
    run = _run_fixture(tmp_path)
    _write_json(run / "artifacts/coordinate_archive.json", {"truth_key": [1, 2, 3]})
    with pytest.raises(ValueError, match="reference field"):
        review_pack.write_review_pack(tmp_path, run)


def test_copied_source_terminal_result_may_contain_reference_evaluation() -> None:
    review_pack._guard_run_json(
        Path("artifacts/source_experiment_result.json"),
        json.dumps({"reference_evaluation": {"exact_plaintext": True}}).encode("utf-8"),
    )
    review_pack._guard_run_json(
        Path("artifacts/staged_d8_handoff/source_pilot_experiment_result.json"),
        json.dumps({"reference_evaluation": {"exact_plaintext": True}}).encode("utf-8"),
    )


def test_run_directory_cannot_escape_campaign_root(tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere/run-001"
    outside.mkdir(parents=True)
    with pytest.raises(ValueError, match="campaign output root"):
        review_pack.write_review_pack(tmp_path, outside)


def test_failure_pack_error_is_attached_without_masking_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = RuntimeError("solver failed")
    monkeypatch.setattr(
        review_pack,
        "write_review_pack",
        lambda repo_root, run_dir: (_ for _ in ()).throw(ValueError("pack failed")),
    )
    result = review_pack.write_review_pack_after_run(
        tmp_path, tmp_path / "run", original_error=original
    )
    assert result is None
    assert any("pack failed" in note for note in getattr(original, "__notes__", []))


def test_validation_receipt_is_strict_and_portable(tmp_path: Path) -> None:
    path = review_pack.write_local_validation_receipt(
        tmp_path,
        selected=12,
        passed=10,
        failed=0,
        skipped=2,
        duration_s=3.5,
        note="focused and real-asset checks",
    )
    payload = json.loads(path.read_text())
    assert payload["schema"] == review_pack.LOCAL_VALIDATION_SCHEMA
    assert payload["status"] == "passed"
    assert payload["selected"] == 12
    assert payload["source_fingerprint"] == review_pack._source_fingerprint(tmp_path)
    with pytest.raises(ValueError, match="sum"):
        review_pack.write_local_validation_receipt(
            tmp_path,
            selected=2,
            passed=1,
            failed=0,
            skipped=0,
            duration_s=1.0,
        )


def test_stale_validation_receipt_blocks_review_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stable_runtime(monkeypatch)
    run = _run_fixture(tmp_path)
    source = tmp_path / review_pack.CAMPAIGN_SOURCE_PATHS[0]
    source.write_text(source.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")

    result = review_pack.write_review_pack(tmp_path, run)

    assert result.pack_complete is True
    assert result.review_ready is False
    with ZipFile(result.path) as archive:
        manifest = json.loads(archive.read("review_manifest.json"))
    assert manifest["evidence_quality"]["validation_source_matches"] is False
    assert manifest["evidence_quality"]["tests_passed"] is False


def test_dirty_git_state_is_informational_not_a_review_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _run_fixture(tmp_path)
    monkeypatch.setattr(
        review_pack,
        "_git_state",
        lambda repo_root, meta: {
            "recorded_run_commit": None,
            "recorded_run_dirty": True,
            "current_commit": None,
            "current_branch": None,
            "working_tree_clean": False,
            "working_tree_entries": [" M local.py"],
        },
    )
    monkeypatch.setattr(
        review_pack,
        "_environment",
        lambda: {
            "python_version": "3.11.0",
            "python_implementation": "CPython",
            "numpy_version": "2.0.0",
            "platform_system": "TestOS",
            "platform_release": "1",
            "platform_machine": "x86_64",
            "byteorder": "little",
        },
    )

    result = review_pack.write_review_pack(tmp_path, run)

    assert result.review_ready is True
    with ZipFile(result.path) as archive:
        manifest = json.loads(archive.read("review_manifest.json"))
    assert manifest["working_tree_clean"] is False
    assert manifest["evidence_quality"]["working_tree_clean"] is False


def test_replay_suite_pack_includes_bound_source_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stable_runtime(monkeypatch)
    run = _run_fixture(tmp_path)
    source_run = tmp_path / "output/cipher_development/two_period_overlay/source-run"
    for relative in review_pack._REPLAY_SOURCE_ARTIFACTS:
        _write_json(source_run / relative, {"schema": "source.fixture.v1", "value": relative})

    manifest_path = run / "artifacts/experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["experiment"]["experiment_id"] = "technical_canary_replay_suite_v1"
    manifest["experiment"]["truth_policy"] = "none"
    _write_json(manifest_path, manifest)
    result_path = run / "artifacts/experiment_result.json"
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    result_payload["experiment_id"] = "technical_canary_replay_suite_v1"
    result_payload["reference_evaluation"] = None
    result_payload["result_summary"] = {
        "source_run_id": "source-run",
        "replay_count": 2,
        "all_deterministic": True,
        "all_stored_scores_verified": True,
        "technical_replay_gate_passed": True,
    }
    _write_json(result_path, result_payload)
    for relative in review_pack._required_artifacts("technical_canary_replay_suite_v1"):
        if relative not in {
            "artifacts/experiment_manifest.json",
            "artifacts/experiment_result.json",
        }:
            _write_json(run / relative, {"schema": "suite.fixture.v1", "payload": {}})
    review_pack.write_local_validation_receipt(
        tmp_path, selected=1, passed=1, failed=0, skipped=0, duration_s=0.1
    )

    packed = review_pack.write_review_pack(tmp_path, run)

    assert packed.pack_complete is True
    assert packed.review_ready is True
    with ZipFile(packed.path) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("review_manifest.json"))
    assert "source_run/artifacts/archive_handoff_binding.json" in names
    assert "source_run/artifacts/control_start_batch.json" in names
    assert manifest["missing_source_run_artifacts"] == []
    assert len(manifest["source_run_files"]) == len(review_pack._REPLAY_SOURCE_ARTIFACTS)
