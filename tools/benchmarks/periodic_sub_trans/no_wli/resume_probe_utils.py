from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[4]
NO_WLI_OUTPUT_ROOT = REPO_ROOT / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli"


def _repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line_s = str(line).strip()
        if not line_s:
            continue
        rows.append(json.loads(line_s))
    return rows


def bundle_dir_for_artifact(artifact_path: Path) -> Path:
    return artifact_path.parents[1] / "resume_handoffs" / artifact_path.stem


def bundle_manifest_path_for_artifact(artifact_path: Path) -> Path:
    return bundle_dir_for_artifact(artifact_path) / "manifest.json"


def load_bundle_manifest_for_artifact(artifact_path: Path) -> dict[str, Any]:
    manifest_path = bundle_manifest_path_for_artifact(artifact_path)
    if not manifest_path.exists():
        return {}
    return load_json(manifest_path)


def stage2_to_stage3_bundle_source(manifest: Mapping[str, Any] | None) -> str:
    stage2_to_stage3 = dict((manifest or {}).get("stage2_to_stage3", {}) or {})
    return str(stage2_to_stage3.get("source", "") or "")


def is_live_stage3_bundle_artifact(artifact_path: Path) -> bool:
    manifest = load_bundle_manifest_for_artifact(artifact_path)
    return stage2_to_stage3_bundle_source(manifest) == "live_stage3_pipeline"


def iter_seed_artifact_paths(*, key_seed: int) -> list[Path]:
    pattern = f"*/final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed{int(key_seed)}.json"
    paths = [
        path
        for path in NO_WLI_OUTPUT_ROOT.glob(pattern)
        if path.is_file()
    ]
    return sorted(
        paths,
        key=lambda path: str(path.parents[1].name),
    )


def resolve_probe_source_artifact(
    *,
    fallback_artifact_path: Path,
    key_seed: int,
    prefer_live_stage3_bundle: bool,
) -> dict[str, Any]:
    fallback_path = Path(fallback_artifact_path)
    if not fallback_path.is_absolute():
        fallback_path = (REPO_ROOT / fallback_path).resolve()
    candidates = iter_seed_artifact_paths(key_seed=int(key_seed))
    live_bundle_candidates = [
        path
        for path in candidates
        if is_live_stage3_bundle_artifact(path)
    ]
    if bool(prefer_live_stage3_bundle) and live_bundle_candidates:
        selected_path = live_bundle_candidates[-1]
        selection_reason = "latest_live_stage3_bundle"
    else:
        selected_path = fallback_path
        selection_reason = "fallback_artifact"
    selected_manifest = load_bundle_manifest_for_artifact(selected_path)
    return dict(
        artifact_path=selected_path,
        artifact_relpath=_repo_rel(selected_path),
        selection_reason=str(selection_reason),
        candidate_count=int(len(candidates)),
        live_bundle_candidate_count=int(len(live_bundle_candidates)),
        live_bundle_candidate_relpaths=[_repo_rel(path) for path in live_bundle_candidates],
        selected_bundle_source=stage2_to_stage3_bundle_source(selected_manifest),
        selected_manifest_relpath=(
            _repo_rel(bundle_manifest_path_for_artifact(selected_path))
            if bundle_manifest_path_for_artifact(selected_path).exists()
            else ""
        ),
    )


def summarize_phasec_checkpoint_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    checkpoint_rows = [dict(row) for row in rows]
    if not checkpoint_rows:
        return dict(row_count=0)
    best_truth = max(
        checkpoint_rows,
        key=lambda row: float(row.get("final_match", float("-inf"))),
    )
    best_score = max(
        checkpoint_rows,
        key=lambda row: float(row.get("final_score", float("-inf"))),
    )
    anchor_row = next(
        (row for row in checkpoint_rows if str(row.get("lane", "") or "") == "anchor"),
        None,
    )
    return dict(
        row_count=int(len(checkpoint_rows)),
        best_truth_match=float(best_truth.get("final_match", float("nan"))),
        best_truth_score=float(best_truth.get("final_score", float("nan"))),
        best_truth_lane=str(best_truth.get("lane", "") or ""),
        best_truth_source_rank=int(best_truth.get("source_rank", 0) or 0),
        best_score_match=float(best_score.get("final_match", float("nan"))),
        best_score=float(best_score.get("final_score", float("nan"))),
        best_score_lane=str(best_score.get("lane", "") or ""),
        best_score_source_rank=int(best_score.get("source_rank", 0) or 0),
        anchor_final_match=(
            float(anchor_row.get("final_match", float("nan")))
            if anchor_row is not None
            else float("nan")
        ),
        anchor_final_score=(
            float(anchor_row.get("final_score", float("nan")))
            if anchor_row is not None
            else float("nan")
        ),
        lexical_requests_total=int(
            sum(int(row.get("lexical_requests_delta", 0) or 0) for row in checkpoint_rows)
        ),
        lexical_threshold_skips_total=int(
            sum(int(row.get("lexical_threshold_skips_delta", 0) or 0) for row in checkpoint_rows)
        ),
        lexical_tiebreak_decisions_total=int(
            sum(int(row.get("lexical_tiebreak_decisions_delta", 0) or 0) for row in checkpoint_rows)
        ),
    )
