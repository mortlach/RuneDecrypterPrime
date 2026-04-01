from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_frontier_rows import (
    load_phasec_frontier_rows_with_source,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_truth_reporting import (
    build_phasec_truth_reporting,
)


REPO_ROOT = Path(__file__).resolve().parents[4]


def _as_int_list(value: Any) -> list[int]:
    if isinstance(value, (str, bytes)) or value is None:
        return []
    try:
        return [int(v) for v in list(value)]
    except Exception:
        return []


def _repo_rel_or_str(path_like: Any) -> str:
    if path_like in (None, ""):
        return ""
    path = Path(path_like)
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def _normalize_frontier_candidate(row_obj: Mapping[str, Any]) -> Dict[str, Any]:
    row = dict(row_obj)
    return dict(
        start_idx=int(row.get("start_idx", 0) or 0),
        lane=str(row.get("lane", "") or ""),
        source=str(row.get("source", "") or ""),
        source_rank=int(row.get("source_rank", 0) or 0),
        candidate_hash=str(row.get("candidate_hash", "") or ""),
        selection_bucket=str(row.get("selection_bucket", "") or ""),
        selected_by_novel_policy=int(row.get("selected_by_novel_policy", 0) or 0),
        eligible_novel_challenger=int(
            row.get("eligible_novel_challenger", 0) or 0
        ),
        novelty_distance_to_anchor=(
            int(row["novelty_distance_to_anchor"])
            if row.get("novelty_distance_to_anchor", None) is not None
            else None
        ),
        novelty_min_distance_to_selected_challenger=(
            int(row["novelty_min_distance_to_selected_challenger"])
            if row.get("novelty_min_distance_to_selected_challenger", None) is not None
            else None
        ),
        init_match=row.get("init_match"),
        final_match=row.get("final_match"),
        init_score=row.get("init_score"),
        final_score=row.get("final_score"),
        init_search_score=row.get("init_search_score"),
        match_gain=row.get("match_gain"),
        score_gain=row.get("score_gain"),
        became_global_best=int(row.get("became_global_best", 0) or 0),
        overtook_anchor=int(row.get("overtook_anchor", 0) or 0),
        init_key_idx=_as_int_list(row.get("init_key_idx", [])),
        init_plaintext_idx=_as_int_list(row.get("init_plaintext_idx", [])),
        final_key_idx=_as_int_list(row.get("final_key_idx", [])),
        final_plaintext_idx=_as_int_list(row.get("final_plaintext_idx", [])),
    )


def build_late_stage_frontier_fixture(
    *,
    artifact_path: Path,
    artifact: Mapping[str, Any],
    fixture_id: str,
) -> Dict[str, Any]:
    artifact_obj = dict(artifact or {})
    stage3_diag = dict(artifact_obj.get("stage3_diagnostics", {}) or {})
    frontier_payload = load_phasec_frontier_rows_with_source(
        artifact_path=artifact_path,
        artifact=artifact_obj,
    )
    candidate_rows = [
        _normalize_frontier_candidate(row)
        for row in list(frontier_payload.get("rows", []) or [])
        if isinstance(row, Mapping)
    ]
    reporting = build_phasec_truth_reporting(
        phasec_start_summaries=candidate_rows,
        phasec_final_winner_lane=str(stage3_diag.get("phaseC_final_winner_lane", "") or ""),
        phasec_final_winner_source=str(
            stage3_diag.get("phaseC_final_winner_source", "") or ""
        ),
    )
    disagreement = dict(reporting.get("phaseC_truth_disagreement_summary", {}) or {})
    winner = dict(reporting.get("phaseC_score_selected_winner_summary", {}) or {})
    oracle_best = dict(reporting.get("phaseC_best_truth_challenger_summary", {}) or {})
    rows_with_final_key = sum(
        1 for row in candidate_rows if list(row.get("final_key_idx", []))
    )
    rows_with_final_plaintext = sum(
        1 for row in candidate_rows if list(row.get("final_plaintext_idx", []))
    )
    return dict(
        fixture_id=str(fixture_id),
        source_artifact_path=_repo_rel_or_str(artifact_path),
        run_id=str(artifact_path.parents[1].name),
        tier=str(artifact_obj.get("tier", "") or ""),
        text_id=int(artifact_obj.get("text_id", 0) or 0),
        seed=int(artifact_obj.get("key_seed", 0) or 0),
        period=int(artifact_obj.get("period", 0) or 0),
        columns=int(artifact_obj.get("columns", 0) or 0),
        length=int(artifact_obj.get("length", 0) or 0),
        best_stage=str(artifact_obj.get("best_stage", "") or ""),
        best_match_ratio=artifact_obj.get("best_match_ratio"),
        stage3_match_ratio=artifact_obj.get("stage3_match_ratio"),
        phasec_start_policy=str(stage3_diag.get("phaseC_start_policy", "") or ""),
        phasec_frontier_row_source=str(frontier_payload.get("source", "") or ""),
        phasec_checkpoint_path=_repo_rel_or_str(
            frontier_payload.get("checkpoint_path", "") or ""
        ),
        phaseb_top_n_used=int(stage3_diag.get("phaseB_top_n_used", 0) or 0),
        target_plaintext_idx=_as_int_list(artifact_obj.get("target_plaintext_idx", [])),
        ciphertext_idx=_as_int_list(artifact_obj.get("ciphertext_idx", [])),
        score_selected_winner_hash=str(winner.get("candidate_hash", "") or ""),
        oracle_best_explored_hash=str(oracle_best.get("candidate_hash", "") or ""),
        oracle_truth_disagreement=dict(disagreement),
        candidate_count=int(len(candidate_rows)),
        candidates_with_final_key_idx=int(rows_with_final_key),
        candidates_with_final_plaintext_idx=int(rows_with_final_plaintext),
        frontier_key_material_complete=int(
            1
            if candidate_rows
            and rows_with_final_key == len(candidate_rows)
            and rows_with_final_plaintext == len(candidate_rows)
            else 0
        ),
        candidates=[dict(row) for row in candidate_rows],
    )


def write_late_stage_frontier_fixture(
    *,
    fixture: Mapping[str, Any],
    output_path: Path,
) -> Dict[str, Any]:
    out = dict(fixture or {})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(out, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return out
