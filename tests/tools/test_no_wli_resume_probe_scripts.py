from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli import (
    resume_probe_utils as probe_utils,
    resume_seed211_stage3_policy_probe as seed211_probe,
    resume_seed411_phasec_ranking_probe as seed411_probe,
)


def _artifact_path(root: Path, run_name: str, *, seed: int) -> Path:
    return (
        root
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / run_name
        / "final_instances"
        / f"fixture_fixture_001_p9_c3_l1000__text0__seed{int(seed)}.json"
    )


def _write_artifact(root: Path, run_name: str, *, seed: int, bundle_source: str = "") -> Path:
    artifact_path = _artifact_path(root, run_name, seed=int(seed))
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("{}", encoding="utf-8")
    if bundle_source:
        manifest_path = (
            artifact_path.parents[1]
            / "resume_handoffs"
            / artifact_path.stem
            / "manifest.json"
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({"stage2_to_stage3": {"source": str(bundle_source)}}),
            encoding="utf-8",
        )
    return artifact_path


def test_resolve_probe_source_artifact_prefers_latest_live_bundle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fallback_path = _write_artifact(
        tmp_path,
        "20260324T000000000000Z__bench_solve_pipeline_no_wli__old",
        seed=211,
    )
    live_old = _write_artifact(
        tmp_path,
        "20260324T010000000000Z__bench_solve_pipeline_no_wli__mid",
        seed=211,
        bundle_source="live_stage3_pipeline",
    )
    live_new = _write_artifact(
        tmp_path,
        "20260324T020000000000Z__bench_solve_pipeline_no_wli__new",
        seed=211,
        bundle_source="live_stage3_pipeline",
    )
    monkeypatch.setattr(probe_utils, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        probe_utils,
        "NO_WLI_OUTPUT_ROOT",
        tmp_path / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli",
    )

    out = probe_utils.resolve_probe_source_artifact(
        fallback_artifact_path=fallback_path,
        key_seed=211,
        prefer_live_stage3_bundle=True,
    )

    assert Path(out["artifact_path"]) == live_new
    assert out["selection_reason"] == "latest_live_stage3_bundle"
    assert out["live_bundle_candidate_count"] == 2
    assert out["selected_bundle_source"] == "live_stage3_pipeline"
    assert live_old.relative_to(tmp_path).as_posix() in out["live_bundle_candidate_relpaths"]
    assert live_new.relative_to(tmp_path).as_posix() in out["live_bundle_candidate_relpaths"]


def test_resolve_probe_source_artifact_falls_back_without_live_bundle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fallback_path = _write_artifact(
        tmp_path,
        "20260324T000000000000Z__bench_solve_pipeline_no_wli__old",
        seed=411,
    )
    _write_artifact(
        tmp_path,
        "20260324T010000000000Z__bench_solve_pipeline_no_wli__other",
        seed=411,
    )
    monkeypatch.setattr(probe_utils, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        probe_utils,
        "NO_WLI_OUTPUT_ROOT",
        tmp_path / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli",
    )

    out = probe_utils.resolve_probe_source_artifact(
        fallback_artifact_path=fallback_path,
        key_seed=411,
        prefer_live_stage3_bundle=True,
    )

    assert Path(out["artifact_path"]) == fallback_path
    assert out["selection_reason"] == "fallback_artifact"
    assert out["live_bundle_candidate_count"] == 0
    assert out["selected_bundle_source"] == ""


def test_summarize_phasec_checkpoint_rows_reports_anchor_and_lexical_totals() -> None:
    rows = [
        {
            "lane": "anchor",
            "final_match": 0.039,
            "final_score": 0.1910,
            "source_rank": 1,
            "lexical_requests_delta": 0,
            "lexical_threshold_skips_delta": 65,
            "lexical_tiebreak_decisions_delta": 0,
        },
        {
            "lane": "challenger",
            "final_match": 0.418,
            "final_score": 0.1728,
            "source_rank": 2,
            "lexical_requests_delta": 0,
            "lexical_threshold_skips_delta": 60,
            "lexical_tiebreak_decisions_delta": 0,
        },
    ]

    out = probe_utils.summarize_phasec_checkpoint_rows(rows)

    assert out["row_count"] == 2
    assert out["best_truth_match"] == 0.418
    assert out["best_truth_lane"] == "challenger"
    assert out["best_score_match"] == 0.039
    assert out["anchor_final_match"] == 0.039
    assert out["lexical_threshold_skips_total"] == 125
    assert out["lexical_tiebreak_decisions_total"] == 0


def test_seed411_variant_row_reports_between_family_truth_gap(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "phasec_start_checkpoints.jsonl"
    checkpoint_path.write_text(
        "\n".join(
            [
                json.dumps({"lane": "anchor", "final_match": 0.039, "final_score": 0.1910}),
                json.dumps({"lane": "challenger", "final_match": 0.418, "final_score": 0.1728}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    row = seed411_probe._variant_row(
        variant_id="baseline",
        description="desc",
        output_dir=tmp_path,
        payload={
            "resume_best_stage": "stage2_search",
            "resume_best_match_ratio": 0.039,
            "resume_best_score": 0.1910,
            "resume_source": "saved_live_bundle",
            "bundle_dir_relpath": "output/test_bundle",
            "stage3_flow": {
                "stop_reason": "stalled",
                "phaseC_final_winner_lane": "anchor",
                "phaseC_final_winner_source": "stage3_best_phaseB",
            },
        },
    )

    assert row["resume_source"] == "saved_live_bundle"
    assert row["checkpoint_summary"]["best_truth_match"] == 0.418
    assert abs(float(row["between_family_truth_gap"]) - 0.379) < 1e-9


def test_seed211_variant_row_exposes_resume_source(tmp_path: Path) -> None:
    row = seed211_probe._variant_row(
        variant_id="baseline",
        description="desc",
        output_dir=tmp_path,
        payload={
            "resume_best_stage": "stage3_full_refine",
            "resume_best_match_ratio": 0.574,
            "resume_best_score": 0.2368,
            "resume_source": "saved_live_bundle",
            "bundle_dir_relpath": "output/test_bundle",
            "stage3_flow": {
                "best3_match": 0.574,
                "best3_score": 0.2368,
                "stop_reason": "complete",
                "stage35_selected": 0,
                "phaseC_final_winner_lane": "anchor",
                "phaseC_final_winner_source": "stage3_best_phaseB",
            },
        },
    )

    assert row["resume_source"] == "saved_live_bundle"
    assert row["bundle_dir_relpath"] == "output/test_bundle"
    assert row["resume_best_match_ratio"] == 0.574
