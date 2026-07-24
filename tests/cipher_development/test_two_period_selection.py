from __future__ import annotations

import json
from pathlib import Path

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    candidate_id_for,
)
from cipher_development.two_period_overlay.candidate_selection import (
    SOURCE_BENCHMARK_ID,
    latest_completed_coordinate_supply,
)
from cipher_development.two_period_overlay.config import DECISION_SCORE
from cipher_development.two_period_overlay.selection import (
    affine_hamming,
    build_selection_batches,
    diverse_high_wli_candidate_ids,
    top_wli_candidate_ids,
)


def _record(values: tuple[int, ...], score: float) -> CandidateRecord:
    identity = {"expanded_key": list(values) + [0]}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={
            "variables": list(values),
            "expanded_key": list(values) + [0],
            "benchmark_id": SOURCE_BENCHMARK_ID,
        },
        scores={DECISION_SCORE: score},
        provenance=CandidateProvenance(source="test"),
    )


def _archive() -> CandidateArchive:
    archive = CandidateArchive(ArchivePolicy(16, DECISION_SCORE))
    values = (
        (0, 0, 0, 0),
        (1, 0, 0, 0),
        (0, 1, 0, 0),
        (0, 0, 1, 0),
        (0, 0, 0, 1),
        (1, 1, 0, 0),
        (1, 0, 1, 0),
        (1, 0, 0, 1),
        (2, 2, 2, 2),
        (3, 3, 3, 3),
        (4, 4, 4, 4),
        (5, 5, 5, 5),
        (6, 6, 6, 6),
        (7, 7, 7, 7),
        (8, 8, 8, 8),
        (9, 9, 9, 9),
    )
    for index, item in enumerate(values):
        archive.offer(_record(item, 100.0 - index))
    return archive


def test_top_selection_uses_best_first_archive_order() -> None:
    archive = _archive()
    assert top_wli_candidate_ids(archive, 4) == tuple(
        record.candidate_id for record in archive.records[:4]
    )


def test_diverse_selection_is_deterministic_and_preserves_best() -> None:
    archive = _archive()
    first = diverse_high_wli_candidate_ids(archive, count=4, shortlist_multiplier=4)
    second = diverse_high_wli_candidate_ids(archive, count=4, shortlist_multiplier=4)
    assert first == second
    assert first[0] == archive.records[0].candidate_id
    assert len(first) == len(set(first)) == 4
    assert first != top_wli_candidate_ids(archive, 4)


def test_diverse_policy_maximises_minimum_affine_distance_greedily() -> None:
    archive = _archive()
    selected_ids = diverse_high_wli_candidate_ids(archive, count=4, shortlist_multiplier=4)
    selected = [archive.get(item) for item in selected_ids]
    assert affine_hamming(selected[0], selected[1]) == 4
    for index in range(1, len(selected)):
        prior = selected[:index]
        chosen_minimum = min(affine_hamming(selected[index], item) for item in prior)
        remaining = [
            record for record in archive.records[:16]
            if record.candidate_id not in selected_ids[:index]
        ]
        assert chosen_minimum == max(
            min(affine_hamming(record, item) for item in prior)
            for record in remaining
        )


def test_selection_batches_are_bound_to_same_archive_and_report_contrast() -> None:
    archive = _archive()
    top, diverse, comparison = build_selection_batches(
        archive, count=4, shortlist_multiplier=4
    )
    assert top.source_archive_hash == diverse.source_archive_hash
    assert top.selection_label == "top_wli"
    assert diverse.selection_label == "diverse_high_wli"
    assert comparison.identical is False
    assert comparison.overlap_count < 4
    assert comparison.diverse_affine_hamming_summary["minimum"] > (
        comparison.top_affine_hamming_summary["minimum"]
    )


def test_latest_coordinate_supply_requires_completed_thresholded_result(tmp_path: Path) -> None:
    root = tmp_path / "output/cipher_development/two_period_overlay"
    for run_id, completed in (("run-001", False), ("run-002", True)):
        run = root / run_id / "artifacts"
        run.mkdir(parents=True)
        (run / "experiment_manifest.json").write_text(json.dumps({
            "experiment": {"experiment_id": "coordinate_supply_v1"},
        }))
        (run / "experiment_result.json").write_text(json.dumps({
            "run_id": run_id,
            "status": "completed",
            "result_summary": {"all_unique_thresholds_met": completed},
        }))
    assert latest_completed_coordinate_supply(tmp_path) == "run-002"


def test_review_pack_requires_complete_selection_and_replay_surface() -> None:
    from cipher_development.two_period_overlay.review_pack import _required_artifacts

    required = set(_required_artifacts("candidate_selection_v1"))
    assert {
        "artifacts/source_discovery_pool_archive.json",
        "artifacts/source_discovery_diagnostics.json",
        "artifacts/replay_context.json",
        "artifacts/top_wli_batch.json",
        "artifacts/top_wli_binding.json",
        "artifacts/top_wli_replay.json",
        "artifacts/diverse_high_wli_batch.json",
        "artifacts/diverse_high_wli_binding.json",
        "artifacts/diverse_high_wli_replay.json",
        "artifacts/selection_comparison.json",
    }.issubset(required)
