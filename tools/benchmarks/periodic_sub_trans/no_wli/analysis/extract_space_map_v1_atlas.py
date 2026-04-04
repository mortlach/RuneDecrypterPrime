from __future__ import annotations

import csv
import datetime as dt
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


FINAL_INSTANCE_GLOB = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "*/final_instances/*.json"
)
OUTPUT_BASE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas"
)
MAX_ARTIFACTS = 500

SCORE_GAIN_FALSE_FRIEND_MIN = 0.002
MATCH_DROP_FALSE_FRIEND_MAX = -0.001
PROMISING_OUTSIDER_MIN_DISTANCE = 0.10
UNDERVALUED_GOOD_MIN_DISTANCE = 0.05
GOOD_FAMILY_MIN_MATCH = 0.30
WEAK_FAMILY_MAX_MATCH = 0.20
DEAD_PATH_MAX_MATCH = 0.10
REPAIR_MIN_CONTINUED_GAIN = 0.01
SOLVED_MATCH_THRESHOLD = 0.999
STAGE35_LIVE_WIN_MIN_MATCH = 0.30
BROAD_POOL_MIN_FAMILIES = 4
BROAD_POOL_MAX_LARGEST_FAMILY_SHARE = 0.5
COMPRESSED_POOL_MIN_FAMILIES = 2
COMPRESSED_POOL_MIN_LARGEST_FAMILY_SHARE = 0.5


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_str(value: Any) -> str:
    return str(value or "")


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def classify_row_type(row: Mapping[str, Any]) -> str:
    row_d = dict(row or {})
    selected = _safe_int(row_d.get("selected", 0), 0)
    eligible = _safe_int(row_d.get("eligible", 0), 0)
    admitted = _safe_int(row_d.get("admitted_by_next_stage", 0), 0)
    score_gain = _safe_float(row_d.get("score_gain", float("nan")))
    match_gain = _safe_float(row_d.get("match_gain", float("nan")))
    final_match = _safe_float(row_d.get("final_match", float("nan")))
    continued_best_match = _safe_float(
        row_d.get("continued_best_match", float("nan"))
    )
    distance_to_anchor = _safe_float(
        row_d.get("distance_to_anchor", float("nan"))
    )

    if (
        admitted == 1
        and _is_finite(final_match)
        and _is_finite(continued_best_match)
        and continued_best_match >= final_match + REPAIR_MIN_CONTINUED_GAIN
    ):
        return "repair_candidate"
    if (
        _is_finite(score_gain)
        and _is_finite(match_gain)
        and score_gain >= SCORE_GAIN_FALSE_FRIEND_MIN
        and match_gain <= MATCH_DROP_FALSE_FRIEND_MAX
    ):
        return "false_friend"
    if (
        eligible == 1
        and selected == 0
        and _is_finite(distance_to_anchor)
        and distance_to_anchor >= PROMISING_OUTSIDER_MIN_DISTANCE
        and (not _is_finite(score_gain) or score_gain >= 0.0)
        and (not _is_finite(match_gain) or match_gain >= -0.005)
    ):
        return "promising_outsider"
    if (
        selected == 0
        and _is_finite(final_match)
        and final_match >= GOOD_FAMILY_MIN_MATCH
        and _is_finite(distance_to_anchor)
        and distance_to_anchor >= UNDERVALUED_GOOD_MIN_DISTANCE
    ):
        return "undervalued_good_family"
    if (
        selected == 0
        and admitted == 0
        and _is_finite(final_match)
        and final_match >= GOOD_FAMILY_MIN_MATCH
    ):
        return "good_family_not_exploited"
    if (
        selected == 1
        and _is_finite(final_match)
        and final_match < WEAK_FAMILY_MAX_MATCH
        and (not _is_finite(match_gain) or abs(match_gain) <= 0.01)
    ):
        return "weak_family_survivor"
    if (
        selected == 0
        and admitted == 0
        and _is_finite(final_match)
        and final_match < DEAD_PATH_MAX_MATCH
    ):
        return "dead_path"
    return "unclassified_row"


def classify_pool_type(pool_row: Mapping[str, Any]) -> str:
    row_d = dict(pool_row or {})
    pool_status = _safe_str(row_d.get("pool_status", ""))
    family_count = _safe_int(row_d.get("family_count", 0), 0)
    row_count = _safe_int(row_d.get("row_count", 0), 0)
    largest_family_share = _safe_float(
        row_d.get("largest_family_share", float("nan"))
    )

    if pool_status == "not_run":
        return "not_run_pool"
    if pool_status == "empty" or row_count <= 0:
        return "empty_pool"
    if row_count > 0 and family_count <= 1:
        return "single_hill_pool"
    if (
        family_count >= BROAD_POOL_MIN_FAMILIES
        and _is_finite(largest_family_share)
        and largest_family_share <= BROAD_POOL_MAX_LARGEST_FAMILY_SHARE
    ):
        return "broad_multi_hill_pool"
    if (
        family_count >= COMPRESSED_POOL_MIN_FAMILIES
        and _is_finite(largest_family_share)
        and largest_family_share > COMPRESSED_POOL_MIN_LARGEST_FAMILY_SHARE
    ):
        return "compressed_multi_hill_pool"
    return "unclassified_pool"


def classify_run_type(artifact: Mapping[str, Any]) -> str:
    artifact_d = dict(artifact or {})
    stage3_diag = dict(artifact_d.get("stage3_diagnostics", {}) or {})
    best_match = _safe_float(artifact_d.get("best_match_ratio", float("nan")))
    best_stage = _safe_str(artifact_d.get("best_stage", ""))
    stage35_accept_passed = _safe_int(
        stage3_diag.get("stage35_accept_passed", 0),
        0,
    )
    stage35_accept_reason = _safe_str(
        stage3_diag.get("stage35_accept_reason", "")
    )
    stage35_outcome_status = _safe_str(
        stage3_diag.get("stage35_outcome_status", "")
    )
    stage35_capped = _safe_int(stage3_diag.get("stage35_capped", 0), 0)

    if stage35_capped == 1 or (
        stage35_outcome_status and stage35_outcome_status != "completed"
    ):
        return "incomplete_or_capped"
    if _is_finite(best_match) and best_match >= SOLVED_MATCH_THRESHOLD:
        return "solved_control"
    if (
        stage35_accept_passed == 1
        and best_stage == "stage35_substitution_only"
        and _is_finite(best_match)
        and best_match >= STAGE35_LIVE_WIN_MIN_MATCH
    ):
        return "stage35_live_win"
    if stage35_accept_reason == "top_candidate_matches_baseline":
        return "stage35_noop_reject"
    if stage35_accept_reason == "search_score_drop_guard_failed":
        return "stage35_guard_reject"
    return "unclassified_run"


def detect_data_gap_flags(
    *,
    artifact: Mapping[str, Any],
    partial_row: Mapping[str, Any] | None = None,
    pool_row: Mapping[str, Any] | None = None,
) -> list[str]:
    artifact_d = dict(artifact or {})
    stage3_diag = dict(artifact_d.get("stage3_diagnostics", {}) or {})
    payload = dict(stage3_diag.get("space_map_v1", {}) or {})
    flags: set[str] = set()

    if not payload:
        return ["missing_space_map_v1"]
    if not _safe_str(payload.get("run_id", "")):
        flags.add("missing_space_map_run_id")
    if not list(payload.get("partial_state_rows", []) or []):
        flags.add("missing_partial_state_rows")
    if not list(payload.get("pool_summaries", []) or []):
        flags.add("missing_pool_summaries")
    stage35_requested = _safe_int(stage3_diag.get("stage35_requested_cfg", 0), 0)
    stage35_ran = _safe_int(stage3_diag.get("stage35_ran", 0), 0)
    stage35_has_rows = any(
        _safe_str(dict(row).get("stage_boundary", ""))
        in {"stage35_seed", "stage35_archive"}
        for row in list(payload.get("partial_state_rows", []) or [])
    )
    if (stage35_requested == 1 or stage35_ran == 1 or bool(stage35_has_rows)) and (
        not _safe_str(stage3_diag.get("stage35_progress_jsonl_name", ""))
        or not _safe_str(stage3_diag.get("stage35_partial_state_name", ""))
    ):
        flags.add("missing_stage35_progress_paths")

    if partial_row is not None:
        row_d = dict(partial_row or {})
        row_stage = _safe_str(row_d.get("stage_boundary", ""))
        row_hash = _safe_str(row_d.get("candidate_hash", ""))
        phasec_anchor_hash = _safe_str(
            stage3_diag.get("phaseC_anchor_candidate_hash", "")
        )
        baseline_hash = _safe_str(
            stage3_diag.get("stage35_baseline_candidate_hash", "")
        )
        is_root_row = (
            row_stage == "stage2_promoted"
            or (
                row_stage == "stage3_prep"
                and row_hash
                and row_hash == _safe_str(
                    next(
                        (
                            dict(pool_row).get("anchor_candidate_hash", "")
                            for pool_row in list(
                                payload.get("pool_summaries", []) or []
                            )
                            if _safe_str(
                                dict(pool_row).get("stage_boundary", "")
                            )
                            == "stage3_prep"
                        ),
                        "",
                    )
                )
            )
            or
            (
                row_stage in {"phaseC_pool", "phaseC_start"}
                and row_hash
                and row_hash == phasec_anchor_hash
            )
            or (
                row_stage == "stage35_seed"
                and row_hash
                and row_hash == baseline_hash
            )
            or (
                row_stage == "stage35_archive"
                and row_hash
                and row_hash == baseline_hash
            )
        )
        if not is_root_row and not _safe_str(
            row_d.get("parent_candidate_hash", "")
        ):
            flags.add("missing_parent_candidate_hash")
        if not _safe_str(row_d.get("family_id", "")):
            flags.add("missing_family_id")
        if not _is_finite(row_d.get("distance_to_anchor", float("nan"))):
            flags.add("missing_distance_to_anchor")
        if (
            _safe_int(row_d.get("admitted_by_next_stage", 0), 0) == 1
            and not _safe_str(row_d.get("continued_best_candidate_hash", ""))
        ):
            flags.add("missing_continued_best_links")

    if pool_row is not None:
        row_d = dict(pool_row or {})
        payload_pool_stages = {
            _safe_str(dict(summary_row).get("stage_boundary", ""))
            for summary_row in list(payload.get("pool_summaries", []) or [])
        }
        if (
            (
                _safe_str(row_d.get("stage_boundary", "")) == "phaseC_pool"
                or (
                    _safe_str(row_d.get("stage_boundary", "")) == "phaseC_start"
                    and "phaseC_pool" not in payload_pool_stages
                )
            )
            and _safe_str(row_d.get("pool_status", "")) == "available"
        ):
            expected_rows = _safe_int(
                stage3_diag.get("phaseC_candidate_pool_count", 0),
                0,
            )
            actual_rows = _safe_int(row_d.get("row_count", 0), 0)
            if expected_rows > 0 and actual_rows < expected_rows:
                flags.add("phasec_pool_not_row_complete")
    return sorted(flags)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["artifact_path"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _iter_artifact_paths() -> list[Path]:
    return sorted(Path().glob(str(FINAL_INSTANCE_GLOB)))[-int(MAX_ARTIFACTS) :]


def _build_row_atlas_row(
    *,
    artifact_path: str,
    run_id: str,
    period: int,
    columns: int,
    key_seed: int,
    run_label: str,
    artifact: Mapping[str, Any],
    row: Mapping[str, Any],
) -> dict[str, Any]:
    row_d = dict(row or {})
    return dict(
        artifact_path=artifact_path,
        run_id=run_id,
        period=period,
        columns=columns,
        key_seed=key_seed,
        run_label=run_label,
        stage_boundary=_safe_str(row_d.get("stage_boundary", "")),
        candidate_hash=_safe_str(row_d.get("candidate_hash", "")),
        parent_candidate_hash=_safe_str(row_d.get("parent_candidate_hash", "")),
        parent_link_kind=_safe_str(row_d.get("parent_link_kind", "")),
        family_id=_safe_str(row_d.get("family_id", "")),
        family_id_kind=_safe_str(row_d.get("family_id_kind", "")),
        row_type=classify_row_type(row_d),
        source=_safe_str(row_d.get("source", "")),
        lane=_safe_str(row_d.get("lane", "")),
        selected=_safe_int(row_d.get("selected", 0), 0),
        eligible=_safe_int(row_d.get("eligible", 0), 0),
        admitted_by_next_stage=_safe_int(
            row_d.get("admitted_by_next_stage", 0),
            0,
        ),
        final_match=_safe_float(row_d.get("final_match", float("nan"))),
        match_gain=_safe_float(row_d.get("match_gain", float("nan"))),
        final_score=_safe_float(row_d.get("final_score", float("nan"))),
        score_gain=_safe_float(row_d.get("score_gain", float("nan"))),
        distance_to_anchor=_safe_float(
            row_d.get("distance_to_anchor", float("nan"))
        ),
        continued_best_candidate_hash=_safe_str(
            row_d.get("continued_best_candidate_hash", "")
        ),
        continued_best_match=_safe_float(
            row_d.get("continued_best_match", float("nan"))
        ),
        reject_reason=_safe_str(row_d.get("reject_reason", "")),
        data_gap_flags=";".join(
            detect_data_gap_flags(artifact=artifact, partial_row=row_d)
        ),
    )


def _build_pool_atlas_row(
    *,
    artifact_path: str,
    run_id: str,
    period: int,
    columns: int,
    key_seed: int,
    run_label: str,
    artifact: Mapping[str, Any],
    row: Mapping[str, Any],
) -> dict[str, Any]:
    row_d = dict(row or {})
    return dict(
        artifact_path=artifact_path,
        run_id=run_id,
        period=period,
        columns=columns,
        key_seed=key_seed,
        run_label=run_label,
        stage_boundary=_safe_str(row_d.get("stage_boundary", "")),
        pool_id=_safe_str(row_d.get("pool_id", "")),
        pool_status=_safe_str(row_d.get("pool_status", "")),
        pool_type=classify_pool_type(row_d),
        selection_policy=_safe_str(row_d.get("selection_policy", "")),
        row_count=_safe_int(row_d.get("row_count", 0), 0),
        eligible_row_count=_safe_int(row_d.get("eligible_row_count", 0), 0),
        selected_row_count=_safe_int(row_d.get("selected_row_count", 0), 0),
        family_count=_safe_int(row_d.get("family_count", 0), 0),
        largest_family_share=_safe_float(
            row_d.get("largest_family_share", float("nan"))
        ),
        unique_candidate_hash_count=_safe_int(
            row_d.get("unique_candidate_hash_count", 0),
            0,
        ),
        anchor_candidate_hash=_safe_str(row_d.get("anchor_candidate_hash", "")),
        selected_pairwise_distance_mean=_safe_float(
            row_d.get("selected_pairwise_distance_mean", float("nan"))
        ),
        next_stage_started_count=_safe_int(
            row_d.get("next_stage_started_count", 0),
            0,
        ),
        next_stage_admitted_count=_safe_int(
            row_d.get("next_stage_admitted_count", 0),
            0,
        ),
        next_stage_rejected_count=_safe_int(
            row_d.get("next_stage_rejected_count", 0),
            0,
        ),
        data_gap_flags=";".join(
            detect_data_gap_flags(artifact=artifact, pool_row=row_d)
        ),
    )


def extract_rows_for_artifact(
    artifact_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    artifact = _read_json(Path(artifact_path))
    stage3_diag = dict(artifact.get("stage3_diagnostics", {}) or {})
    payload = dict(stage3_diag.get("space_map_v1", {}) or {})
    partial_rows = [
        dict(row)
        for row in list(payload.get("partial_state_rows", []) or [])
        if isinstance(row, Mapping)
    ]
    pool_rows = [
        dict(row)
        for row in list(payload.get("pool_summaries", []) or [])
        if isinstance(row, Mapping)
    ]
    artifact_rel = str(Path(artifact_path)).replace("\\", "/")
    period = _safe_int(artifact.get("period", 0), 0)
    columns = _safe_int(artifact.get("columns", 0), 0)
    key_seed = _safe_int(artifact.get("key_seed", 0), 0)
    run_id = _safe_str(payload.get("run_id", ""))
    run_label = classify_run_type(artifact)

    row_atlas = [
        _build_row_atlas_row(
            artifact_path=artifact_rel,
            run_id=run_id,
            period=period,
            columns=columns,
            key_seed=key_seed,
            run_label=run_label,
            artifact=artifact,
            row=row,
        )
        for row in partial_rows
    ]
    pool_atlas = [
        _build_pool_atlas_row(
            artifact_path=artifact_rel,
            run_id=run_id,
            period=period,
            columns=columns,
            key_seed=key_seed,
            run_label=run_label,
            artifact=artifact,
            row=row,
        )
        for row in pool_rows
    ]

    row_lookup = {
        (
            _safe_str(row.get("stage_boundary", "")),
            _safe_str(row.get("candidate_hash", "")),
        ): dict(row)
        for row in partial_rows
    }
    transition_atlas: list[dict[str, Any]] = []
    for row in partial_rows:
        row_d = dict(row or {})
        candidate_hash = _safe_str(row_d.get("candidate_hash", ""))
        stage_boundary = _safe_str(row_d.get("stage_boundary", ""))
        parent_hash = _safe_str(row_d.get("parent_candidate_hash", ""))
        continued_hash = _safe_str(row_d.get("continued_best_candidate_hash", ""))
        if parent_hash:
            transition_atlas.append(
                dict(
                    artifact_path=artifact_rel,
                    run_id=run_id,
                    period=period,
                    columns=columns,
                    key_seed=key_seed,
                    transition_type="parent_to_candidate",
                    from_stage_boundary=stage_boundary,
                    to_stage_boundary=stage_boundary,
                    from_candidate_hash=parent_hash,
                    to_candidate_hash=candidate_hash,
                    to_row_type=classify_row_type(row_d),
                    to_family_id=_safe_str(row_d.get("family_id", "")),
                    to_final_match=_safe_float(
                        row_d.get("final_match", float("nan"))
                    ),
                    to_distance_to_anchor=_safe_float(
                        row_d.get("distance_to_anchor", float("nan"))
                    ),
                )
            )
        if continued_hash:
            continued_row = row_lookup.get(("stage35_archive", continued_hash), {})
            transition_atlas.append(
                dict(
                    artifact_path=artifact_rel,
                    run_id=run_id,
                    period=period,
                    columns=columns,
                    key_seed=key_seed,
                    transition_type="candidate_to_continued_best",
                    from_stage_boundary=stage_boundary,
                    to_stage_boundary="stage35_archive",
                    from_candidate_hash=candidate_hash,
                    to_candidate_hash=continued_hash,
                    to_row_type=classify_row_type(continued_row)
                    if continued_row
                    else "missing_continued_row",
                    to_family_id=_safe_str(continued_row.get("family_id", "")),
                    to_final_match=_safe_float(
                        continued_row.get("final_match", float("nan"))
                    ),
                    to_distance_to_anchor=_safe_float(
                        continued_row.get("distance_to_anchor", float("nan"))
                    ),
                )
            )

    run_row = dict(
        artifact_path=artifact_rel,
        run_id=run_id,
        period=period,
        columns=columns,
        key_seed=key_seed,
        best_stage=_safe_str(artifact.get("best_stage", "")),
        best_match_ratio=_safe_float(
            artifact.get("best_match_ratio", float("nan"))
        ),
        stage35_baseline_selector=_safe_str(
            stage3_diag.get("stage35_baseline_selector", "")
        ),
        stage35_baseline_candidate_hash=_safe_str(
            stage3_diag.get("stage35_baseline_candidate_hash", "")
        ),
        stage35_accept_passed=_safe_int(
            stage3_diag.get("stage35_accept_passed", 0),
            0,
        ),
        stage35_accept_reason=_safe_str(
            stage3_diag.get("stage35_accept_reason", "")
        ),
        stage35_best_match=_safe_float(
            stage3_diag.get("stage35_best_match", float("nan"))
        ),
        stage35_outcome_status=_safe_str(
            stage3_diag.get("stage35_outcome_status", "")
        ),
        stage35_runtime_seconds=_safe_float(
            stage3_diag.get("stage35_runtime_seconds", float("nan"))
        ),
        run_label=run_label,
        data_gap_flags=";".join(detect_data_gap_flags(artifact=artifact)),
    )
    return row_atlas, pool_atlas, transition_atlas, run_row


def _summarize_rows(
    row_atlas: Iterable[Mapping[str, Any]],
    pool_atlas: Iterable[Mapping[str, Any]],
    run_atlas: Iterable[Mapping[str, Any]],
    transition_atlas: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    row_rows = [dict(row) for row in row_atlas]
    pool_rows = [dict(row) for row in pool_atlas]
    run_rows = [dict(row) for row in run_atlas]
    transition_rows = [dict(row) for row in transition_atlas]
    row_labels = Counter(_safe_str(row.get("row_type", "")) for row in row_rows)
    pool_labels = Counter(_safe_str(row.get("pool_type", "")) for row in pool_rows)
    run_labels = Counter(_safe_str(row.get("run_label", "")) for row in run_rows)
    transition_labels = Counter(
        _safe_str(row.get("transition_type", "")) for row in transition_rows
    )
    gap_counts: Counter[str] = Counter()
    for row in row_rows + pool_rows + run_rows:
        for flag in _safe_str(row.get("data_gap_flags", "")).split(";"):
            if flag:
                gap_counts[flag] += 1
    return dict(
        row_type_counts=dict(sorted(row_labels.items())),
        pool_type_counts=dict(sorted(pool_labels.items())),
        run_type_counts=dict(sorted(run_labels.items())),
        transition_type_counts=dict(sorted(transition_labels.items())),
        data_gap_flag_counts=dict(sorted(gap_counts.items())),
    )


def main() -> None:
    artifact_paths = _iter_artifact_paths()
    row_atlas: list[dict[str, Any]] = []
    pool_atlas: list[dict[str, Any]] = []
    transition_atlas: list[dict[str, Any]] = []
    run_atlas: list[dict[str, Any]] = []
    for artifact_path in artifact_paths:
        row_rows, pool_rows, transition_rows, run_row = extract_rows_for_artifact(
            Path(artifact_path)
        )
        row_atlas.extend(row_rows)
        pool_atlas.extend(pool_rows)
        transition_atlas.extend(transition_rows)
        run_atlas.append(run_row)

    output_dir = OUTPUT_BASE_DIR / (
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        "__space_map_v1_atlas"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "row_atlas.csv", row_atlas)
    _write_csv(output_dir / "pool_atlas.csv", pool_atlas)
    _write_csv(output_dir / "transition_atlas.csv", transition_atlas)
    _write_csv(output_dir / "run_atlas.csv", run_atlas)

    summary = dict(
        artifact_glob=str(FINAL_INSTANCE_GLOB),
        artifacts_scanned=int(len(artifact_paths)),
        row_atlas_rows=int(len(row_atlas)),
        pool_atlas_rows=int(len(pool_atlas)),
        transition_atlas_rows=int(len(transition_atlas)),
        run_atlas_rows=int(len(run_atlas)),
        output_dir=str(output_dir).replace("\\", "/"),
    )
    summary.update(
        _summarize_rows(
            row_atlas=row_atlas,
            pool_atlas=pool_atlas,
            run_atlas=run_atlas,
            transition_atlas=transition_atlas,
        )
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "[space_map_v1_atlas] "
        f"artifacts={summary['artifacts_scanned']} "
        f"rows={summary['row_atlas_rows']} "
        f"pools={summary['pool_atlas_rows']} "
        f"transitions={summary['transition_atlas_rows']} "
        f"runs={summary['run_atlas_rows']} "
        f"output_dir={summary['output_dir']}"
    )


if __name__ == "__main__":
    main()
