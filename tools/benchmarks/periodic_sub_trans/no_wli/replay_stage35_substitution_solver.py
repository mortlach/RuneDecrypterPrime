from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import (
    replay_phasec_rescue_sweep as phasec_replay_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_candidate_archive import (
    build_stage35_seed_archive,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_substitution_solver import (
    DEFAULT_STAGE35_SOLVER_CFG,
    solve_stage35_substitution_only,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (
    refresh_catalog_safely,
)


RUN_LABEL = "stage35_substitution_replay_v1"
OUTPUT_ROOT = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "stage35_substitution_replay"
)
FILTER_PERIOD = 9
FILTER_COLUMNS = 3
FILTER_LENGTH = 1000
MAX_CASES = 8
SOLVER_CFG = dict(
    seed_keep=4,
    beam_width=4,
    archive_keep=16,
    rounds=3,
    mini_search_steps=2,
    mini_search_beam_width=3,
    mini_search_top_symbols=10,
    mini_search_final_keep=2,
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _truth_match_ratio(plaintext_idx: Sequence[int], target_plaintext_idx: Sequence[int]) -> float:
    lhs = np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)
    rhs = np.asarray(target_plaintext_idx, dtype=np.uint8).reshape(-1)
    if int(lhs.size) == 0 or int(rhs.size) == 0 or int(lhs.size) != int(rhs.size):
        return float("nan")
    return float(np.mean(lhs == rhs))


def _truth_better(
    cand_match: float,
    cand_score: float,
    best_match: float,
    best_score: float,
) -> bool:
    if np.isfinite(cand_match) and np.isfinite(best_match):
        if float(cand_match) > float(best_match):
            return True
        if float(cand_match) < float(best_match):
            return False
    elif np.isfinite(cand_match):
        return True
    elif np.isfinite(best_match):
        return False
    if np.isfinite(cand_score) and np.isfinite(best_score):
        return bool(float(cand_score) > float(best_score))
    return bool(np.isfinite(cand_score) and not np.isfinite(best_score))


def _discover_stage35_cases_with_stats() -> tuple[list[phasec_replay_mod.ArtifactCase], dict[str, Any]]:
    out: list[phasec_replay_mod.ArtifactCase] = []
    filtered_case_count = 0
    empty_stage3_topk_case_count = 0
    for case in phasec_replay_mod.discover_artifact_cases():
        artifact = dict(case.artifact)
        if int(artifact.get("period", 0) or 0) != int(FILTER_PERIOD):
            continue
        if int(artifact.get("columns", 0) or 0) != int(FILTER_COLUMNS):
            continue
        if int(artifact.get("length", 0) or 0) != int(FILTER_LENGTH):
            continue
        filtered_case_count += 1
        if not list(artifact.get("stage3_topk", []) or []):
            empty_stage3_topk_case_count += 1
        out.append(case)
    pre_limit_case_count = int(len(out))
    if MAX_CASES is not None:
        out = out[-int(MAX_CASES) :]
    return out, dict(
        filtered_case_count=int(filtered_case_count),
        empty_stage3_topk_case_count=int(empty_stage3_topk_case_count),
        nonempty_stage3_topk_case_count=int(
            max(0, int(filtered_case_count) - int(empty_stage3_topk_case_count))
        ),
        pre_limit_case_count=int(pre_limit_case_count),
        selected_case_count=int(len(out)),
    )


def discover_stage35_cases() -> list[phasec_replay_mod.ArtifactCase]:
    cases, _stats = _discover_stage35_cases_with_stats()
    return cases


def evaluate_stage35_case(
    case: phasec_replay_mod.ArtifactCase,
    *,
    chunk_size: int = phasec_replay_mod.ANALYSIS_BATCH_CHUNK_SIZE,
    require_batch: bool = phasec_replay_mod.ANALYSIS_REQUIRE_BATCH_SCORING,
) -> dict[str, Any]:
    artifact = dict(case.artifact)
    run_config = dict(case.run_config)
    artifact_relpath = phasec_replay_mod._repo_rel(case.artifact_path)
    target_plaintext_idx = np.asarray(
        artifact.get("target_plaintext_idx", []),
        dtype=np.uint8,
    ).reshape(-1)
    seed_archive = build_stage35_seed_archive(artifact)
    seed_rows = list(seed_archive.get("seed_rows", []))
    if not seed_rows:
        return dict(
            artifact_relpath=str(artifact_relpath),
            run_id=str(case.run_dir.name),
            archive_rows=[],
            case_summary=dict(
                artifact_relpath=str(artifact_relpath),
                run_id=str(case.run_dir.name),
                seed_count=0,
                stage35_archive_count=0,
                outcome="tie",
                top_match=float("nan"),
                baseline_match=float(artifact.get("best_match_ratio", float("nan"))),
                best_truth_match=float("nan"),
                runtime_seconds=0.0,
            ),
        )
    cipher = phasec_replay_mod._build_cipher(artifact)
    scorer_full = phasec_replay_mod._build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="scorer",
    )
    scorer_search = phasec_replay_mod._build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="search_scorer",
    )
    solver_out = solve_stage35_substitution_only(
        ciphertext_idx=np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8).reshape(-1),
        seed_rows=seed_rows,
        period=int(artifact.get("period", 0) or 0),
        alphabet_size=int(artifact.get("alphabet_size", 0) or 0),
        cipher=cipher,
        scorer_full=scorer_full,
        scorer_search=scorer_search,
        cfg=SOLVER_CFG,
        chunk_size=int(chunk_size),
        require_batch=bool(require_batch),
        fixed_tail=list(seed_archive.get("frozen_tail", [])),
    )
    archive_rows = [dict(row) for row in list(solver_out.get("archive_rows", []))]
    baseline_match = float(artifact.get("best_match_ratio", float("nan")))
    baseline_score = float(artifact.get("best_score", float("nan")))
    enriched_rows: list[dict[str, Any]] = []
    best_truth_row: dict[str, Any] | None = None
    for rank_idx, row in enumerate(archive_rows, start=1):
        pt = list(map(int, row.get("plaintext_idx", []) or []))
        truth_match = _truth_match_ratio(pt, target_plaintext_idx)
        enriched = dict(
            row,
            artifact_relpath=str(artifact_relpath),
            run_id=str(case.run_dir.name),
            archive_rank=int(rank_idx),
            truth_match=float(truth_match),
            truth_gain=(
                float(truth_match - baseline_match)
                if np.isfinite(truth_match) and np.isfinite(baseline_match)
                else float("nan")
            ),
            top_rank_live_visible_only=1,
        )
        enriched_rows.append(enriched)
        if best_truth_row is None or _truth_better(
            float(enriched.get("truth_match", float("nan"))),
            float(enriched.get("score", float("nan"))),
            float(best_truth_row.get("truth_match", float("nan"))),
            float(best_truth_row.get("score", float("nan"))),
        ):
            best_truth_row = dict(enriched)

    top_row = dict(enriched_rows[0]) if enriched_rows else {}
    top_match = float(top_row.get("truth_match", float("nan")))
    top_score = float(top_row.get("score", float("nan")))
    if _truth_better(float(top_match), float(top_score), float(baseline_match), float(baseline_score)):
        outcome = "win"
    elif _truth_better(float(baseline_match), float(baseline_score), float(top_match), float(top_score)):
        outcome = "loss"
    else:
        outcome = "tie"
    diversity = dict(solver_out.get("diversity", {}) or {})
    case_summary = dict(
        artifact_relpath=str(artifact_relpath),
        run_id=str(case.run_dir.name),
        seed_count=int(len(seed_rows)),
        seed_tail_mismatch_count=int(seed_archive.get("tail_mismatch_count", 0)),
        seed_source_counts=dict(seed_archive.get("seed_source_counts", {})),
        stage35_archive_count=int(len(enriched_rows)),
        stage35_rounds_completed=int(solver_out.get("rounds_completed", 0) or 0),
        stage35_evals=int(solver_out.get("evals", 0) or 0),
        runtime_seconds=float(solver_out.get("runtime_seconds", 0.0) or 0.0),
        outcome=str(outcome),
        baseline_match=float(baseline_match),
        baseline_score=float(baseline_score),
        top_match=float(top_match),
        top_score=float(top_score),
        top_gain=(
            float(top_match - baseline_match)
            if np.isfinite(top_match) and np.isfinite(baseline_match)
            else float("nan")
        ),
        best_truth_match=float(best_truth_row.get("truth_match", float("nan")))
        if best_truth_row is not None
        else float("nan"),
        best_truth_score=float(best_truth_row.get("score", float("nan")))
        if best_truth_row is not None
        else float("nan"),
        best_truth_gain=(
            float(best_truth_row.get("truth_match", float("nan")) - baseline_match)
            if best_truth_row is not None
            and np.isfinite(float(best_truth_row.get("truth_match", float("nan"))))
            and np.isfinite(baseline_match)
            else float("nan")
        ),
        best_truth_rank=int(best_truth_row.get("archive_rank", 0) or 0)
        if best_truth_row is not None
        else 0,
        archive_diversity_unique_keys=int(diversity.get("unique_keys", 0) or 0),
        archive_diversity_unique_seed_sources=int(
            diversity.get("unique_seed_sources", 0) or 0
        ),
        archive_diversity_unique_target_slices=int(
            diversity.get("unique_target_slices", 0) or 0
        ),
        archive_diversity_mean_substitution_hamming=float(
            diversity.get("mean_substitution_hamming", 0.0) or 0.0
        ),
    )
    return dict(
        artifact_relpath=str(artifact_relpath),
        run_id=str(case.run_dir.name),
        archive_rows=enriched_rows,
        case_summary=case_summary,
    )


def summarize_case_summaries(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    case_rows = [dict(row) for row in rows]
    wins = [row for row in case_rows if str(row.get("outcome", "")) == "win"]
    losses = [row for row in case_rows if str(row.get("outcome", "")) == "loss"]
    ties = [row for row in case_rows if str(row.get("outcome", "")) == "tie"]
    top_gains = [
        float(row.get("top_gain", float("nan")))
        for row in case_rows
        if np.isfinite(float(row.get("top_gain", float("nan"))))
    ]
    best_truth_gains = [
        float(row.get("best_truth_gain", float("nan")))
        for row in case_rows
        if np.isfinite(float(row.get("best_truth_gain", float("nan"))))
    ]
    runtimes = [
        float(row.get("runtime_seconds", 0.0) or 0.0)
        for row in case_rows
        if np.isfinite(float(row.get("runtime_seconds", float("nan"))))
    ]
    return dict(
        case_count=int(len(case_rows)),
        wins=int(len(wins)),
        losses=int(len(losses)),
        ties=int(len(ties)),
        best_top_gain=(max(top_gains) if top_gains else float("nan")),
        average_top_gain=(
            float(np.mean(np.asarray(top_gains, dtype=np.float64)))
            if top_gains
            else float("nan")
        ),
        best_truth_gain=(max(best_truth_gains) if best_truth_gains else float("nan")),
        average_best_truth_gain=(
            float(np.mean(np.asarray(best_truth_gains, dtype=np.float64)))
            if best_truth_gains
            else float("nan")
        ),
        average_runtime_seconds=(
            float(np.mean(np.asarray(runtimes, dtype=np.float64)))
            if runtimes
            else 0.0
        ),
    )


def main() -> None:
    cases, discovery_stats = _discover_stage35_cases_with_stats()
    label = f"{_utc_label()}_{RUN_LABEL}"
    output_dir = OUTPUT_ROOT / label
    output_dir.mkdir(parents=True, exist_ok=True)

    case_summaries: list[dict[str, Any]] = []
    archive_rows: list[dict[str, Any]] = []
    for case in cases:
        result = evaluate_stage35_case(
            case,
            chunk_size=int(phasec_replay_mod.ANALYSIS_BATCH_CHUNK_SIZE),
            require_batch=bool(phasec_replay_mod.ANALYSIS_REQUIRE_BATCH_SCORING),
        )
        case_summaries.append(dict(result.get("case_summary", {})))
        archive_rows.extend(list(result.get("archive_rows", [])))

    summary = dict(
        run_label=str(RUN_LABEL),
        solver_cfg=dict(SOLVER_CFG),
        filter_period=int(FILTER_PERIOD),
        filter_columns=int(FILTER_COLUMNS),
        filter_length=int(FILTER_LENGTH),
        max_cases=(int(MAX_CASES) if MAX_CASES is not None else None),
        discovered_case_count=int(len(cases)),
        discovery_stats=dict(discovery_stats),
        aggregate=summarize_case_summaries(case_summaries),
    )
    (output_dir / "summary.json").write_text(
        json.dumps(phasec_replay_mod._jsonify(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    phasec_replay_mod._write_csv(output_dir / "case_summary.csv", case_summaries)
    phasec_replay_mod._write_csv(output_dir / "archive_rows.csv", archive_rows)
    print(
        json.dumps(
            phasec_replay_mod._jsonify(
                dict(
                    output_dir=phasec_replay_mod._repo_rel(output_dir),
                    case_count=int(len(case_summaries)),
                    archive_row_count=int(len(archive_rows)),
                    aggregate=summary["aggregate"],
                )
            ),
            sort_keys=True,
        )
    )
    refresh_catalog_safely(print_fn=print)


if __name__ == "__main__":
    main()
