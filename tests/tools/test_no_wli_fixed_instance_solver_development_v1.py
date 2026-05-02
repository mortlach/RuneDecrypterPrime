from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    extract_fixed_instance_solver_development_v1 as mod,
    verify_candidate1_guard_accept_611_7005 as verify_mod,
    verify_candidate2_anchor_family_reserved_shadow as candidate2_anchor_shadow_mod,
    verify_candidate3_phasec_phaseb_topk_anchor_shadow as candidate3_anchor_shadow_mod,
    verify_candidate3_phasec_anchor_swap_exact_replay_611_7004 as candidate3_exact_mod,
)


def _inventory_row(
    *,
    panel_job_index: int,
    fixture_seed: int,
    search_seed: int,
    status: str,
    best_stage: str,
    best_match_ratio: str,
    stage35_selected: str,
    source_run_label: str = "vx",
    stop_reason: str = "unsolved",
    stage35_proof_valid: str = "1",
    total_seconds: str = "123.0",
) -> dict[str, str]:
    run_name = f"run_{fixture_seed}_{search_seed}"
    return {
        "panel_job_index": str(panel_job_index),
        "source_run_label": source_run_label,
        "fixture_seed": str(fixture_seed),
        "search_seed": str(search_seed),
        "status": status,
        "stop_reason": stop_reason,
        "best_stage": best_stage,
        "best_match_ratio": best_match_ratio,
        "stage35_selected": stage35_selected,
        "stage35_proof_valid": stage35_proof_valid,
        "total_seconds": total_seconds,
        "source_report_dir": f"output/test/{run_name}",
        "copied_report_dir": f"50_completed_job_runs/{run_name}",
    }


def _stage35_row(
    *,
    panel_job_index: int,
    fixture_seed: int,
    search_seed: int,
    status: str,
    best_stage: str,
    best_match_ratio: str,
    stage35_selected: str,
    archive_seed_row_count: str,
    best_stage35_seed_row_count: str,
    space_map_stage35_row_count: str,
    joined_row_count: str,
    distinct_stage35_family_count: str,
    dominant_stage35_family_id: str,
    dominant_stage35_family_share: str,
    focus_stage35_family_id: str,
    stage35_family_counts: str,
    source_run_label: str = "vx",
) -> dict[str, str]:
    run_name = f"run_{fixture_seed}_{search_seed}"
    return {
        "panel_job_index": str(panel_job_index),
        "source_run_label": source_run_label,
        "fixture_seed": str(fixture_seed),
        "search_seed": str(search_seed),
        "status": status,
        "best_stage": best_stage,
        "best_match_ratio": best_match_ratio,
        "stage35_selected": stage35_selected,
        "source_report_dir": f"output/test/{run_name}",
        "best_path": f"output/test/{run_name}/best/best_instance.json",
        "archive_path": f"output/test/{run_name}/stage35_seed_archive.json",
        "progress_path": f"output/test/{run_name}/stage35_progress.jsonl",
        "archive_seed_row_count": archive_seed_row_count,
        "best_stage35_seed_row_count": best_stage35_seed_row_count,
        "space_map_stage35_row_count": space_map_stage35_row_count,
        "joined_row_count": joined_row_count,
        "distinct_stage35_family_count": distinct_stage35_family_count,
        "dominant_stage35_family_id": dominant_stage35_family_id,
        "dominant_stage35_family_share": dominant_stage35_family_share,
        "focus_stage35_family_id": focus_stage35_family_id,
        "stage35_family_counts": stage35_family_counts,
    }


def _best_instance(
    *,
    fixture_seed: int,
    search_seed: int,
    status: str,
    best_stage: str,
    best_match_ratio: str,
    stage35_selected: bool,
    best_score: float = 1.234,
) -> dict[str, object]:
    return {
        "instance_source_key_seed": fixture_seed,
        "instance_fixture_id": f"fixture_{fixture_seed}",
        "status": status,
        "best_stage": best_stage,
        "best_match_ratio": float(best_match_ratio),
        "best_score": best_score,
        "stage35_selected": stage35_selected,
        "word_ngram_judge_active": True,
        "word_ngram_judge_report_xent": 10.5,
        "word_ngram_judge_trust_score": 0.42,
        "word_ngram_judge_trust_tier": "medium",
        "word_ngram_judge_n_positions": 512,
    }


def _baseline_1111_row(
    *,
    panel_job_index: int,
    search_seed: int,
    status: str,
    best_match_ratio: float,
    dominant_family_id: str,
    dominant_family_share: float,
    stage35_family_counts: str,
    distinct_family_count: int,
    archive_seed_row_count: int,
    best_stage35_seed_row_count: int,
    space_map_stage35_row_count: int,
    joined_row_count: int,
) -> dict[str, object]:
    return {
        "panel_job_index": panel_job_index,
        "fixture_seed": 1111,
        "search_seed": search_seed,
        "status": status,
        "best_stage": "stage35_substitution_only",
        "best_match_ratio": best_match_ratio,
        "archive_seed_row_count": archive_seed_row_count,
        "best_stage35_seed_row_count": best_stage35_seed_row_count,
        "space_map_stage35_row_count": space_map_stage35_row_count,
        "joined_row_count": joined_row_count,
        "distinct_stage35_family_count": distinct_family_count,
        "stage35_family_counts": stage35_family_counts,
        "dominant_stage35_family_id": dominant_family_id,
        "dominant_stage35_family_share": dominant_family_share,
        "word_ngram_judge_active": 1,
        "word_ngram_judge_report_xent": 10.5,
        "word_ngram_judge_trust_score": 0.42,
        "word_ngram_judge_trust_tier": "medium",
        "word_ngram_judge_n_positions": 512,
    }


def _focus_1111_run_summary_row(
    *,
    panel_job_index: int,
    search_seed: int,
    status: str,
    best_match_ratio: float,
    focus_family_id: str,
    total_rows: int,
    stage35_rows: int,
    selected_rows: int,
    admitted_rows: int,
    max_final_score: float,
    max_final_match: float,
) -> dict[str, str]:
    return {
        "panel_job_index": str(panel_job_index),
        "fixture_seed": "1111",
        "search_seed": str(search_seed),
        "status": status,
        "best_stage": "stage35_substitution_only",
        "best_match_ratio": str(best_match_ratio),
        "focus_family_id": focus_family_id,
        "focus_family_total_rows": str(total_rows),
        "focus_family_stage35_rows": str(stage35_rows),
        "focus_family_selected_rows": str(selected_rows),
        "focus_family_admitted_rows": str(admitted_rows),
        "focus_family_max_final_score": str(max_final_score),
        "focus_family_max_final_match": str(max_final_match),
    }


def _focus_1111_all_family_row(
    *,
    search_seed: int,
    family_id: str,
    row_count: int,
    selected_row_count: int,
    admitted_row_count: int,
    stage35_row_count: int,
    max_final_score: float | None,
    max_final_match: float | None,
) -> dict[str, str]:
    return {
        "search_seed": str(search_seed),
        "family_id": family_id,
        "row_count": str(row_count),
        "selected_row_count": str(selected_row_count),
        "admitted_row_count": str(admitted_row_count),
        "stage35_row_count": str(stage35_row_count),
        "max_final_score": "" if max_final_score is None else str(max_final_score),
        "max_final_match": "" if max_final_match is None else str(max_final_match),
    }


def _join_final_best_row(
    *,
    search_seed: int,
    family_id: str,
    best_lane: str,
    best_stage3_source: str,
    selection_rank: int,
) -> dict[str, str]:
    return {
        "fixture_seed": "1111",
        "search_seed": str(search_seed),
        "best_seed_source": "final_best",
        "best_space_candidate_hash_match": "True",
        "space_family_id": family_id,
        "best_lane": best_lane,
        "best_stage3_source": best_stage3_source,
        "space_selection_rank": str(selection_rank),
    }


def _followup_finish(
    *,
    baseline_candidate_source: str,
    baseline_candidate_lane: str,
    archive_count: int = 12,
    runtime_seconds: float = 1000.0,
) -> dict[str, object]:
    return {
        "accept_reason": "accepted",
        "accept_passed": 1,
        "archive_count": archive_count,
        "baseline_candidate_source": baseline_candidate_source,
        "baseline_candidate_lane": baseline_candidate_lane,
        "baseline_selector": "score_plus_novelty",
        "rounds_completed": 1,
        "runtime_seconds": runtime_seconds,
    }


def _full_1111_compare_input_bundle() -> tuple[
    list[dict[str, object]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    dict[tuple[int, int], dict[str, object]],
]:
    baseline_rows = [
        _baseline_1111_row(
            panel_job_index=6,
            search_seed=7001,
            status="unsolved",
            best_match_ratio=0.428,
            dominant_family_id="f1",
            dominant_family_share=0.8333333333333334,
            stage35_family_counts="f0:1, f1:5",
            distinct_family_count=2,
            archive_seed_row_count=6,
            best_stage35_seed_row_count=6,
            space_map_stage35_row_count=6,
            joined_row_count=6,
        ),
        _baseline_1111_row(
            panel_job_index=7,
            search_seed=7002,
            status="unsolved",
            best_match_ratio=0.754,
            dominant_family_id="f0",
            dominant_family_share=1.0,
            stage35_family_counts="f0:6",
            distinct_family_count=1,
            archive_seed_row_count=6,
            best_stage35_seed_row_count=6,
            space_map_stage35_row_count=6,
            joined_row_count=6,
        ),
        _baseline_1111_row(
            panel_job_index=8,
            search_seed=7003,
            status="stalled",
            best_match_ratio=0.408,
            dominant_family_id="f0",
            dominant_family_share=0.8333333333333334,
            stage35_family_counts="f0:5, f1:1",
            distinct_family_count=2,
            archive_seed_row_count=6,
            best_stage35_seed_row_count=6,
            space_map_stage35_row_count=6,
            joined_row_count=6,
        ),
        _baseline_1111_row(
            panel_job_index=9,
            search_seed=7004,
            status="unsolved",
            best_match_ratio=0.423,
            dominant_family_id="f2",
            dominant_family_share=0.6,
            stage35_family_counts="f0:1, f1:1, f2:3",
            distinct_family_count=3,
            archive_seed_row_count=5,
            best_stage35_seed_row_count=5,
            space_map_stage35_row_count=5,
            joined_row_count=5,
        ),
        _baseline_1111_row(
            panel_job_index=10,
            search_seed=7005,
            status="unsolved",
            best_match_ratio=0.372,
            dominant_family_id="f0",
            dominant_family_share=0.8333333333333334,
            stage35_family_counts="f0:5, f1:1",
            distinct_family_count=2,
            archive_seed_row_count=6,
            best_stage35_seed_row_count=6,
            space_map_stage35_row_count=6,
            joined_row_count=6,
        ),
    ]
    focus_rows = [
        _focus_1111_run_summary_row(
            panel_job_index=6,
            search_seed=7001,
            status="unsolved",
            best_match_ratio=0.428,
            focus_family_id="f0",
            total_rows=32,
            stage35_rows=1,
            selected_rows=20,
            admitted_rows=10,
            max_final_score=0.19601150727475802,
            max_final_match=0.42,
        ),
        _focus_1111_run_summary_row(
            panel_job_index=7,
            search_seed=7002,
            status="unsolved",
            best_match_ratio=0.754,
            focus_family_id="f0",
            total_rows=41,
            stage35_rows=6,
            selected_rows=24,
            admitted_rows=9,
            max_final_score=0.3022291305585272,
            max_final_match=0.752,
        ),
        _focus_1111_run_summary_row(
            panel_job_index=8,
            search_seed=7003,
            status="stalled",
            best_match_ratio=0.408,
            focus_family_id="f0",
            total_rows=36,
            stage35_rows=5,
            selected_rows=20,
            admitted_rows=7,
            max_final_score=0.16151737726005755,
            max_final_match=0.161,
        ),
        _focus_1111_run_summary_row(
            panel_job_index=9,
            search_seed=7004,
            status="unsolved",
            best_match_ratio=0.423,
            focus_family_id="f0",
            total_rows=29,
            stage35_rows=1,
            selected_rows=17,
            admitted_rows=7,
            max_final_score=0.17955717672334737,
            max_final_match=0.432,
        ),
        _focus_1111_run_summary_row(
            panel_job_index=10,
            search_seed=7005,
            status="unsolved",
            best_match_ratio=0.372,
            focus_family_id="f0",
            total_rows=36,
            stage35_rows=5,
            selected_rows=20,
            admitted_rows=7,
            max_final_score=0.1466989954364033,
            max_final_match=0.416,
        ),
    ]
    all_family_rows = [
        _focus_1111_all_family_row(
            search_seed=7001,
            family_id="f0",
            row_count=32,
            selected_row_count=20,
            admitted_row_count=10,
            stage35_row_count=1,
            max_final_score=0.19601150727475802,
            max_final_match=0.42,
        ),
        _focus_1111_all_family_row(
            search_seed=7002,
            family_id="f0",
            row_count=41,
            selected_row_count=24,
            admitted_row_count=9,
            stage35_row_count=6,
            max_final_score=0.3022291305585272,
            max_final_match=0.752,
        ),
        _focus_1111_all_family_row(
            search_seed=7003,
            family_id="f0",
            row_count=36,
            selected_row_count=20,
            admitted_row_count=7,
            stage35_row_count=5,
            max_final_score=0.16151737726005755,
            max_final_match=0.161,
        ),
        _focus_1111_all_family_row(
            search_seed=7003,
            family_id="f1",
            row_count=13,
            selected_row_count=12,
            admitted_row_count=7,
            stage35_row_count=1,
            max_final_score=0.15783563605620754,
            max_final_match=0.188,
        ),
        _focus_1111_all_family_row(
            search_seed=7003,
            family_id="f5",
            row_count=9,
            selected_row_count=8,
            admitted_row_count=7,
            stage35_row_count=0,
            max_final_score=0.14713993100640466,
            max_final_match=0.323,
        ),
        _focus_1111_all_family_row(
            search_seed=7004,
            family_id="f0",
            row_count=29,
            selected_row_count=17,
            admitted_row_count=7,
            stage35_row_count=1,
            max_final_score=0.17955717672334737,
            max_final_match=0.432,
        ),
        _focus_1111_all_family_row(
            search_seed=7005,
            family_id="f0",
            row_count=36,
            selected_row_count=20,
            admitted_row_count=7,
            stage35_row_count=5,
            max_final_score=0.1466989954364033,
            max_final_match=0.416,
        ),
    ]
    join_rows = [
        _join_final_best_row(
            search_seed=7001,
            family_id="f0",
            best_lane="anchor",
            best_stage3_source="stage3_best_phaseB",
            selection_rank=1,
        ),
        _join_final_best_row(
            search_seed=7002,
            family_id="f0",
            best_lane="anchor",
            best_stage3_source="stage3_best_phaseB",
            selection_rank=1,
        ),
        _join_final_best_row(
            search_seed=7003,
            family_id="f1",
            best_lane="challenger",
            best_stage3_source="phaseB_topk",
            selection_rank=6,
        ),
        _join_final_best_row(
            search_seed=7004,
            family_id="f0",
            best_lane="anchor",
            best_stage3_source="stage3_best_phaseA",
            selection_rank=1,
        ),
        _join_final_best_row(
            search_seed=7005,
            family_id="f1",
            best_lane="challenger",
            best_stage3_source="phaseB_topk",
            selection_rank=6,
        ),
    ]
    followup = {
        (1111, 7001): _followup_finish(
            baseline_candidate_source="stage3_best_phaseB",
            baseline_candidate_lane="anchor",
            runtime_seconds=1225.2,
        ),
        (1111, 7002): _followup_finish(
            baseline_candidate_source="phaseB_topk",
            baseline_candidate_lane="challenger",
            runtime_seconds=648.4,
        ),
        (1111, 7003): _followup_finish(
            baseline_candidate_source="phaseA_selected",
            baseline_candidate_lane="challenger",
            runtime_seconds=2522.7,
        ),
        (1111, 7004): _followup_finish(
            baseline_candidate_source="phaseB_topk",
            baseline_candidate_lane="challenger",
            runtime_seconds=1548.4,
        ),
        (1111, 7005): _followup_finish(
            baseline_candidate_source="phaseA_selected",
            baseline_candidate_lane="challenger",
            runtime_seconds=1996.2,
        ),
    }
    return baseline_rows, focus_rows, all_family_rows, join_rows, followup


def _full_1511_compare_input_bundle() -> tuple[
    list[dict[str, object]],
    list[dict[str, str]],
    dict[tuple[int, int], dict[str, object]],
]:
    baseline_rows = [
        {
            "panel_job_index": 16,
            "fixture_seed": 1511,
            "search_seed": 7001,
            "status": "solved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.956,
            "stage35_selected": 0,
            "archive_seed_row_count": 5,
            "best_stage35_seed_row_count": 0,
            "space_map_stage35_row_count": 0,
            "joined_row_count": 5,
            "family_summary_available": 0,
            "distinct_stage35_family_count": 0,
            "stage35_family_counts": "",
            "focus_stage35_family_id": "",
            "dominant_stage35_family_id": "",
            "dominant_stage35_family_share": None,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 16.770874409138507,
            "word_ngram_judge_trust_score": 0.4838709677419355,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 31,
        },
        {
            "panel_job_index": 17,
            "fixture_seed": 1511,
            "search_seed": 7002,
            "status": "unsolved",
            "best_stage": "stage35_substitution_only",
            "best_match_ratio": 0.829,
            "stage35_selected": 1,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "joined_row_count": 6,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 1,
            "stage35_family_counts": "f0:6",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "dominant_stage35_family_share": 1.0,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 17.5966698732852,
            "word_ngram_judge_trust_score": 0.4107142857142857,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 28,
        },
        {
            "panel_job_index": 18,
            "fixture_seed": 1511,
            "search_seed": 7003,
            "status": "unsolved",
            "best_stage": "stage35_substitution_only",
            "best_match_ratio": 0.845,
            "stage35_selected": 1,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "joined_row_count": 6,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 1,
            "stage35_family_counts": "f0:6",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "dominant_stage35_family_share": 1.0,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 16.57146618423603,
            "word_ngram_judge_trust_score": 0.4285714285714286,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 28,
        },
        {
            "panel_job_index": 19,
            "fixture_seed": 1511,
            "search_seed": 7004,
            "status": "unsolved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.571,
            "stage35_selected": 0,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "joined_row_count": 6,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 1,
            "stage35_family_counts": "f0:6",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "dominant_stage35_family_share": 1.0,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 18.954785740217982,
            "word_ngram_judge_trust_score": 0.35294117647058826,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 34,
        },
        {
            "panel_job_index": 20,
            "fixture_seed": 1511,
            "search_seed": 7005,
            "status": "unsolved",
            "best_stage": "stage35_substitution_only",
            "best_match_ratio": 0.692,
            "stage35_selected": 1,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "joined_row_count": 6,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 2,
            "stage35_family_counts": "f0:5, f1:1",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "dominant_stage35_family_share": 0.8333333333333334,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 16.887018356559675,
            "word_ngram_judge_trust_score": 0.34375,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 32,
        },
    ]
    join_rows = [
        {
            "search_seed": "7001",
            "join_seed_source": "final_best",
            "family_id": "",
            "join_stage3_source": "",
            "selection_rank": "",
        },
        {
            "search_seed": "7002",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "1",
        },
        {
            "search_seed": "7003",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "1",
        },
        {
            "search_seed": "7004",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "1",
        },
        {
            "search_seed": "7005",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "1",
        },
        {
            "search_seed": "7005",
            "join_seed_source": "stage3_topk_phaseb",
            "family_id": "f1",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "2",
        },
    ]
    followup = {
        (1511, 7002): _followup_finish(
            baseline_candidate_source="phaseB_topk",
            baseline_candidate_lane="challenger",
            runtime_seconds=942.3,
        ),
        (1511, 7003): _followup_finish(
            baseline_candidate_source="phaseB_topk",
            baseline_candidate_lane="challenger",
            runtime_seconds=669.6,
        ),
        (1511, 7004): {
            "accept_reason": "search_score_drop_guard_failed",
            "accept_passed": 0,
            "archive_count": 12,
            "baseline_candidate_source": "phaseB_topk",
            "baseline_candidate_lane": "challenger",
            "baseline_selector": "score_plus_novelty",
            "runtime_seconds": 809.7,
        },
        (1511, 7005): _followup_finish(
            baseline_candidate_source="phaseB_topk",
            baseline_candidate_lane="challenger",
            runtime_seconds=1315.3,
        ),
    }
    return baseline_rows, join_rows, followup


def _full_611_compare_input_bundle() -> tuple[
    list[dict[str, object]],
    list[dict[str, str]],
    dict[tuple[int, int], dict[str, object]],
]:
    baseline_rows = [
        {
            "panel_job_index": 1,
            "fixture_seed": 611,
            "search_seed": 7001,
            "status": "unsolved",
            "best_stage": "stage35_substitution_only",
            "best_match_ratio": 0.335,
            "stage35_selected": 1,
            "archive_seed_row_count": 2,
            "best_stage35_seed_row_count": 2,
            "space_map_stage35_row_count": 2,
            "joined_row_count": 2,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 2,
            "stage35_family_counts": "f0:1, f1:1",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "dominant_stage35_family_share": 0.5,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 14.0,
            "word_ngram_judge_trust_score": 0.31,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 31,
        },
        {
            "panel_job_index": 2,
            "fixture_seed": 611,
            "search_seed": 7002,
            "status": "unsolved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.424,
            "stage35_selected": 0,
            "archive_seed_row_count": 2,
            "best_stage35_seed_row_count": 2,
            "space_map_stage35_row_count": 2,
            "joined_row_count": 2,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 2,
            "stage35_family_counts": "f0:1, f1:1",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "dominant_stage35_family_share": 0.5,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 13.8,
            "word_ngram_judge_trust_score": 0.33,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 30,
        },
        {
            "panel_job_index": 3,
            "fixture_seed": 611,
            "search_seed": 7003,
            "status": "unsolved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.466,
            "stage35_selected": 0,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "joined_row_count": 6,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 2,
            "stage35_family_counts": "f0:1, f1:5",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f1",
            "dominant_stage35_family_share": 0.8333333333333334,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 13.1,
            "word_ngram_judge_trust_score": 0.36,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 28,
        },
        {
            "panel_job_index": 4,
            "fixture_seed": 611,
            "search_seed": 7004,
            "status": "unsolved",
            "best_stage": "stage35_substitution_only",
            "best_match_ratio": 0.762,
            "stage35_selected": 1,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "joined_row_count": 6,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 1,
            "stage35_family_counts": "f0:6",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "dominant_stage35_family_share": 1.0,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 12.4,
            "word_ngram_judge_trust_score": 0.39,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 29,
        },
        {
            "panel_job_index": 5,
            "fixture_seed": 611,
            "search_seed": 7005,
            "status": "unsolved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.585,
            "stage35_selected": 0,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "joined_row_count": 6,
            "family_summary_available": 1,
            "distinct_stage35_family_count": 1,
            "stage35_family_counts": "f0:6",
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "dominant_stage35_family_share": 1.0,
            "word_ngram_judge_active": 1,
            "word_ngram_judge_report_xent": 12.9,
            "word_ngram_judge_trust_score": 0.35,
            "word_ngram_judge_trust_tier": "medium",
            "word_ngram_judge_n_positions": 28,
        },
    ]
    join_rows = [
        {
            "search_seed": "7001",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "stage3_best_phaseA",
            "selection_rank": "1",
        },
        {
            "search_seed": "7001",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f1",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "2",
        },
        {
            "search_seed": "7002",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "stage3_best_phaseA",
            "selection_rank": "1",
        },
        {
            "search_seed": "7002",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f1",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "2",
        },
        {
            "search_seed": "7003",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "1",
        },
        {
            "search_seed": "7003",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f1",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "2",
        },
        {
            "search_seed": "7003",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f1",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "3",
        },
        {
            "search_seed": "7003",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f1",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "4",
        },
        {
            "search_seed": "7003",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f1",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "5",
        },
        {
            "search_seed": "7003",
            "join_seed_source": "stage3_topk_phaseb",
            "family_id": "f1",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "6",
        },
        {
            "search_seed": "7004",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "1",
        },
        {
            "search_seed": "7004",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "2",
        },
        {
            "search_seed": "7004",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "3",
        },
        {
            "search_seed": "7004",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "4",
        },
        {
            "search_seed": "7004",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "5",
        },
        {
            "search_seed": "7004",
            "join_seed_source": "stage3_topk_phaseb",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "6",
        },
        {
            "search_seed": "7005",
            "join_seed_source": "final_best",
            "family_id": "f0",
            "join_stage3_source": "stage3_best_phaseB",
            "selection_rank": "1",
        },
        {
            "search_seed": "7005",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "2",
        },
        {
            "search_seed": "7005",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "4",
        },
        {
            "search_seed": "7005",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "5",
        },
        {
            "search_seed": "7005",
            "join_seed_source": "phasec_phaseb_challenger",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "6",
        },
        {
            "search_seed": "7005",
            "join_seed_source": "stage3_topk_phaseb",
            "family_id": "f0",
            "join_stage3_source": "phaseB_topk",
            "selection_rank": "3",
        },
    ]
    followup = {
        (611, 7001): _followup_finish(
            baseline_candidate_source="phaseA_selected",
            baseline_candidate_lane="challenger",
            runtime_seconds=6395.5,
        ),
        (611, 7002): {
            "accept_reason": "search_score_drop_guard_failed",
            "accept_passed": 0,
            "archive_count": 12,
            "baseline_candidate_source": "phaseA_selected",
            "baseline_candidate_lane": "challenger",
            "baseline_selector": "score_plus_novelty",
            "runtime_seconds": 5981.2,
        },
        (611, 7003): {
            "accept_reason": "search_score_drop_guard_failed",
            "accept_passed": 0,
            "archive_count": 12,
            "baseline_candidate_source": "phaseB_topk",
            "baseline_candidate_lane": "challenger",
            "baseline_selector": "score_plus_novelty",
            "runtime_seconds": 2456.1,
        },
        (611, 7004): _followup_finish(
            baseline_candidate_source="phaseB_topk",
            baseline_candidate_lane="challenger",
            runtime_seconds=771.6,
        ),
        (611, 7005): {
            "accept_reason": "search_score_drop_guard_failed",
            "accept_passed": 0,
            "archive_count": 12,
            "baseline_candidate_source": "phaseB_topk",
            "baseline_candidate_lane": "challenger",
            "baseline_selector": "score_plus_novelty",
            "runtime_seconds": 1174.8,
        },
    }
    return baseline_rows, join_rows, followup


def test_case_role_contract_is_fixed() -> None:
    assert mod.CASE_ROLE_BY_FIXTURE_SEED == {
        1511: "positive_control",
        611: "middle_unsolved_case",
        1111: "conversion_failure_case",
        1411: "caveated_cross_check",
    }


def test_panel_baseline_rows_keep_stage35_counts_and_solved_run_caveat() -> None:
    panel_rows = [
        _inventory_row(
            panel_job_index=16,
            fixture_seed=1511,
            search_seed=7001,
            status="solved",
            best_stage="stage3_full_refine",
            best_match_ratio="0.956",
            stage35_selected="False",
            stop_reason="solved",
        ),
    ]
    stage35_rows = [
        _stage35_row(
            panel_job_index=16,
            fixture_seed=1511,
            search_seed=7001,
            status="solved",
            best_stage="stage3_full_refine",
            best_match_ratio="0.956",
            stage35_selected="False",
            archive_seed_row_count="5",
            best_stage35_seed_row_count="0",
            space_map_stage35_row_count="0",
            joined_row_count="5",
            distinct_stage35_family_count="0",
            dominant_stage35_family_id="",
            dominant_stage35_family_share="",
            focus_stage35_family_id="",
            stage35_family_counts="",
        ),
    ]
    best_instances = {
        (1511, 7001): _best_instance(
            fixture_seed=1511,
            search_seed=7001,
            status="solved",
            best_stage="stage3_full_refine",
            best_match_ratio="0.956",
            stage35_selected=False,
        )
    }

    rows = mod.build_panel_baseline_rows(
        panel_inventory_rows=panel_rows,
        stage35_run_summary_rows=stage35_rows,
        best_instances_by_run_key=best_instances,
        focus_1111_rows_by_run_key={},
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["archive_seed_row_count"] == 5
    assert row["best_stage35_seed_row_count"] == 0
    assert row["space_map_stage35_row_count"] == 0
    assert row["benchmark_case_role"] == "positive_control"
    assert row["primary_tuning_target"] == 1
    assert row["cross_check_case"] == 0
    assert row["family_mapping_caveat"] == 1
    assert row["family_summary_available"] == 0
    assert row["caveat_flags"] == [
        "no_family_mapped_stage35_rows",
        "archive_only_stage35_seed_rows",
        "solved_stage3_with_archive_side_stage35_rows",
        "solved_without_family_mapped_stage35_rows",
    ]


def test_panel_baseline_rows_keep_focus_family_separate_from_dominant_family() -> None:
    panel_rows = [
        _inventory_row(
            panel_job_index=6,
            fixture_seed=1111,
            search_seed=7001,
            status="unsolved",
            best_stage="stage35_substitution_only",
            best_match_ratio="0.438",
            stage35_selected="True",
        ),
    ]
    stage35_rows = [
        _stage35_row(
            panel_job_index=6,
            fixture_seed=1111,
            search_seed=7001,
            status="unsolved",
            best_stage="stage35_substitution_only",
            best_match_ratio="0.438",
            stage35_selected="True",
            archive_seed_row_count="8",
            best_stage35_seed_row_count="8",
            space_map_stage35_row_count="8",
            joined_row_count="8",
            distinct_stage35_family_count="2",
            dominant_stage35_family_id="f1",
            dominant_stage35_family_share="0.625",
            focus_stage35_family_id="f0",
            stage35_family_counts="f0:3, f1:5",
        ),
    ]
    best_instances = {
        (1111, 7001): _best_instance(
            fixture_seed=1111,
            search_seed=7001,
            status="unsolved",
            best_stage="stage35_substitution_only",
            best_match_ratio="0.438",
            stage35_selected=True,
        )
    }
    focus_rows = {
        (1111, 7001): {
            "focus_family_total_rows": "9",
            "focus_family_stage35_rows": "4",
            "focus_family_selected_rows": "1",
            "focus_family_admitted_rows": "1",
            "focus_family_max_final_score": "0.88",
            "focus_family_max_final_match": "0.438",
        }
    }

    rows = mod.build_panel_baseline_rows(
        panel_inventory_rows=panel_rows,
        stage35_run_summary_rows=stage35_rows,
        best_instances_by_run_key=best_instances,
        focus_1111_rows_by_run_key=focus_rows,
    )

    row = rows[0]
    assert row["focus_stage35_family_id"] == "f0"
    assert row["dominant_stage35_family_id"] == "f1"
    assert row["primary_tuning_target"] == 1
    assert row["focus_family_total_rows"] == 9
    assert row["focus_family_max_final_match"] == 0.438
    assert "focus_family_differs_from_dominant_mapped_stage35_family" in row["caveat_flags"]


def test_panel_baseline_rows_are_deterministic_under_input_reordering() -> None:
    panel_rows = [
        _inventory_row(
            panel_job_index=6,
            fixture_seed=1111,
            search_seed=7001,
            status="unsolved",
            best_stage="stage35_substitution_only",
            best_match_ratio="0.438",
            stage35_selected="True",
        ),
        _inventory_row(
            panel_job_index=1,
            fixture_seed=611,
            search_seed=7001,
            status="unsolved",
            best_stage="stage3_full_refine",
            best_match_ratio="0.424",
            stage35_selected="False",
        ),
    ]
    stage35_rows = [
        _stage35_row(
            panel_job_index=1,
            fixture_seed=611,
            search_seed=7001,
            status="unsolved",
            best_stage="stage3_full_refine",
            best_match_ratio="0.424",
            stage35_selected="False",
            archive_seed_row_count="2",
            best_stage35_seed_row_count="2",
            space_map_stage35_row_count="2",
            joined_row_count="2",
            distinct_stage35_family_count="1",
            dominant_stage35_family_id="f0",
            dominant_stage35_family_share="1.0",
            focus_stage35_family_id="f0",
            stage35_family_counts="f0:2",
        ),
        _stage35_row(
            panel_job_index=6,
            fixture_seed=1111,
            search_seed=7001,
            status="unsolved",
            best_stage="stage35_substitution_only",
            best_match_ratio="0.438",
            stage35_selected="True",
            archive_seed_row_count="8",
            best_stage35_seed_row_count="8",
            space_map_stage35_row_count="8",
            joined_row_count="8",
            distinct_stage35_family_count="2",
            dominant_stage35_family_id="f1",
            dominant_stage35_family_share="0.625",
            focus_stage35_family_id="f0",
            stage35_family_counts="f0:3, f1:5",
        ),
    ]
    best_instances = {
        (611, 7001): _best_instance(
            fixture_seed=611,
            search_seed=7001,
            status="unsolved",
            best_stage="stage3_full_refine",
            best_match_ratio="0.424",
            stage35_selected=False,
        ),
        (1111, 7001): _best_instance(
            fixture_seed=1111,
            search_seed=7001,
            status="unsolved",
            best_stage="stage35_substitution_only",
            best_match_ratio="0.438",
            stage35_selected=True,
        ),
    }

    rows_a = mod.build_panel_baseline_rows(
        panel_inventory_rows=panel_rows,
        stage35_run_summary_rows=stage35_rows,
        best_instances_by_run_key=best_instances,
        focus_1111_rows_by_run_key={},
    )
    rows_b = mod.build_panel_baseline_rows(
        panel_inventory_rows=list(reversed(panel_rows)),
        stage35_run_summary_rows=list(reversed(stage35_rows)),
        best_instances_by_run_key=dict(reversed(list(best_instances.items()))),
        focus_1111_rows_by_run_key={},
    )

    assert rows_a == rows_b
    assert [(row["fixture_seed"], row["search_seed"]) for row in rows_a] == [
        (611, 7001),
        (1111, 7001),
    ]


def test_instance_search_matrix_keeps_zero_family_mapped_runs() -> None:
    baseline_rows = [
        {
            "panel_job_index": 13,
            "fixture_seed": 1411,
            "search_seed": 7003,
            "benchmark_case_role": "caveated_cross_check",
            "status": "solved",
            "best_match_ratio": 0.905,
            "best_stage": "stage3_full_refine",
            "stage35_selected": 0,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 0,
            "space_map_stage35_row_count": 0,
            "focus_stage35_family_id": "",
            "dominant_stage35_family_id": "",
            "caveat_flags": [
                "no_family_mapped_stage35_rows",
                "archive_only_stage35_seed_rows",
                "solved_stage3_with_archive_side_stage35_rows",
                "solved_without_family_mapped_stage35_rows",
                "fixture_role_caveated_cross_check",
            ],
        }
    ]

    rows = mod.build_instance_search_matrix_rows(baseline_rows)

    assert len(rows) == 1
    row = rows[0]
    assert row["search7003_archive_seed_row_count"] == 6
    assert row["search7003_space_map_stage35_row_count"] == 0
    assert row["search7003_caveat_flags"] == (
        "no_family_mapped_stage35_rows; "
        "archive_only_stage35_seed_rows; "
        "solved_stage3_with_archive_side_stage35_rows; "
        "solved_without_family_mapped_stage35_rows; "
        "fixture_role_caveated_cross_check"
    )


def test_baseline_cases_markdown_uses_primary_trio_and_caveated_cross_check(tmp_path: Path) -> None:
    baseline_rows = [
        {
            "panel_job_index": 1,
            "fixture_seed": 1511,
            "search_seed": 7001,
            "benchmark_case_role": "positive_control",
            "primary_tuning_target": 1,
            "cross_check_case": 0,
            "family_mapping_caveat": 1,
            "status": "solved",
            "best_match_ratio": 0.956,
            "best_stage": "stage3_full_refine",
            "stage35_selected": 0,
            "archive_seed_row_count": 5,
            "best_stage35_seed_row_count": 0,
            "space_map_stage35_row_count": 0,
            "focus_stage35_family_id": "",
            "dominant_stage35_family_id": "",
            "caveat_flags": ["solved_without_family_mapped_stage35_rows"],
        },
        {
            "panel_job_index": 2,
            "fixture_seed": 611,
            "search_seed": 7004,
            "benchmark_case_role": "middle_unsolved_case",
            "primary_tuning_target": 1,
            "cross_check_case": 0,
            "family_mapping_caveat": 0,
            "status": "unsolved",
            "best_match_ratio": 0.762,
            "best_stage": "stage35_substitution_only",
            "stage35_selected": 1,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "caveat_flags": [],
        },
        {
            "panel_job_index": 3,
            "fixture_seed": 1111,
            "search_seed": 7002,
            "benchmark_case_role": "conversion_failure_case",
            "primary_tuning_target": 1,
            "cross_check_case": 0,
            "family_mapping_caveat": 0,
            "status": "unsolved",
            "best_match_ratio": 0.754,
            "best_stage": "stage35_substitution_only",
            "stage35_selected": 1,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
            "caveat_flags": [],
        },
        {
            "panel_job_index": 4,
            "fixture_seed": 1411,
            "search_seed": 7003,
            "benchmark_case_role": "caveated_cross_check",
            "primary_tuning_target": 0,
            "cross_check_case": 1,
            "family_mapping_caveat": 1,
            "status": "solved",
            "best_match_ratio": 0.905,
            "best_stage": "stage3_full_refine",
            "stage35_selected": 0,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 0,
            "space_map_stage35_row_count": 0,
            "focus_stage35_family_id": "",
            "dominant_stage35_family_id": "",
            "caveat_flags": ["fixture_role_caveated_cross_check"],
        },
    ]
    instance_summary_rows = mod.build_instance_summary_rows(baseline_rows)
    by_seed = {row["fixture_seed"]: row for row in instance_summary_rows}
    assert by_seed[1511]["primary_tuning_target"] == 1
    assert by_seed[1511]["family_mapping_caveat_run_count"] == 1
    assert by_seed[1411]["primary_tuning_target"] == 0
    assert by_seed[1411]["cross_check_case"] == 1
    assert by_seed[1411]["family_mapping_caveat_run_count"] == 1

    mod.write_baseline_cases_markdown(
        tmp_path,
        baseline_rows=baseline_rows,
        instance_summary_rows=instance_summary_rows,
    )

    text = (tmp_path / "fixed_instance_solver_baseline_cases.md").read_text(
        encoding="utf-8"
    )
    assert "Primary tuning trio:" in text
    assert "- `1511` - positive control" in text
    assert "- `611` - middle unsolved case" in text
    assert "- `1111` - conversion-failure case" in text
    assert "Cross-check case:" in text
    assert "- `1411` - useful but caveated cross-check" in text
    assert "Seed 1411" in text
    assert "caveated cross-check" in text


def test_1111_compare_rows_keep_focus_dominant_and_final_best_separate() -> None:
    baseline_rows, focus_rows, all_family_rows, join_rows, followup = (
        _full_1111_compare_input_bundle()
    )
    compare_rows = mod.build_1111_conversion_compare_rows(
        baseline_rows=baseline_rows,
        focus_1111_run_summary_rows=focus_rows,
        focus_1111_all_family_summary_rows=all_family_rows,
        stage35_join_rows=join_rows,
        followup_finish_by_run_key=followup,
    )

    row = next(row for row in compare_rows if row["search_seed"] == 7003)
    assert row["focus_family_id"] == "f0"
    assert row["dominant_mapped_stage35_family_id"] == "f0"
    assert row["final_best_stage35_seed_family_id"] == "f1"
    assert row["max_mapped_family_by_final_match_id"] == "f5"
    assert row["family_alignment_label"] == "focus_and_dominant_aligned"
    assert row["baseline_candidate_source"] == "phaseA_selected"
    assert row["baseline_candidate_lane"] == "challenger"
    assert row["focus_family_matches_dominant_mapped_family"] == 1
    assert row["focus_family_matches_final_best_family"] == 0
    assert "final-best stage35 seed family diverges from focus family" in row["key_stage35_notes"]


def test_1111_compare_rows_are_deterministic_under_input_reordering() -> None:
    baseline_rows, focus_rows, all_family_rows, join_rows, followup = (
        _full_1111_compare_input_bundle()
    )

    rows_a = mod.build_1111_conversion_compare_rows(
        baseline_rows=baseline_rows,
        focus_1111_run_summary_rows=focus_rows,
        focus_1111_all_family_summary_rows=all_family_rows,
        stage35_join_rows=join_rows,
        followup_finish_by_run_key=followup,
    )
    rows_b = mod.build_1111_conversion_compare_rows(
        baseline_rows=list(reversed(baseline_rows)),
        focus_1111_run_summary_rows=list(reversed(focus_rows)),
        focus_1111_all_family_summary_rows=list(reversed(all_family_rows)),
        stage35_join_rows=list(reversed(join_rows)),
        followup_finish_by_run_key=dict(reversed(list(followup.items()))),
    )

    assert rows_a == rows_b
    assert [row["search_seed"] for row in rows_a] == [7001, 7002, 7003, 7004, 7005]
    assert rows_a[1]["family_alignment_label"] == "all_aligned"
    assert rows_a[2]["family_alignment_label"] == "focus_and_dominant_aligned"


def test_1111_audit_markdown_includes_locked_definitions_and_required_runs(
    tmp_path: Path,
) -> None:
    compare_rows = [
        {
            "search_seed": 7002,
            "status": "unsolved",
            "best_match_ratio": 0.754,
            "focus_family_id": "f0",
            "dominant_mapped_stage35_family_id": "f0",
            "final_best_stage35_seed_family_id": "f0",
            "max_mapped_family_by_final_match_id": "f0",
            "baseline_candidate_source": "phaseB_topk",
            "baseline_candidate_lane": "challenger",
            "baseline_selector": "score_plus_novelty",
            "focus_family_stage35_rows": 6,
            "focus_family_max_final_match": 0.752,
            "family_alignment_label": "all_aligned",
            "stage35_family_counts": "f0:6",
            "distinct_stage35_family_count": 1,
            "key_stage35_notes": "baseline phaseB_topk/challenger; single-family mapped stage35 region",
        },
        {
            "search_seed": 7001,
            "status": "unsolved",
            "best_match_ratio": 0.428,
            "focus_family_id": "f0",
            "dominant_mapped_stage35_family_id": "f1",
            "final_best_stage35_seed_family_id": "f0",
            "max_mapped_family_by_final_match_id": "f0",
            "baseline_candidate_source": "stage3_best_phaseB",
            "baseline_candidate_lane": "anchor",
            "baseline_selector": "score_plus_novelty",
            "focus_family_stage35_rows": 1,
            "focus_family_max_final_match": 0.42,
            "family_alignment_label": "focus_and_final_best_aligned",
            "stage35_family_counts": "f0:1, f1:5",
            "distinct_stage35_family_count": 2,
            "key_stage35_notes": "baseline stage3_best_phaseB/anchor; 2 mapped stage35 families (f0:1, f1:5); mapped late rows dominated away from focus family",
        },
        {
            "search_seed": 7003,
            "status": "stalled",
            "best_match_ratio": 0.408,
            "focus_family_id": "f0",
            "dominant_mapped_stage35_family_id": "f0",
            "final_best_stage35_seed_family_id": "f1",
            "max_mapped_family_by_final_match_id": "f5",
            "baseline_candidate_source": "phaseA_selected",
            "baseline_candidate_lane": "challenger",
            "baseline_selector": "score_plus_novelty",
            "focus_family_stage35_rows": 5,
            "focus_family_max_final_match": 0.161,
            "family_alignment_label": "focus_and_dominant_aligned",
            "stage35_family_counts": "f0:5, f1:1",
            "distinct_stage35_family_count": 2,
            "key_stage35_notes": "baseline phaseA_selected/challenger; 2 mapped stage35 families (f0:5, f1:1); final-best stage35 seed family diverges from focus family; max mapped final-match family is f5; run stalled after stage35 admission",
        },
        {
            "search_seed": 7004,
            "status": "unsolved",
            "best_match_ratio": 0.423,
            "focus_family_id": "f0",
            "dominant_mapped_stage35_family_id": "f2",
            "final_best_stage35_seed_family_id": "f0",
            "max_mapped_family_by_final_match_id": "f0",
            "baseline_candidate_source": "phaseB_topk",
            "baseline_candidate_lane": "challenger",
            "baseline_selector": "score_plus_novelty",
            "focus_family_stage35_rows": 1,
            "focus_family_max_final_match": 0.432,
            "family_alignment_label": "focus_and_final_best_aligned",
            "stage35_family_counts": "f0:1, f1:1, f2:3",
            "distinct_stage35_family_count": 3,
            "key_stage35_notes": "baseline phaseB_topk/challenger; 3 mapped stage35 families (f0:1, f1:1, f2:3); mapped late rows dominated away from focus family",
        },
        {
            "search_seed": 7005,
            "status": "unsolved",
            "best_match_ratio": 0.372,
            "focus_family_id": "f0",
            "dominant_mapped_stage35_family_id": "f0",
            "final_best_stage35_seed_family_id": "f1",
            "max_mapped_family_by_final_match_id": "f0",
            "baseline_candidate_source": "phaseA_selected",
            "baseline_candidate_lane": "challenger",
            "baseline_selector": "score_plus_novelty",
            "focus_family_stage35_rows": 5,
            "focus_family_max_final_match": 0.416,
            "family_alignment_label": "focus_and_dominant_aligned",
            "stage35_family_counts": "f0:5, f1:1",
            "distinct_stage35_family_count": 2,
            "key_stage35_notes": "baseline phaseA_selected/challenger; 2 mapped stage35 families (f0:5, f1:1); final-best stage35 seed family diverges from focus family",
        },
    ]

    mod.write_1111_conversion_failure_audit_markdown(
        tmp_path,
        compare_rows=compare_rows,
    )

    text = (tmp_path / "1111_conversion_failure_audit.md").read_text(
        encoding="utf-8"
    )
    assert "focus family = family of the top stage35-admitted row in that run" in text
    assert "final-best family = family of the joined stage35 seed row" in text
    assert "`7002` is the only fully aligned case" in text
    assert "`7003` and `7005` keep mapped stage35 dominance on `f0`" in text
    assert "| search seed | status | best match | focus family | dominant mapped family | final-best family |" in text


def test_1511_positive_control_compare_rows_keep_solved_run_caveat_and_tight_f0_cases() -> None:
    baseline_rows, join_rows, followup = _full_1511_compare_input_bundle()

    rows = mod.build_1511_positive_control_compare_rows(
        baseline_rows=baseline_rows,
        seed1511_join_rows=join_rows,
        followup_finish_by_run_key=followup,
    )

    assert [row["search_seed"] for row in rows] == [7001, 7002, 7003, 7004, 7005]

    solved_row = rows[0]
    assert solved_row["status"] == "solved"
    assert solved_row["solved_run_stage3_caveat"] == 1
    assert solved_row["mapped_family_shape_label"] == "no_family_mapped_stage35_rows"
    assert solved_row["final_best_stage35_seed_family_id"] == ""

    strong_row = rows[2]
    assert strong_row["search_seed"] == 7003
    assert strong_row["dominant_mapped_stage35_family_id"] == "f0"
    assert strong_row["final_best_stage35_seed_family_id"] == "f0"
    assert strong_row["mapped_family_shape_label"] == "single_family"
    assert strong_row["followup_accept_reason"] == "accepted"

    tail_row = rows[4]
    assert tail_row["search_seed"] == 7005
    assert tail_row["mapped_family_shape_label"] == "dominant_family_with_minor_tail"
    assert tail_row["mapped_family_counter_f1"] == 1


def test_1511_audit_markdown_mentions_solved_run_caveat_and_tight_f0_pattern(
    tmp_path: Path,
) -> None:
    baseline_rows, join_rows, followup = _full_1511_compare_input_bundle()
    rows = mod.build_1511_positive_control_compare_rows(
        baseline_rows=baseline_rows,
        seed1511_join_rows=join_rows,
        followup_finish_by_run_key=followup,
    )

    mod.write_1511_positive_control_audit_markdown(
        tmp_path,
        compare_rows=rows,
    )

    text = (tmp_path / "1511_positive_control_audit.md").read_text(
        encoding="utf-8"
    )
    assert "`1511/7001` is the true solve" in text
    assert "`7002` and `7003` are the strongest non-solved references" in text
    assert "single-family `f0`" in text
    assert "`7004` shows that family tightness alone does not guarantee success" in text


def test_611_middle_case_compare_rows_keep_7004_7005_pair_and_mixed_7003() -> None:
    baseline_rows, join_rows, followup = _full_611_compare_input_bundle()

    rows = mod.build_611_middle_case_compare_rows(
        baseline_rows=baseline_rows,
        seed611_join_rows=join_rows,
        followup_finish_by_run_key=followup,
    )

    assert [row["search_seed"] for row in rows] == [7001, 7002, 7003, 7004, 7005]

    mixed_row = rows[2]
    assert mixed_row["search_seed"] == 7003
    assert mixed_row["dominant_mapped_stage35_family_id"] == "f1"
    assert mixed_row["mapped_family_shape_label"] == "dominant_family_with_minor_tail"
    assert mixed_row["final_best_stage35_seed_family_id"] == "f0"

    strong_row = rows[3]
    assert strong_row["search_seed"] == 7004
    assert strong_row["mapped_family_shape_label"] == "single_family"
    assert strong_row["followup_accept_reason"] == "accepted"
    assert strong_row["baseline_candidate_source"] == "phaseB_topk"

    reject_row = rows[4]
    assert reject_row["search_seed"] == 7005
    assert reject_row["mapped_family_shape_label"] == "single_family"
    assert reject_row["followup_accept_reason"] == "search_score_drop_guard_failed"
    assert "run finishes back at stage 3" in reject_row["key_stage35_notes"]


def test_611_audit_markdown_calls_out_7004_vs_7005_and_f1_dominant_7003(
    tmp_path: Path,
) -> None:
    baseline_rows, join_rows, followup = _full_611_compare_input_bundle()
    rows = mod.build_611_middle_case_compare_rows(
        baseline_rows=baseline_rows,
        seed611_join_rows=join_rows,
        followup_finish_by_run_key=followup,
    )

    mod.write_611_middle_case_audit_markdown(
        tmp_path,
        compare_rows=rows,
    )

    text = (tmp_path / "611_middle_case_audit.md").read_text(
        encoding="utf-8"
    )
    assert "`611/7004` is the clearest middle-case reference" in text
    assert "`611/7005` reaches the same single-family `f0` late region" in text
    assert "`7003` reaches a larger mapped region, but it is mostly `f1`" in text
    assert "`7004` and `7005` are the most useful pair" in text


def test_1411_caveat_note_keeps_cross_check_status_and_counts(tmp_path: Path) -> None:
    baseline_rows = [
        {
            "fixture_seed": 1411,
            "search_seed": 7001,
            "status": "unsolved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.73,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f0",
        },
        {
            "fixture_seed": 1411,
            "search_seed": 7002,
            "status": "unsolved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.43,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f1",
        },
        {
            "fixture_seed": 1411,
            "search_seed": 7003,
            "status": "solved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.905,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 0,
            "space_map_stage35_row_count": 0,
            "focus_stage35_family_id": "",
            "dominant_stage35_family_id": "",
        },
        {
            "fixture_seed": 1411,
            "search_seed": 7004,
            "status": "unsolved",
            "best_stage": "stage35_substitution_only",
            "best_match_ratio": 0.398,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f1",
        },
        {
            "fixture_seed": 1411,
            "search_seed": 7005,
            "status": "unsolved",
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.422,
            "archive_seed_row_count": 6,
            "best_stage35_seed_row_count": 6,
            "space_map_stage35_row_count": 6,
            "focus_stage35_family_id": "f0",
            "dominant_stage35_family_id": "f1",
        },
    ]

    mod.write_1411_caveat_and_use_note(
        tmp_path,
        baseline_rows=baseline_rows,
    )

    text = (tmp_path / "1411_caveat_and_use_note.md").read_text(
        encoding="utf-8"
    )
    assert "`1411` remains in the benchmark as a useful, mixed solvable cross-check case." in text
    assert "`1411/7003` is a true stage-3 solve." in text
    assert "`best / space_map` side" in text
    assert "do not treat it as an equal first-line tuning target" in text


def test_candidate_shortlist_keeps_two_narrow_candidates(tmp_path: Path) -> None:
    baseline_611, join_611, followup_611 = _full_611_compare_input_bundle()
    compare_611 = mod.build_611_middle_case_compare_rows(
        baseline_rows=baseline_611,
        seed611_join_rows=join_611,
        followup_finish_by_run_key=followup_611,
    )
    baseline_1511, join_1511, followup_1511 = _full_1511_compare_input_bundle()
    compare_1511 = mod.build_1511_positive_control_compare_rows(
        baseline_rows=baseline_1511,
        seed1511_join_rows=join_1511,
        followup_finish_by_run_key=followup_1511,
    )
    baseline_1111, focus_1111, all_family_1111, join_1111, followup_1111 = (
        _full_1111_compare_input_bundle()
    )
    compare_1111 = mod.build_1111_conversion_compare_rows(
        baseline_rows=baseline_1111,
        focus_1111_run_summary_rows=focus_1111,
        focus_1111_all_family_summary_rows=all_family_1111,
        stage35_join_rows=join_1111,
        followup_finish_by_run_key=followup_1111,
    )

    mod.write_candidate_solver_change_shortlist(
        tmp_path,
        compare_1111_rows=compare_1111,
        compare_1511_rows=compare_1511,
        compare_611_rows=compare_611,
    )

    text = (tmp_path / "candidate_solver_change_shortlist.md").read_text(
        encoding="utf-8"
    )
    assert "Candidate 1 - continuation selection and acceptance around coherent late routes" in text
    assert "Candidate 2 - family-aware budget allocation once a coherent focal family appears" in text
    assert "- primary: `611` and `1111`" in text
    assert "- primary: `1111`" in text


def test_verify_candidate1_load_selected_phasec_row_keeps_hash_and_selector() -> None:
    artifact = {
        "stage3_diagnostics": {
            "phaseC_start_summaries": [
                {
                    "candidate_hash": "other",
                    "source": "phaseA_selected",
                    "lane": "anchor",
                    "source_rank": 1,
                    "final_score": 0.11,
                    "final_match": 0.21,
                },
                {
                    "candidate_hash": "wanted",
                    "source": "phaseB_topk",
                    "lane": "challenger",
                    "source_rank": 2,
                    "final_score": 0.23,
                    "final_match": 0.57,
                },
            ]
        }
    }

    row = verify_mod.load_selected_phasec_row(
        artifact,
        candidate_hash="wanted",
        selector="score_plus_novelty",
    )

    assert row["candidate_hash"] == "wanted"
    assert row["source"] == "phaseB_topk"
    assert row["lane"] == "challenger"
    assert row["source_rank"] == 2
    assert row["selector"] == "score_plus_novelty"


def test_verify_candidate1_comparison_summary_marks_second_preview_match() -> None:
    case = type(
        "Case",
        (),
        {
            "artifact_path": Path(
                "output/tools/benchmarks/periodic_sub_trans/no_wli/mock/final.json"
            ),
            "run_dir": Path(
                "output/tools/benchmarks/periodic_sub_trans/no_wli/mock/run_dir"
            ),
            "artifact": {
                "best_match_ratio": 0.585,
            },
        },
    )()
    selected_row = {
        "selector": "score_plus_novelty",
        "candidate_hash": "baseline-hash",
        "source": "phaseB_topk",
        "lane": "challenger",
        "source_rank": 2,
        "final_score": 0.23171454932072244,
        "final_match": 0.572,
    }
    retained_stage_row = {
        "stage35_accept_passed": 0,
        "stage35_accept_reason": "search_score_drop_guard_failed",
        "stage35_best_score": 0.23357093889279312,
        "stage35_best_search_score": -12.01193032221665,
    }
    retained_followup_row = {
        "archive_preview_rows": [
            {
                "candidate_hash": "top-hash",
                "score": 0.23357093889279312,
                "search_score": -12.01193032221665,
            },
            {
                "candidate_hash": "second-hash",
                "score": 0.2327406552195851,
                "search_score": -11.993596530367164,
            },
        ]
    }
    candidate_payload = {
        "resume_best_match_ratio": 0.58,
        "stage35": {
            "baseline_search_score": -12.00737629491563,
            "accept_passed": 1,
            "accept_reason": "accepted_via_guard_passing_selector",
            "selected_archive_rank": 2,
            "selected_via_guard_passing_selector": 1,
            "best_candidate_hash": "second-hash",
            "best_score": 0.2327406552195851,
            "best_search_score": -11.993596530367164,
        },
    }

    summary = verify_mod.build_candidate1_comparison_summary(
        case=case,
        selected_row=selected_row,
        retained_stage_row=retained_stage_row,
        retained_followup_row=retained_followup_row,
        candidate_payload=candidate_payload,
    )

    assert summary["selected_candidate_hash"] == "baseline-hash"
    assert summary["candidate_accept_passed"] == 1
    assert summary["candidate_selected_archive_rank"] == 2
    assert summary["candidate_matches_retained_second_preview_hash"] == 1
    assert summary["candidate_best_score_minus_retained_top_score"] < 0.0
    assert summary["candidate_best_search_score_minus_retained_top_search_score"] > 0.0


def test_verify_candidate1_projected_no_harm_summary_keeps_no_harm_fields() -> None:
    class _Case:
        artifact_path = Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/source/final_instances/case.json"
        )
        run_dir = Path(
            "output/tools/benchmarks/periodic_sub_trans/no_wli/source"
        )
        artifact = {"best_match_ratio": 0.585}

    projected_payload = {
        "projected_best_stage": "stage3_full_refine",
        "projected_best_match_ratio": 0.585,
        "projected_best_score": 0.241,
        "stage3_flow": {
            "stage35_selected": 1,
            "stage35_best_match": 0.572,
        },
        "outcome": {
            "stage35_used_for_final_best": 0,
        },
    }

    summary = verify_mod.build_projected_no_harm_summary(
        case=_Case(),
        projected_payload=projected_payload,
    )

    assert summary["projected_best_stage"] == "stage3_full_refine"
    assert summary["projected_best_match_ratio"] == 0.585
    assert summary["projected_stage35_selected"] == 1
    assert summary["projected_stage35_best_match"] == 0.572
    assert summary["projected_stage35_used_for_final_best"] == 0
    assert summary["projected_match_delta_vs_original_run_best"] == 0.0


def test_candidate2_anchor_family_shadow_summary_finds_saved_anchor_family_room() -> None:
    annotated_rows = [
        {
            "candidate_hash": "anchor",
            "family_id": "f0",
            "source": "stage3_best_phaseB",
            "source_rank": 1,
            "selected_by_phasec_start": 1,
        },
        {
            "candidate_hash": "start-b",
            "family_id": "f1",
            "source": "phaseB_topk",
            "source_rank": 2,
            "selected_by_phasec_start": 1,
        },
        {
            "candidate_hash": "start-c",
            "family_id": "f2",
            "source": "phaseA_selected",
            "source_rank": 3,
            "selected_by_phasec_start": 1,
        },
        {
            "candidate_hash": "extra-a",
            "family_id": "f0",
            "source": "phaseA_selected",
            "source_rank": 4,
            "selected_by_phasec_start": 0,
        },
        {
            "candidate_hash": "extra-b",
            "family_id": "f0",
            "source": "phaseA_selected",
            "source_rank": 5,
            "selected_by_phasec_start": 0,
        },
    ]
    start_rows = [
        {"candidate_hash": "anchor"},
        {"candidate_hash": "start-b"},
        {"candidate_hash": "start-c"},
    ]

    summary = candidate2_anchor_shadow_mod.summarize_candidate2_anchor_family_shadow_from_annotated_rows(
        fixture_seed=611,
        search_seed=7005,
        status="unsolved",
        best_stage="stage3_full_refine",
        best_match_ratio=0.585,
        phasec_start_policy="source_order",
        phasec_start_keys_used=3,
        annotated_rows=annotated_rows,
        start_rows=start_rows,
        reserved_slots=2,
        best_instance_relpath="50_completed_job_runs/run/best/best_instance.json",
    )

    assert summary["anchor_candidate_hash"] == "anchor"
    assert summary["anchor_family_id"] == "f0"
    assert summary["phasec_selected_start_unique_hash_count"] == 3
    assert summary["anchor_family_selected_start_unique_hash_count"] == 1
    assert summary["anchor_family_extra_pool_unique_hash_count"] == 2
    assert summary["shadow_materializable_extra_anchor_rows"] == 2
    assert summary["shadow_anchor_family_unique_hash_count_after"] == 3
    assert summary["baseline_anchor_family_start_share"] == pytest.approx(1.0 / 3.0)
    assert summary["shadow_anchor_family_start_share_after"] == pytest.approx(1.0)
    assert summary["room_label"] == "saved_room_available"


def test_candidate2_anchor_family_shadow_summary_marks_missing_phasec_pool() -> None:
    summary = candidate2_anchor_shadow_mod.summarize_candidate2_anchor_family_shadow_from_annotated_rows(
        fixture_seed=1411,
        search_seed=7003,
        status="solved",
        best_stage="stage3_full_refine",
        best_match_ratio=0.905,
        phasec_start_policy="source_order",
        phasec_start_keys_used=0,
        annotated_rows=[],
        start_rows=[],
        reserved_slots=2,
        best_instance_relpath="50_completed_job_runs/run/best/best_instance.json",
    )

    assert summary["phasec_candidate_pool_unique_hash_count"] == 0
    assert summary["shadow_materializable_extra_anchor_rows"] == 0
    assert summary["room_label"] == "no_phasec_candidate_pool"


def test_candidate3_anchor_shadow_row_detects_engageable_phaseb_topk_anchor_swap() -> None:
    panel_row = _inventory_row(
        panel_job_index=4,
        fixture_seed=611,
        search_seed=7004,
        status="unsolved",
        best_stage="stage35_substitution_only",
        best_match_ratio="0.762",
        stage35_selected="1",
    )
    best_instance = {
        "instance_source_key_seed": 611,
        "status": "unsolved",
        "best_stage": "stage35_substitution_only",
        "best_match_ratio": 0.762,
        "stage3_diagnostics": {
            "phaseC_start_policy": "source_order",
            "phaseC_start_keys_used": 4,
            "phaseC_start_summaries": [
                {
                    "source": "stage3_best_phaseB",
                    "candidate_hash": "anchor",
                    "final_match": 0.750,
                },
                {
                    "source": "phaseB_topk",
                    "source_rank": 2,
                    "candidate_hash": "topk-first",
                    "final_match": 0.758,
                },
                {
                    "source": "phaseA_selected",
                    "source_rank": 1,
                    "candidate_hash": "phasea",
                    "final_match": 0.730,
                },
            ],
        },
    }

    row = candidate3_anchor_shadow_mod.build_candidate3_anchor_shadow_row(
        panel_row=panel_row,
        best_instance=best_instance,
    )

    assert row["candidate3_anchor_swap_can_engage"] == 1
    assert row["anchor_candidate_hash"] == "anchor"
    assert row["first_phaseb_topk_candidate_hash"] == "topk-first"
    assert row["phaseb_topk_minus_anchor_final_match"] == pytest.approx(0.008)
    assert row["anchor_swap_match_label"] == "phaseb_topk_better"


def test_candidate3_anchor_shadow_summary_counts_better_and_worse_cases() -> None:
    rows = [
        {
            "fixture_seed": 611,
            "benchmark_case_role": "middle_unsolved_case",
            "candidate3_anchor_swap_can_engage": 1,
            "anchor_swap_match_label": "phaseb_topk_better",
        },
        {
            "fixture_seed": 611,
            "benchmark_case_role": "middle_unsolved_case",
            "candidate3_anchor_swap_can_engage": 1,
            "anchor_swap_match_label": "anchor_better",
        },
        {
            "fixture_seed": 1111,
            "benchmark_case_role": "conversion_failure_case",
            "candidate3_anchor_swap_can_engage": 0,
            "anchor_swap_match_label": "missing_match",
        },
    ]

    summary = candidate3_anchor_shadow_mod.build_candidate3_anchor_shadow_summary(rows)

    assert summary["run_count"] == 3
    assert summary["runs_where_anchor_swap_can_engage"] == 2
    assert summary["phaseb_topk_better_count"] == 1
    assert summary["anchor_better_count"] == 1
    assert summary["candidate3_anchor_swap_shadow_live_on_panel"] == 1


def test_candidate3_exact_replay_summary_keeps_phasec_anchor_swap_fields() -> None:
    case = type(
        "Case",
        (),
        {
            "artifact_path": Path(
                "output/tools/benchmarks/periodic_sub_trans/no_wli/mock/final.json"
            ),
            "run_dir": Path(
                "output/tools/benchmarks/periodic_sub_trans/no_wli/mock/run_dir"
            ),
            "artifact": {
                "instance_source_key_seed": 611,
                "search_seed": 7004,
                "best_stage": "stage35_substitution_only",
                "best_match_ratio": 0.762,
                "stage3_diagnostics": {
                    "phaseC_best_truth_start_summary": {
                        "source": "phaseB_topk",
                        "source_rank": 2,
                        "candidate_hash": "retained-stage3-best",
                        "final_match": 0.758,
                    }
                },
            },
        },
    )()
    payload = {
        "resume_source": "saved_live_stage2_resume_rebuilt_prep",
        "stage35_enabled_effective": 0,
        "resume_best_stage": "stage3_full_refine",
        "resume_best_match_ratio": 0.781,
        "resume_best_score": 0.123,
        "stage3_flow": {
            "phaseC_ran": 1,
            "phaseC_start_keys_used": 6,
            "phaseC_start_policy": "phaseb_topk_anchor_swap_v1",
            "phaseC_start_summaries": [
                {
                    "source": "phaseB_topk",
                    "candidate_hash": "topk-anchor",
                    "final_match": 0.770,
                    "selected_by_phaseb_topk_anchor_policy": 1,
                },
                {
                    "source": "stage3_best_phaseB",
                    "candidate_hash": "demoted-anchor",
                    "final_match": 0.761,
                    "selected_by_phaseb_topk_anchor_policy": 0,
                },
            ],
        },
        "outcome": {
            "status": "unsolved",
        },
    }

    summary = candidate3_exact_mod.build_candidate3_exact_replay_summary(
        case=case,
        payload=payload,
    )

    assert summary["fixture_seed"] == 611
    assert summary["search_seed"] == 7004
    assert summary["phasec_start_policy"] == "phaseb_topk_anchor_swap_v1"
    assert summary["anchor_source"] == "phaseB_topk"
    assert summary["anchor_selected_by_phaseb_topk_anchor_policy"] == 1
    assert summary["first_phaseb_topk_candidate_hash"] == "topk-anchor"
    assert summary["phaseb_topk_minus_anchor_final_match"] == pytest.approx(0.0)
    assert summary["match_delta_vs_baseline"] == pytest.approx(0.019)
    assert summary["retained_stage3_reference_source"] == "phaseC_best_truth_start_summary"
    assert summary["retained_stage3_reference_match_ratio"] == pytest.approx(0.758)
    assert summary["match_delta_vs_retained_stage3_reference"] == pytest.approx(0.023)


def test_candidate3_extract_retained_stage3_reference_falls_back_to_stage3_topk() -> None:
    reference = candidate3_exact_mod.extract_retained_stage3_reference(
        {
            "best_stage": "stage3_full_refine",
            "best_match_ratio": 0.571,
            "stage3_topk": [
                {"rank": 1, "source": "phaseB_topk", "match_ratio": 0.564},
                {"rank": 2, "source": "phaseB_topk", "match_ratio": 0.571},
            ],
        }
    )

    assert reference["source"] == "stage3_topk"
    assert reference["stage3_source"] == "phaseB_topk"
    assert reference["source_rank"] == 2
    assert reference["match_ratio"] == pytest.approx(0.571)


def test_require_csv_columns_raises_on_missing_required_header() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        mod._require_csv_columns(
            path=Path("planning/projects/no_wli/missing.csv"),
            rows=[{"fixture_seed": "1111"}],
            required_columns=("fixture_seed", "search_seed"),
        )


def test_require_fixture_seed_coverage_raises_on_missing_seed() -> None:
    with pytest.raises(ValueError, match="Missing required fixture seeds"):
        mod._require_fixture_seed_coverage(
            path=Path("planning/projects/no_wli/focus.csv"),
            rows=[{"fixture_seed": "1111"}],
            required_fixture_seeds=(1111, 1411),
        )
