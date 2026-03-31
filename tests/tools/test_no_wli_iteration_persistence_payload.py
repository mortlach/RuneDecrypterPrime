from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.stage_iteration_payload import (
    IterationPersistencePayload,
)


pytestmark = pytest.mark.tier_a


def test_iteration_persistence_payload_builds_instance_and_artifact_views() -> None:
    payload = IterationPersistencePayload.build(
        target_key_idx=[7, 8, 9],
        truth_diagnostics={
            "available": True,
            "key_hamming_total": 2,
            "worst_substitution_slice": 1,
        },
        word_ngram_report={
            "word_ngram_judge_active": True,
            "word_ngram_judge_n_positions": 14,
            "word_ngram_judge_trust_tier": "medium",
        },
        stage2_topk_word_ngram_report=[{"rank": 1}],
        stage3_topk_word_ngram_report=[{"rank": 2}],
        stage35_archive_rows=[{"archive_rank": 1}],
        stage35_seed_rows=[{"seed_rank": 1}],
        stage3_diagnostics={
            "stage35_requested_cfg": 1,
            "stage35_proof_valid": 1,
            "stage35_proof_invalid_reason": "",
            "stage35_selected": 1,
            "stage35_archive_count": 4,
            "stage35_rounds_completed": 3,
        },
    )

    instance_fields = payload.instance_fields()
    artifact_fields = payload.artifact_fields()

    assert bool(instance_fields["word_ngram_judge_active"]) is True
    assert int(instance_fields["word_ngram_judge_n_positions"]) == 14
    assert int(instance_fields["stage35_requested_cfg"]) == 1
    assert bool(instance_fields["stage35_selected"]) is True
    assert int(instance_fields["stage35_archive_count"]) == 4
    assert artifact_fields["target_key_idx"] == [7, 8, 9]
    assert bool(artifact_fields["truth_diagnostics"]["available"]) is True
    assert artifact_fields["stage2_topk_word_ngram_report"] == [{"rank": 1}]
    assert artifact_fields["stage3_topk_word_ngram_report"] == [{"rank": 2}]
    assert artifact_fields["stage35_archive"] == [{"archive_rank": 1}]
    assert artifact_fields["stage35_seed_rows"] == [{"seed_rank": 1}]
    assert int(artifact_fields["stage35_requested_cfg"]) == 1
