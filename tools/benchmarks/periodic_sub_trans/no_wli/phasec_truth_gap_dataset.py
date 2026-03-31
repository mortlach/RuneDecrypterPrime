from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_truth_reporting import (
    build_phasec_truth_reporting,
)


def build_phasec_truth_gap_row(
    *,
    artifact_path: Path,
    artifact: Mapping[str, Any],
) -> Dict[str, Any] | None:
    stage3_diag = dict(artifact.get("stage3_diagnostics", {}) or {})
    reporting = build_phasec_truth_reporting(
        phasec_start_summaries=list(stage3_diag.get("phaseC_start_summaries", []) or []),
        phasec_final_winner_lane=str(stage3_diag.get("phaseC_final_winner_lane", "") or ""),
        phasec_final_winner_source=str(stage3_diag.get("phaseC_final_winner_source", "") or ""),
    )
    disagreement = dict(reporting.get("phaseC_truth_disagreement_summary", {}) or {})
    if int(reporting.get("phaseC_truth_reporting_available", 0) or 0) != 1:
        return None
    if int(disagreement.get("best_truth_challenger_available", 0) or 0) != 1:
        return None

    run_dir = artifact_path.parents[1]
    winner = dict(reporting.get("phaseC_score_selected_winner_summary", {}) or {})
    challenger = dict(reporting.get("phaseC_best_truth_challenger_summary", {}) or {})
    return dict(
        run_dir=str(run_dir).replace("\\", "/"),
        artifact_path=str(artifact_path).replace("\\", "/"),
        tier=str(artifact.get("tier", "") or ""),
        text_id=int(artifact.get("text_id", 0) or 0),
        key_seed=int(artifact.get("key_seed", 0) or 0),
        best_stage=str(artifact.get("best_stage", "") or ""),
        best_match_ratio=float(artifact.get("best_match_ratio", float("nan"))),
        stage3_match_ratio=float(artifact.get("stage3_match_ratio", float("nan"))),
        phaseC_start_policy=str(stage3_diag.get("phaseC_start_policy", "") or ""),
        phaseB_top_n_used=int(stage3_diag.get("phaseB_top_n_used", 0) or 0),
        phaseC_candidate_pool_count=int(
            stage3_diag.get("phaseC_candidate_pool_count", 0) or 0
        ),
        phaseC_start_keys_used=int(stage3_diag.get("phaseC_start_keys_used", 0) or 0),
        winner_candidate_hash=str(winner.get("candidate_hash", "") or ""),
        winner_source=str(winner.get("source", "") or ""),
        winner_lane=str(winner.get("lane", "") or ""),
        winner_selection_bucket=str(winner.get("selection_bucket", "") or ""),
        winner_selected_by_novel_policy=int(
            winner.get("selected_by_novel_policy", 0) or 0
        ),
        winner_truth_match=disagreement.get("winner_truth_match"),
        winner_score=disagreement.get("winner_score"),
        challenger_candidate_hash=str(challenger.get("candidate_hash", "") or ""),
        challenger_source=str(challenger.get("source", "") or ""),
        challenger_lane=str(challenger.get("lane", "") or ""),
        challenger_selection_bucket=str(
            challenger.get("selection_bucket", "") or ""
        ),
        challenger_selected_by_novel_policy=int(
            challenger.get("selected_by_novel_policy", 0) or 0
        ),
        challenger_truth_match=disagreement.get("best_truth_challenger_match"),
        challenger_score=disagreement.get("best_truth_challenger_score"),
        truth_gap_vs_winner=disagreement.get(
            "truth_gap_best_truth_challenger_vs_winner"
        ),
        score_gap_vs_winner=disagreement.get(
            "score_gap_best_truth_challenger_vs_winner"
        ),
        winner_and_best_truth_differ=int(
            disagreement.get("winner_and_best_truth_differ", 0) or 0
        ),
    )


def collect_phasec_truth_gap_rows(
    root: Path,
    *,
    min_truth_gap: float = 0.05,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for artifact_path in sorted(root.glob("*/final_instances/*.json")):
        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(artifact, Mapping):
            continue
        row = build_phasec_truth_gap_row(
            artifact_path=artifact_path,
            artifact=artifact,
        )
        if row is None:
            continue
        truth_gap = float(row.get("truth_gap_vs_winner", float("nan")))
        if not math.isfinite(truth_gap) or float(truth_gap) < float(min_truth_gap):
            continue
        if int(row.get("winner_and_best_truth_differ", 0) or 0) != 1:
            continue
        if not str(row.get("challenger_candidate_hash", "") or ""):
            continue
        rows.append(dict(row))
    rows.sort(
        key=lambda row: (
            float(row.get("truth_gap_vs_winner", float("-inf"))),
            float(row.get("challenger_truth_match", float("-inf"))),
            -float(row.get("winner_score", float("inf"))),
            str(row.get("artifact_path", "")),
        ),
        reverse=True,
    )
    return rows


def write_phasec_truth_gap_dataset(
    *,
    rows: Sequence[Mapping[str, Any]],
    output_dir: Path,
    top_n: int = 12,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    row_dicts = [dict(row) for row in list(rows or [])]
    summary = dict(
        row_count=int(len(row_dicts)),
        top_truth_gap_rows=[dict(row) for row in row_dicts[: int(max(0, int(top_n)))]],
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "rows.json").write_text(
        json.dumps(row_dicts, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    fieldnames = [
        "artifact_path",
        "key_seed",
        "best_stage",
        "best_match_ratio",
        "stage3_match_ratio",
        "phaseC_start_policy",
        "phaseB_top_n_used",
        "phaseC_candidate_pool_count",
        "phaseC_start_keys_used",
        "winner_candidate_hash",
        "winner_source",
        "winner_lane",
        "winner_selection_bucket",
        "winner_selected_by_novel_policy",
        "winner_truth_match",
        "winner_score",
        "challenger_candidate_hash",
        "challenger_source",
        "challenger_lane",
        "challenger_selection_bucket",
        "challenger_selected_by_novel_policy",
        "challenger_truth_match",
        "challenger_score",
        "truth_gap_vs_winner",
        "score_gap_vs_winner",
        "winner_and_best_truth_differ",
    ]
    with (output_dir / "rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in row_dicts:
            writer.writerow({field: row.get(field) for field in fieldnames})

    lines = [
        "# Phase-C Truth Gap Dataset",
        "",
        f"- row count: `{int(len(row_dicts))}`",
        "",
        "| artifact | seed | winner truth | challenger truth | truth gap | winner score | challenger score | start policy |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in row_dicts[: int(max(0, int(top_n)))]:
        lines.append(
            "| {artifact} | {seed} | {winner_truth:.3f} | {challenger_truth:.3f} | {gap:.3f} | {winner_score:.6f} | {challenger_score:.6f} | {policy} |".format(
                artifact=str(row.get("artifact_path", "")),
                seed=int(row.get("key_seed", 0) or 0),
                winner_truth=float(row.get("winner_truth_match", float("nan"))),
                challenger_truth=float(
                    row.get("challenger_truth_match", float("nan"))
                ),
                gap=float(row.get("truth_gap_vs_winner", float("nan"))),
                winner_score=float(row.get("winner_score", float("nan"))),
                challenger_score=float(row.get("challenger_score", float("nan"))),
                policy=str(row.get("phaseC_start_policy", "") or ""),
            )
        )
    (output_dir / "summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return dict(summary)
