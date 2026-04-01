from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_benchmark import (
    build_frontier_trial_material_rows,
    build_late_stage_candidate_feature_table,
    build_weighted_score_plus_novelty_config,
    build_weighted_score_plus_novelty_plus_source_penalties_config,
    load_late_stage_frontier_fixture,
    select_legacy_frontier_winner,
    select_weighted_frontier_candidate,
)


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return float(out)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _selection_summary(
    *,
    selector_name: str,
    selected_row: Mapping[str, Any],
    trial_row: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    row = dict(selected_row or {})
    trial = dict(trial_row or {})
    final_key_idx = list(trial.get("final_key_idx", []) or [])
    final_plaintext_idx = list(trial.get("final_plaintext_idx", []) or [])
    return dict(
        selector=str(selector_name),
        candidate_hash=str(row.get("candidate_hash", "") or ""),
        lane=str(row.get("lane", "") or ""),
        source=str(row.get("source", "") or ""),
        source_rank=_safe_int(row.get("source_rank", 0)),
        eligible_novel_challenger=_safe_int(
            row.get("eligible_novel_challenger", 0)
        ),
        novelty_distance_to_anchor=row.get("novelty_distance_to_anchor", None),
        final_score=_safe_float(row.get("final_score")),
        final_match=_safe_float(row.get("final_match")),
        replay_material_complete=int(trial.get("replay_material_complete", 0) or 0),
        final_key_idx_len=int(len(final_key_idx)),
        final_plaintext_idx_len=int(len(final_plaintext_idx)),
        final_key_idx=list(final_key_idx),
        final_plaintext_idx=list(final_plaintext_idx),
    )


def build_stageb_fixture_comparison(
    fixture: Mapping[str, Any],
) -> Dict[str, Any]:
    fixture_obj = dict(fixture or {})
    feature_rows = build_late_stage_candidate_feature_table(fixture_obj)
    trial_rows = build_frontier_trial_material_rows(fixture_obj)
    by_hash = {
        str(row.get("candidate_hash", "") or ""): dict(row)
        for row in trial_rows
        if str(row.get("candidate_hash", "") or "")
    }

    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture_obj.get("score_selected_winner_hash", "") or ""),
    )
    score_plus_novelty = select_weighted_frontier_candidate(
        feature_rows,
        config=build_weighted_score_plus_novelty_config(),
    )
    score_plus_novelty_plus_source_penalties = select_weighted_frontier_candidate(
        feature_rows,
        config=build_weighted_score_plus_novelty_plus_source_penalties_config(),
    )
    oracle_hash = str(fixture_obj.get("oracle_best_explored_hash", "") or "")
    oracle = next(
        (
            dict(row)
            for row in feature_rows
            if str(row.get("candidate_hash", "") or "") == oracle_hash
        ),
        {},
    )

    legacy_summary = _selection_summary(
        selector_name="legacy",
        selected_row=legacy,
        trial_row=by_hash.get(str(legacy.get("candidate_hash", "") or "")),
    )
    baseline_summary = _selection_summary(
        selector_name="score_plus_novelty",
        selected_row=score_plus_novelty,
        trial_row=by_hash.get(str(score_plus_novelty.get("candidate_hash", "") or "")),
    )
    source_penalty_summary = _selection_summary(
        selector_name="score_plus_novelty_plus_source_penalties",
        selected_row=score_plus_novelty_plus_source_penalties,
        trial_row=by_hash.get(
            str(score_plus_novelty_plus_source_penalties.get("candidate_hash", "") or "")
        ),
    )
    oracle_summary = _selection_summary(
        selector_name="oracle_best_explored",
        selected_row=oracle,
        trial_row=by_hash.get(str(oracle.get("candidate_hash", "") or "")),
    )

    return dict(
        fixture_id=str(fixture_obj.get("fixture_id", "") or ""),
        run_id=str(fixture_obj.get("run_id", "") or ""),
        source_artifact_path=str(fixture_obj.get("source_artifact_path", "") or ""),
        phasec_start_policy=str(fixture_obj.get("phasec_start_policy", "") or ""),
        phasec_frontier_row_source=str(
            fixture_obj.get("phasec_frontier_row_source", "") or ""
        ),
        phasec_checkpoint_path=str(fixture_obj.get("phasec_checkpoint_path", "") or ""),
        candidate_count=_safe_int(fixture_obj.get("candidate_count", 0)),
        frontier_key_material_complete=_safe_int(
            fixture_obj.get("frontier_key_material_complete", 0)
        ),
        score_selected_winner_hash=str(
            fixture_obj.get("score_selected_winner_hash", "") or ""
        ),
        oracle_best_explored_hash=str(
            fixture_obj.get("oracle_best_explored_hash", "") or ""
        ),
        legacy=legacy_summary,
        score_plus_novelty=baseline_summary,
        score_plus_novelty_plus_source_penalties=source_penalty_summary,
        oracle_best_explored=oracle_summary,
        score_plus_novelty_truth_gain_vs_legacy=(
            float(baseline_summary["final_match"]) - float(legacy_summary["final_match"])
            if baseline_summary["final_match"] is not None
            and legacy_summary["final_match"] is not None
            else None
        ),
        source_penalty_truth_gain_vs_legacy=(
            float(source_penalty_summary["final_match"])
            - float(legacy_summary["final_match"])
            if source_penalty_summary["final_match"] is not None
            and legacy_summary["final_match"] is not None
            else None
        ),
        replay_ready_selected_candidates=int(
            1
            if all(
                int(summary.get("replay_material_complete", 0) or 0) == 1
                for summary in (
                    legacy_summary,
                    baseline_summary,
                    source_penalty_summary,
                    oracle_summary,
                )
                if str(summary.get("candidate_hash", "") or "")
            )
            else 0
        ),
    )


def build_stageb_selected_trial_material_rows(
    *,
    fixture_label: str,
    fixture: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    comparison = build_stageb_fixture_comparison(fixture)
    out: list[Dict[str, Any]] = []
    for key in (
        "legacy",
        "score_plus_novelty",
        "score_plus_novelty_plus_source_penalties",
        "oracle_best_explored",
    ):
        row = dict(comparison.get(key, {}) or {})
        out.append(
            dict(
                fixture_label=str(fixture_label),
                fixture_id=str(comparison.get("fixture_id", "") or ""),
                run_id=str(comparison.get("run_id", "") or ""),
                source_artifact_path=str(
                    comparison.get("source_artifact_path", "") or ""
                ),
                phasec_start_policy=str(
                    comparison.get("phasec_start_policy", "") or ""
                ),
                selector=str(row.get("selector", "") or ""),
                candidate_hash=str(row.get("candidate_hash", "") or ""),
                source=str(row.get("source", "") or ""),
                lane=str(row.get("lane", "") or ""),
                final_score=row.get("final_score"),
                final_match=row.get("final_match"),
                replay_material_complete=int(
                    row.get("replay_material_complete", 0) or 0
                ),
                final_key_idx=list(row.get("final_key_idx", []) or []),
                final_plaintext_idx=list(row.get("final_plaintext_idx", []) or []),
            )
        )
    return out


def write_stageb_replay_report(
    *,
    control_fixture: Mapping[str, Any],
    candidate_fixture: Mapping[str, Any],
    output_dir: Path,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    control_comp = build_stageb_fixture_comparison(control_fixture)
    candidate_comp = build_stageb_fixture_comparison(candidate_fixture)
    control_feature_rows = build_late_stage_candidate_feature_table(control_fixture)
    candidate_feature_rows = build_late_stage_candidate_feature_table(candidate_fixture)
    control_trial_rows = build_frontier_trial_material_rows(control_fixture)
    candidate_trial_rows = build_frontier_trial_material_rows(candidate_fixture)
    selected_trial_rows = (
        build_stageb_selected_trial_material_rows(
            fixture_label="control",
            fixture=control_fixture,
        )
        + build_stageb_selected_trial_material_rows(
            fixture_label="candidate",
            fixture=candidate_fixture,
        )
    )
    summary = dict(
        control=control_comp,
        candidate=candidate_comp,
        shared_oracle_hash_match=int(
            1
            if str(control_comp.get("oracle_best_explored_hash", "") or "")
            == str(candidate_comp.get("oracle_best_explored_hash", "") or "")
            else 0
        ),
        shared_legacy_hash_match=int(
            1
            if str(control_comp.get("legacy", {}).get("candidate_hash", "") or "")
            == str(candidate_comp.get("legacy", {}).get("candidate_hash", "") or "")
            else 0
        ),
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "control_feature_rows.json").write_text(
        json.dumps(control_feature_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "candidate_feature_rows.json").write_text(
        json.dumps(candidate_feature_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "control_trial_material_rows.json").write_text(
        json.dumps(control_trial_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "candidate_trial_material_rows.json").write_text(
        json.dumps(candidate_trial_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "selected_trial_material_rows.json").write_text(
        json.dumps(selected_trial_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Late-Stage Selector Stage B",
        "",
        "## Control",
        "",
        f"- fixture: `{control_comp['fixture_id']}`",
        f"- start policy: `{control_comp['phasec_start_policy']}`",
        f"- frontier row source: `{control_comp['phasec_frontier_row_source']}`",
        f"- frontier key material complete: `{control_comp['frontier_key_material_complete']}`",
        f"- legacy candidate: `{control_comp['legacy']['candidate_hash']}` truth `{control_comp['legacy']['final_match']}`",
        f"- score+novelty candidate: `{control_comp['score_plus_novelty']['candidate_hash']}` truth `{control_comp['score_plus_novelty']['final_match']}`",
        f"- source-penalty candidate: `{control_comp['score_plus_novelty_plus_source_penalties']['candidate_hash']}` truth `{control_comp['score_plus_novelty_plus_source_penalties']['final_match']}`",
        f"- oracle-best explored: `{control_comp['oracle_best_explored']['candidate_hash']}` truth `{control_comp['oracle_best_explored']['final_match']}`",
        "",
        "## Candidate",
        "",
        f"- fixture: `{candidate_comp['fixture_id']}`",
        f"- start policy: `{candidate_comp['phasec_start_policy']}`",
        f"- frontier row source: `{candidate_comp['phasec_frontier_row_source']}`",
        f"- frontier key material complete: `{candidate_comp['frontier_key_material_complete']}`",
        f"- legacy candidate: `{candidate_comp['legacy']['candidate_hash']}` truth `{candidate_comp['legacy']['final_match']}`",
        f"- score+novelty candidate: `{candidate_comp['score_plus_novelty']['candidate_hash']}` truth `{candidate_comp['score_plus_novelty']['final_match']}`",
        f"- source-penalty candidate: `{candidate_comp['score_plus_novelty_plus_source_penalties']['candidate_hash']}` truth `{candidate_comp['score_plus_novelty_plus_source_penalties']['final_match']}`",
        f"- oracle-best explored: `{candidate_comp['oracle_best_explored']['candidate_hash']}` truth `{candidate_comp['oracle_best_explored']['final_match']}`",
        "",
        "## Replay Readiness",
        "",
        f"- control selected candidates replay-ready: `{control_comp['replay_ready_selected_candidates']}`",
        f"- candidate selected candidates replay-ready: `{candidate_comp['replay_ready_selected_candidates']}`",
        f"- shared legacy hash across runs: `{summary['shared_legacy_hash_match']}`",
        f"- shared oracle hash across runs: `{summary['shared_oracle_hash_match']}`",
        "",
        "Selected trial material rows are saved in `selected_trial_material_rows.json` for direct trial-key or replay tests.",
        "",
    ]
    (output_dir / "summary.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    return summary


def load_and_write_stageb_replay_report(
    *,
    control_fixture_path: Path,
    candidate_fixture_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    control_fixture = load_late_stage_frontier_fixture(control_fixture_path)
    candidate_fixture = load_late_stage_frontier_fixture(candidate_fixture_path)
    return write_stageb_replay_report(
        control_fixture=control_fixture,
        candidate_fixture=candidate_fixture,
        output_dir=output_dir,
    )
