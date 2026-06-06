from __future__ import annotations

import json

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (
    annotated_cluster_hit_rows,
    semantic_pair_id,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1 import (
    RUNTIME_MANIFEST,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 import (
    N3CRunSpec,
    assert_resume_identity,
    select_chunks_for_run_spec,
)


def test_exact_containing_cluster_is_subset_of_ordinary_cluster_count() -> None:
    clusters = annotated_cluster_hit_rows([
        {"start_offset": 10, "end_offset": 18, "is_exact": True, "length_bucket": "8-9", "logical_group_id": "a"},
        {"start_offset": 14, "end_offset": 22, "is_exact": False, "length_bucket": "8-9", "logical_group_id": "b"},
    ])

    assert len(clusters) == 1
    assert sum(1 for row in clusters if row["has_exact"]) == 1
    assert clusters[0]["raw_hit_count"] == 2
    assert clusters[0]["exact_hit_count"] == 1


def test_non_exact_bridge_between_exact_islands_counts_one_exact_containing_cluster() -> None:
    clusters = annotated_cluster_hit_rows([
        {"start_offset": 0, "end_offset": 4, "is_exact": True, "length_bucket": "8-9", "logical_group_id": "a"},
        {"start_offset": 4, "end_offset": 8, "is_exact": False, "length_bucket": "8-9", "logical_group_id": "b"},
        {"start_offset": 8, "end_offset": 12, "is_exact": True, "length_bucket": "8-9", "logical_group_id": "c"},
    ])

    assert len(clusters) == 1
    assert sum(1 for row in clusters if row["has_exact"]) == 1
    assert clusters[0]["exact_hit_count"] == 2
    assert clusters[0]["logical_group_count"] == 3


def test_semantic_pair_id_is_unordered_within_trial() -> None:
    assert semantic_pair_id("trial", "b", "a") == semantic_pair_id("trial", "a", "b")
    assert semantic_pair_id("trial1", "a", "b") != semantic_pair_id("trial2", "a", "b")


def test_strict_full80_run_spec_selects_locked_inventory() -> None:
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    spec = N3CRunSpec(
        run_family="n3c_strict_full80",
        schema_version="n3c_run_spec_v1",
        direction="fwd",
        ngram_order=3,
        dictionary_cut="strict",
        minimum_phrase_length=8,
        length_bucket=None,
        candidate_scope="selected_80_retained_candidates_v1",
        query_contract="total_hd_le_2_max_word_hd_le_1_word_structured",
    )

    chunks = select_chunks_for_run_spec(runtime["files"], spec)

    assert len(chunks) == 815
    assert len({row["logical_group_id"] for row in chunks}) == 702
    assert sum(int(row["phrase_count"]) for row in chunks) == 365_516_232


def test_run_identity_guard_refuses_mismatched_resume(tmp_path) -> None:
    normal = N3CRunSpec(
        run_family="n3c_normal_full80",
        schema_version="n3c_run_spec_v1",
        direction="fwd",
        ngram_order=3,
        dictionary_cut="normal",
        minimum_phrase_length=8,
        length_bucket="8-9",
        candidate_scope="selected_80_retained_candidates_v1",
        query_contract="total_hd_le_2_max_word_hd_le_1_word_structured",
    )
    strict = N3CRunSpec(
        run_family="n3c_strict_full80",
        schema_version="n3c_run_spec_v1",
        direction="fwd",
        ngram_order=3,
        dictionary_cut="strict",
        minimum_phrase_length=8,
        length_bucket="8-9",
        candidate_scope="selected_80_retained_candidates_v1",
        query_contract="total_hd_le_2_max_word_hd_le_1_word_structured",
    )

    assert_resume_identity(tmp_path, normal)
    with pytest.raises(RuntimeError, match="run identity"):
        assert_resume_identity(tmp_path, strict)
