from __future__ import annotations

import cProfile
import csv
import io
import json
import pstats
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (
    refresh_catalog_safely,
)
from tools.benchmarks.periodic_sub_trans.no_wli import (
    late_stage_selector_stageb_continuation as continuation_mod,
)


RUN_LABEL = "profile_stage35_replay_hotspots_v1"
OUTPUT_ROOT = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "stage35_replay_profile"
)
PREFERRED_SELECTED_ROWS_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json"
)
SELECTED_ROWS_GLOBS: tuple[str, ...] = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "analysis/late_stage_selector_stageb_v*/selected_trial_material_rows.json",
)
ACTIVE_FIXTURE_LABELS: tuple[str, ...] = ("control", "candidate")
ACTIVE_SELECTORS: tuple[str, ...] = ("legacy", "score_plus_novelty")
BATCH_EVAL_CHUNK_SIZE_CANDIDATES: tuple[int, ...] = (256, 512, 1024)
PROFILE_FOCUS_FIXTURE_LABEL = "candidate"
PROFILE_FOCUS_SELECTOR = "score_plus_novelty"
PROFILE_FOCUS_BATCH_EVAL_CHUNK_SIZE = 1024
PROFILE_TOP_N = 60
STAGE35_CFG_OVERRIDE = dict(
    seed_keep=2,
    beam_width=1,
    archive_keep=12,
    rounds=1,
    mini_search_steps=1,
    mini_search_beam_width=2,
    mini_search_top_symbols=10,
    mini_search_final_keep=2,
    mini_search_keep_all_rows=0,
    max_runtime_seconds=30.0,
    partial_dump_preview_rows=3,
)


@dataclass(frozen=True)
class Stage35ProfileCase:
    fixture_label: str
    selector: str
    artifact_relpath: str
    candidate_hash: str
    source: str
    lane: str
    selected_row: dict[str, Any]

    @property
    def case_id(self) -> str:
        return f"{self.fixture_label}__{self.selector}"


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, Path):
        try:
            return str(value.relative_to(REPO_ROOT))
        except Exception:
            return str(value)
    return value


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return float(out)


def discover_selected_rows_path() -> Path:
    preferred = REPO_ROOT / PREFERRED_SELECTED_ROWS_PATH
    if preferred.exists():
        return preferred
    candidates: list[Path] = []
    for pattern in SELECTED_ROWS_GLOBS:
        candidates.extend(REPO_ROOT.glob(pattern))
    existing = [path for path in candidates if path.exists()]
    if not existing:
        raise FileNotFoundError(
            "No late-stage selector Stage B selected-trial rows file was found"
        )
    existing.sort(key=lambda path: (path.stat().st_mtime, str(path)))
    return existing[-1]


def build_profile_cases(
    rows: Sequence[Mapping[str, Any]],
    *,
    fixture_labels: Sequence[str] = ACTIVE_FIXTURE_LABELS,
    selectors: Sequence[str] = ACTIVE_SELECTORS,
) -> list[Stage35ProfileCase]:
    allowed_fixtures = {str(label) for label in fixture_labels}
    allowed_selectors = {str(selector) for selector in selectors}
    deduped: dict[tuple[str, str], Stage35ProfileCase] = {}
    for row_obj in list(rows or []):
        row = dict(row_obj or {})
        fixture_label = str(row.get("fixture_label", "") or "")
        selector = str(row.get("selector", "") or "")
        if fixture_label not in allowed_fixtures:
            continue
        if selector not in allowed_selectors:
            continue
        if int(row.get("replay_material_complete", 0) or 0) != 1:
            continue
        artifact_relpath = str(row.get("source_artifact_path", "") or "")
        candidate_hash = str(row.get("candidate_hash", "") or "")
        if not artifact_relpath or not candidate_hash:
            continue
        deduped[(fixture_label, selector)] = Stage35ProfileCase(
            fixture_label=fixture_label,
            selector=selector,
            artifact_relpath=artifact_relpath,
            candidate_hash=candidate_hash,
            source=str(row.get("source", "") or ""),
            lane=str(row.get("lane", "") or ""),
            selected_row=row,
        )
    return [
        deduped[key]
        for key in sorted(deduped.keys(), key=lambda item: (item[0], item[1]))
    ]


def run_profile_case(
    profile_case: Stage35ProfileCase,
    *,
    stage35_cfg_override: Mapping[str, Any] | None = None,
    batch_eval_chunk_size: int | None = None,
    load_case_fn: Callable[..., Any] | None = None,
    runner_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    load_case = load_case_fn or resume_mod.load_artifact_case
    run_case = runner_fn or resume_mod.run_stage35_from_selected_trial_row
    artifact_case = load_case(artifact_path=Path(profile_case.artifact_relpath))
    t0 = time.perf_counter()
    payload = dict(
        run_case(
            artifact_case,
            selected_row=dict(profile_case.selected_row),
            stage35_cfg_override=dict(stage35_cfg_override or {}),
            batch_eval_chunk_size=(
                int(batch_eval_chunk_size)
                if batch_eval_chunk_size is not None
                else None
            ),
        )
    )
    wallclock_seconds = float(time.perf_counter() - t0)
    stage35 = dict(payload.get("stage35", {}) or {})
    telemetry = dict(stage35.get("telemetry", {}) or {})
    return dict(
        case_config_id=(
            f"{profile_case.case_id}__chunk"
            f"{int(batch_eval_chunk_size) if batch_eval_chunk_size is not None else int(resume_mod.DEFAULT_BATCH_EVAL_CHUNK_SIZE)}"
        ),
        case_id=profile_case.case_id,
        fixture_label=str(profile_case.fixture_label),
        selector=str(profile_case.selector),
        artifact_relpath=str(profile_case.artifact_relpath),
        candidate_hash=str(profile_case.candidate_hash),
        selected_source=str(profile_case.source),
        selected_lane=str(profile_case.lane),
        batch_eval_chunk_size=(
            int(batch_eval_chunk_size)
            if batch_eval_chunk_size is not None
            else int(resume_mod.DEFAULT_BATCH_EVAL_CHUNK_SIZE)
        ),
        selected_truth_match=_safe_float(
            payload.get("selected_candidate_final_match")
        ),
        selected_final_score=_safe_float(
            payload.get("selected_candidate_final_score")
        ),
        resume_best_truth_match=_safe_float(payload.get("resume_best_match_ratio")),
        resume_best_score=_safe_float(payload.get("resume_best_score")),
        truth_gain_vs_selected=_safe_float(
            stage35.get("truth_gain_vs_selected_row")
        ),
        accept_passed=int(stage35.get("accept_passed", 0) or 0),
        accept_reason=str(stage35.get("accept_reason", "") or ""),
        archive_count=int(stage35.get("archive_count", 0) or 0),
        seed_count=int(stage35.get("seed_count", 0) or 0),
        rounds_completed=int(stage35.get("rounds_completed", 0) or 0),
        evals=int(stage35.get("evals", 0) or 0),
        solver_runtime_seconds=float(stage35.get("runtime_seconds", 0.0) or 0.0),
        wallclock_seconds=float(wallclock_seconds),
        telemetry_row_scoring_seconds=_safe_float(
            telemetry.get("row_scoring_seconds", 0.0)
        ),
        telemetry_batch_score_seconds=_safe_float(
            telemetry.get("batch_score_seconds", 0.0)
        ),
        telemetry_mini_search_total_seconds=_safe_float(
            telemetry.get("mini_search_total_seconds", 0.0)
        ),
        telemetry_mini_search_count=int(
            telemetry.get("mini_search_count", 0) or 0
        ),
        telemetry_mini_search_proposals_generated=int(
            telemetry.get("mini_search_proposals_generated", 0) or 0
        ),
        telemetry_mini_search_duplicate_proposals_skipped=int(
            telemetry.get("mini_search_duplicate_proposals_skipped", 0) or 0
        ),
        telemetry_mini_search_rows_scored=int(
            telemetry.get("mini_search_rows_scored", 0) or 0
        ),
        telemetry_mini_search_rows_kept=int(
            telemetry.get("mini_search_rows_kept", 0) or 0
        ),
        telemetry_archive_update_seconds=_safe_float(
            telemetry.get("archive_update_seconds", 0.0)
        ),
        telemetry_archive_rank_seconds=_safe_float(
            telemetry.get("archive_rank_seconds", 0.0)
        ),
        telemetry_beam_rank_seconds=_safe_float(
            telemetry.get("beam_rank_seconds", 0.0)
        ),
        telemetry_average_batch_size=_safe_float(
            telemetry.get("average_batch_size", 0.0)
        ),
        telemetry_average_proposals_generated_per_mini=_safe_float(
            telemetry.get("average_proposals_generated_per_mini", 0.0)
        ),
        telemetry_average_rows_scored_per_mini=_safe_float(
            telemetry.get("average_rows_scored_per_mini", 0.0)
        ),
        telemetry_average_rows_kept_per_mini=_safe_float(
            telemetry.get("average_rows_kept_per_mini", 0.0)
        ),
        telemetry_row_scoring_input_keys_total=int(
            telemetry.get("row_scoring_input_keys_total", 0) or 0
        ),
        telemetry_row_scoring_normalized_unique_keys_total=int(
            telemetry.get("row_scoring_normalized_unique_keys_total", 0) or 0
        ),
        telemetry_row_scoring_normalized_duplicate_keys_total=int(
            telemetry.get("row_scoring_normalized_duplicate_keys_total", 0) or 0
        ),
        best_candidate_hash=str(stage35.get("best_candidate_hash", "") or ""),
        best_seed_source=str(stage35.get("best_seed_source", "") or ""),
        best_stage3_source=str(stage35.get("best_stage3_source", "") or ""),
        best_lane=str(stage35.get("best_lane", "") or ""),
        best_source_rank=int(stage35.get("best_source_rank", 0) or 0),
        stage35_cfg_override=dict(stage35_cfg_override or {}),
        payload=payload,
    )


def summarize_profile_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row_list = [dict(row) for row in list(rows or [])]
    if not row_list:
        return dict(
            case_count=0,
            accepted_case_count=0,
            slowest_case_id="",
            slowest_wallclock_seconds=0.0,
            fastest_case_id="",
            fastest_wallclock_seconds=0.0,
        )
    sorted_rows = sorted(
        row_list,
        key=lambda row: float(row.get("wallclock_seconds", 0.0) or 0.0),
    )
    return dict(
        case_count=int(len(row_list)),
        accepted_case_count=int(
            sum(int(row.get("accept_passed", 0) or 0) for row in row_list)
        ),
        slowest_case_id=str(
            sorted_rows[-1].get("case_config_id", "")
            or sorted_rows[-1].get("case_id", "")
            or ""
        ),
        slowest_wallclock_seconds=float(
            sorted_rows[-1].get("wallclock_seconds", 0.0) or 0.0
        ),
        fastest_case_id=str(
            sorted_rows[0].get("case_config_id", "")
            or sorted_rows[0].get("case_id", "")
            or ""
        ),
        fastest_wallclock_seconds=float(
            sorted_rows[0].get("wallclock_seconds", 0.0) or 0.0
        ),
    )


def write_profile_report(
    *,
    profile_case: Stage35ProfileCase,
    output_dir: Path,
    stage35_cfg_override: Mapping[str, Any],
    batch_eval_chunk_size: int,
    load_case_fn: Callable[..., Any] | None = None,
    runner_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    load_case = load_case_fn or resume_mod.load_artifact_case
    run_case = runner_fn or resume_mod.run_stage35_from_selected_trial_row
    artifact_case = load_case(artifact_path=Path(profile_case.artifact_relpath))
    profiler = cProfile.Profile()
    profiler.enable()
    t0 = time.perf_counter()
    payload = dict(
        run_case(
            artifact_case,
            selected_row=dict(profile_case.selected_row),
            stage35_cfg_override=dict(stage35_cfg_override),
            batch_eval_chunk_size=int(batch_eval_chunk_size),
        )
    )
    elapsed = float(time.perf_counter() - t0)
    profiler.disable()

    profile_dir = output_dir / "profiles" / profile_case.case_id
    profile_dir.mkdir(parents=True, exist_ok=True)
    prof_path = profile_dir / "cprofile.prof"
    txt_path = profile_dir / "cprofile_top_cumulative.txt"
    profiler.dump_stats(str(prof_path))
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(PROFILE_TOP_N)
    txt_path.write_text(stream.getvalue(), encoding="utf-8")

    stage35 = dict(payload.get("stage35", {}) or {})
    return dict(
        case_id=profile_case.case_id,
        fixture_label=profile_case.fixture_label,
        selector=profile_case.selector,
        batch_eval_chunk_size=int(batch_eval_chunk_size),
        wallclock_seconds=float(elapsed),
        solver_runtime_seconds=float(stage35.get("runtime_seconds", 0.0) or 0.0),
        evals=int(stage35.get("evals", 0) or 0),
        accept_reason=str(stage35.get("accept_reason", "") or ""),
        profile_relpath=str(prof_path.relative_to(REPO_ROOT)),
        profile_text_relpath=str(txt_path.relative_to(REPO_ROOT)),
    )


def main() -> None:
    selected_rows_path = discover_selected_rows_path()
    selected_rows = continuation_mod.load_selected_trial_material_rows(selected_rows_path)
    profile_cases = build_profile_cases(selected_rows)
    run_dir = OUTPUT_ROOT / f"{_utc_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    case_rows: list[dict[str, Any]] = []
    for profile_case in profile_cases:
        for batch_eval_chunk_size in BATCH_EVAL_CHUNK_SIZE_CANDIDATES:
            print(
                "[stage35_replay_profile] "
                f"case_start fixture={profile_case.fixture_label} "
                f"selector={profile_case.selector} "
                f"candidate_hash={profile_case.candidate_hash} "
                f"batch_eval_chunk_size={int(batch_eval_chunk_size)}",
                flush=True,
            )
            row = run_profile_case(
                profile_case,
                stage35_cfg_override=STAGE35_CFG_OVERRIDE,
                batch_eval_chunk_size=int(batch_eval_chunk_size),
            )
            case_rows.append(dict(row))
            print(
                "[stage35_replay_profile] "
                f"case_done fixture={profile_case.fixture_label} "
                f"selector={profile_case.selector} "
                f"batch_eval_chunk_size={int(batch_eval_chunk_size)} "
                f"wallclock_seconds={float(row['wallclock_seconds']):.3f} "
                f"evals={int(row['evals'])} "
                f"accept_reason={str(row['accept_reason'])}",
                flush=True,
            )

    focus_case = next(
        profile_case
        for profile_case in profile_cases
        if profile_case.fixture_label == PROFILE_FOCUS_FIXTURE_LABEL
        and profile_case.selector == PROFILE_FOCUS_SELECTOR
    )
    profile_summary = write_profile_report(
        profile_case=focus_case,
        output_dir=run_dir,
        stage35_cfg_override=STAGE35_CFG_OVERRIDE,
        batch_eval_chunk_size=int(PROFILE_FOCUS_BATCH_EVAL_CHUNK_SIZE),
    )

    csv_rows = []
    payload_rows = []
    for row in case_rows:
        row_copy = dict(row)
        payload_rows.append(dict(row_copy.pop("payload", {}) or {}))
        row_copy["stage35_cfg_override"] = json.dumps(
            _jsonify(row_copy.get("stage35_cfg_override", {})),
            sort_keys=True,
        )
        csv_rows.append(row_copy)

    _write_csv(run_dir / "case_timings.csv", csv_rows)
    (run_dir / "case_payloads.json").write_text(
        json.dumps(_jsonify(payload_rows), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (run_dir / "profile_cases.json").write_text(
        json.dumps(
            _jsonify([dict(profile_case.selected_row) for profile_case in profile_cases]),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    summary = dict(
        run_label=RUN_LABEL,
        selected_rows_relpath=str(selected_rows_path.relative_to(REPO_ROOT)),
        stage35_cfg_override=dict(STAGE35_CFG_OVERRIDE),
        batch_eval_chunk_size_candidates=list(
            map(int, BATCH_EVAL_CHUNK_SIZE_CANDIDATES)
        ),
        case_count=int(len(case_rows)),
        aggregate=summarize_profile_rows(case_rows),
        focus_profile=dict(profile_summary),
    )
    (run_dir / "summary.json").write_text(
        json.dumps(_jsonify(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(
        "[stage35_replay_profile] "
        f"run_dir={str(run_dir.relative_to(REPO_ROOT))}",
        flush=True,
    )
    print(
        "[stage35_replay_profile] "
        f"selected_rows={str(selected_rows_path.relative_to(REPO_ROOT))}",
        flush=True,
    )
    print(
        "[stage35_replay_profile] "
        f"slowest_case={summary['aggregate']['slowest_case_id']} "
        f"slowest_wallclock_seconds={float(summary['aggregate']['slowest_wallclock_seconds']):.3f}",
        flush=True,
    )
    refresh_catalog_safely(print_fn=print)


if __name__ == "__main__":
    main()
