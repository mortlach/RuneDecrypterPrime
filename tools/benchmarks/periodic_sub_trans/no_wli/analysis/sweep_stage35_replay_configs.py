from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (
    refresh_catalog_safely,
)
from tools.benchmarks.periodic_sub_trans.no_wli import (
    late_stage_selector_stageb_continuation as continuation_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    profile_stage35_replay_hotspots as profile_mod,
)


RUN_LABEL = "sweep_stage35_replay_configs_v1"
OUTPUT_ROOT = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "stage35_replay_sweep"
)
ACTIVE_FIXTURE_LABELS: tuple[str, ...] = ("candidate",)
ACTIVE_SELECTORS: tuple[str, ...] = ("legacy", "score_plus_novelty")
BASE_STAGE35_CFG = dict(
    seed_keep=2,
    beam_width=3,
    archive_keep=12,
    rounds=1,
    mini_search_steps=1,
    mini_search_beam_width=2,
    mini_search_top_symbols=10,
    mini_search_final_keep=2,
    mini_search_keep_all_rows=0,
)
STAGE35_SWEEP_VARIANTS: tuple[dict[str, Any], ...] = (
    dict(variant_id="baseline", knob="baseline", cfg=dict(BASE_STAGE35_CFG)),
    dict(
        variant_id="top_symbols_8",
        knob="mini_search_top_symbols",
        cfg=dict(BASE_STAGE35_CFG, mini_search_top_symbols=8),
    ),
    dict(
        variant_id="top_symbols_6",
        knob="mini_search_top_symbols",
        cfg=dict(BASE_STAGE35_CFG, mini_search_top_symbols=6),
    ),
    dict(
        variant_id="beam_width_2",
        knob="beam_width",
        cfg=dict(BASE_STAGE35_CFG, beam_width=2),
    ),
    dict(
        variant_id="beam_width_1",
        knob="beam_width",
        cfg=dict(BASE_STAGE35_CFG, beam_width=1),
    ),
    dict(
        variant_id="final_keep_1",
        knob="mini_search_final_keep",
        cfg=dict(BASE_STAGE35_CFG, mini_search_final_keep=1),
    ),
    dict(
        variant_id="archive_keep_8",
        knob="archive_keep",
        cfg=dict(BASE_STAGE35_CFG, archive_keep=8),
    ),
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


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_variant_summary(
    variant: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, Any]],
    *,
    baseline_candidate_row: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows_by_selector = {
        str(dict(row).get("selector", "") or ""): dict(row)
        for row in list(case_rows or [])
    }
    legacy_row = dict(rows_by_selector.get("legacy", {}) or {})
    candidate_row = dict(rows_by_selector.get("score_plus_novelty", {}) or {})
    baseline_row = dict(baseline_candidate_row or {})

    legacy_accept_passed = int(legacy_row.get("accept_passed", 0) or 0)
    candidate_accept_passed = int(candidate_row.get("accept_passed", 0) or 0)
    return dict(
        variant_id=str(variant.get("variant_id", "") or ""),
        knob=str(variant.get("knob", "") or ""),
        cfg=dict(variant.get("cfg", {}) or {}),
        legacy_wallclock_seconds=_safe_float(legacy_row.get("wallclock_seconds")),
        legacy_eval_count=int(legacy_row.get("evals", 0) or 0),
        legacy_proposals_generated=int(
            legacy_row.get("telemetry_mini_search_proposals_generated", 0) or 0
        ),
        legacy_average_proposals_per_mini=_safe_float(
            legacy_row.get("telemetry_average_proposals_generated_per_mini")
        ),
        legacy_row_scoring_seconds=_safe_float(
            legacy_row.get("telemetry_row_scoring_seconds")
        ),
        legacy_batch_score_seconds=_safe_float(
            legacy_row.get("telemetry_batch_score_seconds")
        ),
        legacy_mini_search_total_seconds=_safe_float(
            legacy_row.get("telemetry_mini_search_total_seconds")
        ),
        legacy_accept_reason=str(legacy_row.get("accept_reason", "") or ""),
        legacy_accept_passed=int(legacy_accept_passed),
        legacy_best_truth_match=_safe_float(
            legacy_row.get("resume_best_truth_match")
        ),
        legacy_best_score=_safe_float(legacy_row.get("resume_best_score")),
        candidate_wallclock_seconds=_safe_float(
            candidate_row.get("wallclock_seconds")
        ),
        candidate_eval_count=int(candidate_row.get("evals", 0) or 0),
        candidate_proposals_generated=int(
            candidate_row.get("telemetry_mini_search_proposals_generated", 0) or 0
        ),
        candidate_average_proposals_per_mini=_safe_float(
            candidate_row.get("telemetry_average_proposals_generated_per_mini")
        ),
        candidate_row_scoring_seconds=_safe_float(
            candidate_row.get("telemetry_row_scoring_seconds")
        ),
        candidate_batch_score_seconds=_safe_float(
            candidate_row.get("telemetry_batch_score_seconds")
        ),
        candidate_mini_search_total_seconds=_safe_float(
            candidate_row.get("telemetry_mini_search_total_seconds")
        ),
        candidate_accept_reason=str(candidate_row.get("accept_reason", "") or ""),
        candidate_accept_passed=int(candidate_accept_passed),
        candidate_best_truth_match=_safe_float(
            candidate_row.get("resume_best_truth_match")
        ),
        candidate_best_score=_safe_float(candidate_row.get("resume_best_score")),
        acceptance_split_preserved=int(
            1 if legacy_accept_passed == 0 and candidate_accept_passed == 1 else 0
        ),
        candidate_runtime_vs_baseline_ratio=(
            float(candidate_row.get("wallclock_seconds", 0.0) or 0.0)
            / float(baseline_row.get("wallclock_seconds", 0.0) or 1.0)
            if baseline_row
            and float(baseline_row.get("wallclock_seconds", 0.0) or 0.0) > 0.0
            else None
        ),
        candidate_proposals_vs_baseline_ratio=(
            float(
                candidate_row.get("telemetry_mini_search_proposals_generated", 0) or 0
            )
            / float(
                baseline_row.get("telemetry_mini_search_proposals_generated", 0) or 1
            )
            if baseline_row
            and int(
                baseline_row.get("telemetry_mini_search_proposals_generated", 0) or 0
            )
            > 0
            else None
        ),
        candidate_row_scoring_vs_baseline_ratio=(
            float(candidate_row.get("telemetry_row_scoring_seconds", 0.0) or 0.0)
            / float(baseline_row.get("telemetry_row_scoring_seconds", 0.0) or 1.0)
            if baseline_row
            and float(
                baseline_row.get("telemetry_row_scoring_seconds", 0.0) or 0.0
            )
            > 0.0
            else None
        ),
    )


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

    case_rows: list[dict[str, Any]] = []
    variant_summaries: list[dict[str, Any]] = []
    baseline_candidate_row: dict[str, Any] | None = None
    for variant in STAGE35_SWEEP_VARIANTS:
        variant_id = str(variant.get("variant_id", "") or "")
        cfg = dict(variant.get("cfg", {}) or {})
        print(
            "[stage35_replay_sweep] "
            f"variant_start id={variant_id} knob={str(variant.get('knob', '') or '')}",
            flush=True,
        )
        variant_case_rows: list[dict[str, Any]] = []
        for profile_case in profile_cases:
            row = profile_mod.run_profile_case(
                profile_case,
                stage35_cfg_override=cfg,
            )
            row["variant_id"] = str(variant_id)
            row["variant_knob"] = str(variant.get("knob", "") or "")
            case_rows.append(dict(row))
            variant_case_rows.append(dict(row))
        if variant_id == "baseline":
            for row in variant_case_rows:
                if str(row.get("selector", "") or "") == "score_plus_novelty":
                    baseline_candidate_row = dict(row)
                    break
        summary_row = build_variant_summary(
            variant,
            variant_case_rows,
            baseline_candidate_row=baseline_candidate_row,
        )
        variant_summaries.append(dict(summary_row))
        print(
            "[stage35_replay_sweep] "
            f"variant_done id={variant_id} "
            f"split_preserved={int(summary_row['acceptance_split_preserved'])} "
            f"candidate_wallclock_seconds={summary_row['candidate_wallclock_seconds']}",
            flush=True,
        )

    csv_case_rows = []
    payload_rows = []
    for row in case_rows:
        row_copy = dict(row)
        payload_rows.append(dict(row_copy.pop("payload", {}) or {}))
        row_copy["stage35_cfg_override"] = json.dumps(
            _jsonify(row_copy.get("stage35_cfg_override", {})),
            sort_keys=True,
        )
        csv_case_rows.append(row_copy)
    csv_summary_rows = []
    for row in variant_summaries:
        row_copy = dict(row)
        row_copy["cfg"] = json.dumps(_jsonify(row_copy.get("cfg", {})), sort_keys=True)
        csv_summary_rows.append(row_copy)

    _write_csv(run_dir / "case_rows.csv", csv_case_rows)
    _write_csv(run_dir / "variant_summary.csv", csv_summary_rows)
    (run_dir / "case_payloads.json").write_text(
        json.dumps(_jsonify(payload_rows), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = dict(
        run_label=RUN_LABEL,
        selected_rows_relpath=str(selected_rows_path.relative_to(REPO_ROOT)),
        active_fixture_labels=list(ACTIVE_FIXTURE_LABELS),
        active_selectors=list(ACTIVE_SELECTORS),
        base_stage35_cfg=dict(BASE_STAGE35_CFG),
        variants=[dict(row) for row in variant_summaries],
    )
    (run_dir / "summary.json").write_text(
        json.dumps(_jsonify(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(
        "[stage35_replay_sweep] "
        f"run_dir={str(run_dir.relative_to(REPO_ROOT))}",
        flush=True,
    )
    refresh_catalog_safely(print_fn=print)


if __name__ == "__main__":
    main()
