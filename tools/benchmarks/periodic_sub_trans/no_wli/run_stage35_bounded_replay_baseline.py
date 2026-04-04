from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod
from tools.benchmarks.periodic_sub_trans.no_wli import (
    late_stage_selector_stageb_continuation as continuation_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    profile_stage35_replay_hotspots as profile_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (
    refresh_catalog_safely,
)


RUN_LABEL = "stage35_bounded_replay_baseline_v1"
OUTPUT_ROOT = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "stage35_replay_bounded_baseline"
)
ACTIVE_FIXTURE_LABELS: tuple[str, ...] = ("control", "candidate")
ACTIVE_SELECTORS: tuple[str, ...] = ("legacy", "score_plus_novelty")
BATCH_EVAL_CHUNK_SIZE = 1024
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


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_case_summary_row(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(payload or {})
    stage35 = dict(row.get("stage35", {}) or {})
    return dict(
        case_id=f"{str(row.get('fixture_label', '') or '')}__{str(row.get('selector', '') or '')}",
        fixture_label=str(row.get("fixture_label", "") or ""),
        selector=str(row.get("selector", "") or ""),
        artifact_relpath=str(row.get("artifact_relpath", "") or ""),
        selected_candidate_hash=str(row.get("selected_candidate_hash", "") or ""),
        selected_candidate_source=str(row.get("selected_candidate_source", "") or ""),
        selected_candidate_lane=str(row.get("selected_candidate_lane", "") or ""),
        selected_candidate_final_score=_safe_float(
            row.get("selected_candidate_final_score")
        ),
        selected_candidate_final_match=_safe_float(
            row.get("selected_candidate_final_match")
        ),
        replay_material_complete=int(row.get("replay_material_complete", 0) or 0),
        accept_passed=int(stage35.get("accept_passed", 0) or 0),
        accept_reason=str(stage35.get("accept_reason", "") or ""),
        outcome_status=str(stage35.get("outcome_status", "") or ""),
        outcome_reason=str(stage35.get("outcome_reason", "") or ""),
        completed=int(stage35.get("completed", 0) or 0),
        capped=int(stage35.get("capped", 0) or 0),
        runtime_seconds=_safe_float(stage35.get("runtime_seconds", 0.0)),
        evals=int(stage35.get("evals", 0) or 0),
        rounds_completed=int(stage35.get("rounds_completed", 0) or 0),
        archive_count=int(stage35.get("archive_count", 0) or 0),
        seed_count=int(stage35.get("seed_count", 0) or 0),
        resume_best_match_ratio=_safe_float(row.get("resume_best_match_ratio")),
        resume_best_score=_safe_float(row.get("resume_best_score")),
        truth_gain_vs_selected_row=_safe_float(
            stage35.get("truth_gain_vs_selected_row")
        ),
        truth_gain_vs_phasec_score_winner=_safe_float(
            stage35.get("truth_gain_vs_phasec_score_winner")
        ),
        progress_events_written=int(stage35.get("progress_events_written", 0) or 0),
        partial_dump_write_count=int(
            stage35.get("partial_dump_write_count", 0) or 0
        ),
        stage35_partial_state_relpath=str(
            row.get("stage35_partial_state_relpath", "") or ""
        ),
        stage35_progress_jsonl_relpath=str(
            row.get("stage35_progress_jsonl_relpath", "") or ""
        ),
    )


def build_fixture_split_rows(
    case_summary_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row_obj in list(case_summary_rows or []):
        row = dict(row_obj or {})
        fixture_label = str(row.get("fixture_label", "") or "")
        selector = str(row.get("selector", "") or "")
        if not fixture_label or not selector:
            continue
        grouped.setdefault(fixture_label, {})[selector] = row
    out: list[dict[str, Any]] = []
    for fixture_label in sorted(grouped.keys()):
        legacy_row = dict(grouped[fixture_label].get("legacy", {}) or {})
        candidate_row = dict(
            grouped[fixture_label].get("score_plus_novelty", {}) or {}
        )
        out.append(
            dict(
                fixture_label=str(fixture_label),
                legacy_accept_passed=int(legacy_row.get("accept_passed", 0) or 0),
                legacy_accept_reason=str(legacy_row.get("accept_reason", "") or ""),
                legacy_completed=int(legacy_row.get("completed", 0) or 0),
                legacy_capped=int(legacy_row.get("capped", 0) or 0),
                candidate_accept_passed=int(
                    candidate_row.get("accept_passed", 0) or 0
                ),
                candidate_accept_reason=str(
                    candidate_row.get("accept_reason", "") or ""
                ),
                candidate_completed=int(candidate_row.get("completed", 0) or 0),
                candidate_capped=int(candidate_row.get("capped", 0) or 0),
                acceptance_split_preserved=int(
                    1
                    if int(legacy_row.get("accept_passed", 0) or 0) == 0
                    and int(candidate_row.get("accept_passed", 0) or 0) == 1
                    else 0
                ),
            )
        )
    return out


def main() -> None:
    selected_rows_path = profile_mod.discover_selected_rows_path()
    selected_rows = continuation_mod.load_selected_trial_material_rows(selected_rows_path)
    profile_cases = profile_mod.build_profile_cases(
        selected_rows,
        fixture_labels=ACTIVE_FIXTURE_LABELS,
        selectors=ACTIVE_SELECTORS,
    )
    run_dir = OUTPUT_ROOT / f"{_utc_label()}__{RUN_LABEL}"
    run_dir.mkdir(parents=True, exist_ok=True)

    payload_rows: list[dict[str, Any]] = []
    case_summary_rows: list[dict[str, Any]] = []
    for profile_case in profile_cases:
        print(
            "[stage35_bounded_replay] "
            f"case_start fixture={profile_case.fixture_label} "
            f"selector={profile_case.selector} "
            f"candidate_hash={profile_case.candidate_hash} "
            f"batch_eval_chunk_size={int(BATCH_EVAL_CHUNK_SIZE)}",
            flush=True,
        )
        artifact_case = resume_mod.load_artifact_case(
            artifact_path=Path(profile_case.artifact_relpath)
        )
        case_output_dir = run_dir / "cases" / str(profile_case.case_id)
        payload = dict(
            resume_mod.run_stage35_from_selected_trial_row(
                artifact_case,
                selected_row=dict(profile_case.selected_row),
                stage35_cfg_override=dict(STAGE35_CFG_OVERRIDE),
                batch_eval_chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
                output_dir=case_output_dir,
            )
        )
        resume_mod.write_resume_bundle(payload, output_dir=case_output_dir)
        payload_rows.append(dict(payload))
        summary_row = build_case_summary_row(payload)
        case_summary_rows.append(dict(summary_row))
        print(
            "[stage35_bounded_replay] "
                f"case_done fixture={profile_case.fixture_label} "
                f"selector={profile_case.selector} "
                f"accept_reason={summary_row['accept_reason']} "
                f"runtime_seconds={summary_row['runtime_seconds']} "
                f"batch_eval_chunk_size={int(BATCH_EVAL_CHUNK_SIZE)}",
            flush=True,
        )

    fixture_split_rows = build_fixture_split_rows(case_summary_rows)
    summary = dict(
        run_label=RUN_LABEL,
        selected_rows_relpath=str(selected_rows_path.relative_to(REPO_ROOT)),
        batch_eval_chunk_size=int(BATCH_EVAL_CHUNK_SIZE),
        stage35_cfg_override=dict(STAGE35_CFG_OVERRIDE),
        case_count=int(len(case_summary_rows)),
        fixture_splits=list(fixture_split_rows),
        acceptance_split_preserved_all=int(
            1
            if fixture_split_rows
            and all(
                int(row.get("acceptance_split_preserved", 0) or 0) == 1
                for row in fixture_split_rows
            )
            else 0
        ),
    )

    _write_csv(run_dir / "case_summary.csv", case_summary_rows)
    _write_csv(run_dir / "fixture_split_summary.csv", fixture_split_rows)
    (run_dir / "case_payloads.json").write_text(
        json.dumps(_jsonify(payload_rows), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (run_dir / "summary.json").write_text(
        json.dumps(_jsonify(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Stage 3.5 Bounded Replay Baseline",
        "",
        f"- selected rows: `{str(selected_rows_path.relative_to(REPO_ROOT))}`",
        f"- case count: `{int(len(case_summary_rows))}`",
        f"- acceptance split preserved for all fixtures: `{int(summary['acceptance_split_preserved_all'])}`",
        "",
    ]
    for row in fixture_split_rows:
        lines.extend(
            [
                f"## {str(row['fixture_label'])}",
                "",
                f"- legacy accept reason: `{str(row['legacy_accept_reason'])}`",
                f"- candidate accept reason: `{str(row['candidate_accept_reason'])}`",
                f"- split preserved: `{int(row['acceptance_split_preserved'])}`",
                "",
            ]
        )
    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(
        "[stage35_bounded_replay] "
        f"run_dir={str(run_dir.relative_to(REPO_ROOT))}",
        flush=True,
    )
    refresh_catalog_safely(print_fn=print)


if __name__ == "__main__":
    main()
