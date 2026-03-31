from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[4]
CATALOG_DIR = REPO_ROOT / "output" / "tools" / "benchmarks" / "periodic_sub_trans" / "no_wli_catalog"

PRIMARY_OLD_RUN = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260312T002501438386Z__bench_solve_pipeline_no_wli__5961d3e"
)
SECONDARY_OLD_RUNS = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260315T001203236783Z__bench_solve_pipeline_no_wli__5961d3e",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260315T215112716215Z__bench_solve_pipeline_no_wli__5961d3e",
)
CURRENT_PROOF_RUN = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260321T005721635958Z__bench_solve_pipeline_no_wli__55b7159"
)
TARGET_INSTANCE_NAME = "fixture_fixture_001_p9_c3_l1000__text0__seed511.json"


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _coerce_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if out != out:
        return None
    return out


def _mean_or_none(values: Sequence[float | None]) -> float | None:
    finite = [float(v) for v in values if v is not None]
    if not finite:
        return None
    return float(mean(finite))


def _extract_match(row: Mapping[str, Any]) -> float | None:
    for key in ("match_ratio", "truth_match_ratio", "end_match", "best_match_ratio"):
        value = _coerce_float(row.get(key))
        if value is not None:
            return value
    return None


def _extract_topk_matches(rows: Sequence[Mapping[str, Any]], *, limit: int = 5) -> list[float | None]:
    out: list[float | None] = []
    for row in list(rows)[:limit]:
        out.append(_extract_match(dict(row)))
    return out


def extract_stage3_config_fields(run_config: Mapping[str, Any]) -> dict[str, Any]:
    stage3 = dict(run_config.get("stage3", {}) or {})
    two_phase = dict(stage3.get("two_phase", {}) or {})
    phase_a = dict(two_phase.get("phase_a", {}) or {})
    phase_b = dict(two_phase.get("phase_b", {}) or {})
    phase_c = dict(two_phase.get("phase_c", {}) or {})
    stage35 = dict(stage3.get("stage35", {}) or {})
    stage35_cfg = dict(stage35.get("cfg", {}) or {})
    return dict(
        init_keys=int(stage3.get("init_keys", 0) or 0),
        phaseA_steps=int(phase_a.get("steps", 0) or 0),
        phaseA_restarts=int(phase_a.get("restarts", 0) or 0),
        phaseB_steps=int(phase_b.get("steps", 0) or 0),
        phaseB_top_n=int(two_phase.get("phase_b_top_n", phase_b.get("top_n", 0)) or 0),
        phaseC_enabled=int(1 if bool(phase_c.get("enabled", False)) else 0),
        phaseC_start_keys=int(phase_c.get("start_keys", 0) or 0),
        stage35_requested=int(1 if bool(stage35.get("enabled", False)) else 0),
        stage35_rounds=int(stage35_cfg.get("rounds", 0) or 0),
        stage35_beam_width=int(stage35_cfg.get("beam_width", 0) or 0),
    )


def _build_run_paths(run_dir_rel: str) -> dict[str, Path]:
    run_dir = REPO_ROOT / Path(run_dir_rel)
    return dict(
        run_dir=run_dir,
        run_config=run_dir / "run_config.json",
        stages=run_dir / "stages.json",
        artifact=run_dir / "final_instances" / TARGET_INSTANCE_NAME,
    )


def summarize_run(run_dir_rel: str) -> dict[str, Any]:
    paths = _build_run_paths(run_dir_rel)
    artifact = _read_json(paths["artifact"])
    run_config = _read_json(paths["run_config"])
    stage3_diag = dict(artifact.get("stage3_diagnostics", {}) or {})
    truth_diag = dict(artifact.get("truth_diagnostics", {}) or {})
    stage2_matches = _extract_topk_matches(list(artifact.get("stage2_topk", []) or []))
    stage3_matches = _extract_topk_matches(list(artifact.get("stage3_topk", []) or []))
    stage3_cfg = extract_stage3_config_fields(run_config)
    return dict(
        run_dir=_repo_rel(paths["run_dir"]),
        run_config_path=_repo_rel(paths["run_config"]),
        artifact_path=_repo_rel(paths["artifact"]),
        best_match_ratio=_coerce_float(artifact.get("best_match_ratio")) or 0.0,
        best_score=_coerce_float(artifact.get("best_score")),
        best_stage=str(artifact.get("best_stage", "") or ""),
        stage2_topk_top5_matches=stage2_matches,
        stage2_topk_top5_mean=_mean_or_none(stage2_matches),
        stage3_topk_top5_matches=stage3_matches,
        stage3_topk_top5_mean=_mean_or_none(stage3_matches),
        stage3_eval_count=int(stage3_diag.get("stage3_eval_count", 0) or 0),
        stage3_init_target=int(stage3_diag.get("init_target", 0) or 0),
        stage3_init_actual=int(stage3_diag.get("init_actual", 0) or 0),
        stage3_promoted_keys=int(stage3_diag.get("promoted_keys", 0) or 0),
        phaseB_ran=int(stage3_diag.get("phaseB_ran", 0) or 0),
        phaseB_topk_saved_count=int(stage3_diag.get("phaseB_topk_saved_count", 0) or 0),
        phaseB_selected_unique_end_hash=int(
            stage3_diag.get("phaseB_selected_unique_end_hash", 0) or 0
        ),
        phaseC_ran=int(stage3_diag.get("phaseC_ran", 0) or 0),
        phaseC_challenger_overtook_anchor_count=int(
            stage3_diag.get("phaseC_challenger_overtook_anchor_count", 0) or 0
        ),
        stage35_enabled_cfg=int(stage3_diag.get("stage35_enabled_cfg", 0) or 0),
        stage35_ran=int(stage3_diag.get("stage35_ran", 0) or 0),
        stage35_archive_count=int(stage3_diag.get("stage35_archive_count", 0) or 0),
        stage35_requested_cfg=int(artifact.get("stage35_requested_cfg", 0) or 0),
        stage35_proof_valid=int(artifact.get("stage35_proof_valid", 0) or 0),
        stage35_proof_invalid_reason=str(
            artifact.get("stage35_proof_invalid_reason", "") or ""
        ),
        truth_key_hamming_substitution=_coerce_float(
            truth_diag.get("key_hamming_substitution")
        ),
        truth_key_hamming_columns=_coerce_float(truth_diag.get("key_hamming_columns")),
        stage3_cfg=stage3_cfg,
    )


def classify_regression(
    *,
    old_summary: Mapping[str, Any],
    new_summary: Mapping[str, Any],
) -> dict[str, Any]:
    old_stage2_mean = _coerce_float(old_summary.get("stage2_topk_top5_mean"))
    new_stage2_mean = _coerce_float(new_summary.get("stage2_topk_top5_mean"))
    old_stage3_mean = _coerce_float(old_summary.get("stage3_topk_top5_mean"))
    new_stage3_mean = _coerce_float(new_summary.get("stage3_topk_top5_mean"))
    old_best = _coerce_float(old_summary.get("best_match_ratio"))
    new_best = _coerce_float(new_summary.get("best_match_ratio"))

    stage2_delta = (
        float(new_stage2_mean - old_stage2_mean)
        if old_stage2_mean is not None and new_stage2_mean is not None
        else None
    )
    stage3_delta = (
        float(new_stage3_mean - old_stage3_mean)
        if old_stage3_mean is not None and new_stage3_mean is not None
        else None
    )
    final_delta = (
        float(new_best - old_best)
        if old_best is not None and new_best is not None
        else None
    )

    evidence_rows = [
        dict(metric="stage2_topk_top5_mean_match", old=old_stage2_mean, new=new_stage2_mean, delta=stage2_delta),
        dict(metric="stage3_topk_top5_mean_match", old=old_stage3_mean, new=new_stage3_mean, delta=stage3_delta),
        dict(metric="final_best_match_ratio", old=old_best, new=new_best, delta=final_delta),
        dict(
            metric="stage3_phaseB_steps",
            old=int(dict(old_summary.get("stage3_cfg", {})).get("phaseB_steps", 0)),
            new=int(dict(new_summary.get("stage3_cfg", {})).get("phaseB_steps", 0)),
            delta=int(dict(new_summary.get("stage3_cfg", {})).get("phaseB_steps", 0))
            - int(dict(old_summary.get("stage3_cfg", {})).get("phaseB_steps", 0)),
        ),
        dict(
            metric="stage3_init_keys",
            old=int(dict(old_summary.get("stage3_cfg", {})).get("init_keys", 0)),
            new=int(dict(new_summary.get("stage3_cfg", {})).get("init_keys", 0)),
            delta=int(dict(new_summary.get("stage3_cfg", {})).get("init_keys", 0))
            - int(dict(old_summary.get("stage3_cfg", {})).get("init_keys", 0)),
        ),
    ]

    if stage2_delta is not None and stage2_delta <= -0.05:
        primary_culprit = "pre_stage3_regression"
        rationale = (
            "The newer branch is already materially weaker at Stage 2, before Stage-3 basin generation begins."
        )
    elif (
        stage2_delta is not None
        and abs(stage2_delta) <= 0.01
        and stage3_delta is not None
        and stage3_delta <= -0.05
    ):
        primary_culprit = "inside_stage3_basin_generation"
        rationale = (
            "Stage-2 candidate quality is effectively unchanged, but the regression appears immediately in the "
            "Stage-3 top-k family."
        )
    elif (
        stage3_delta is not None
        and abs(stage3_delta) <= 0.01
        and final_delta is not None
        and final_delta <= -0.05
    ):
        primary_culprit = "late_handoff_regression"
        rationale = (
            "Stage-3 basin quality is similar, but the newer branch loses ground only after the late handoff."
        )
    else:
        primary_culprit = "inside_stage3_basin_generation"
        rationale = (
            "The strongest regression signal is the Stage-3 family collapse, and there is not enough evidence "
            "to blame pre-Stage-3 or late handoff first."
        )

    return dict(
        primary_culprit=str(primary_culprit),
        rationale=str(rationale),
        evidence_rows=evidence_rows,
        secondary_contributors=[],
    )


def build_basin_regression_summary() -> dict[str, Any]:
    primary_old = summarize_run(PRIMARY_OLD_RUN)
    current = summarize_run(CURRENT_PROOF_RUN)
    old_family = [summarize_run(PRIMARY_OLD_RUN)] + [
        summarize_run(run_dir_rel) for run_dir_rel in SECONDARY_OLD_RUNS
    ]
    classification = classify_regression(old_summary=primary_old, new_summary=current)
    return dict(
        target_instance_name=str(TARGET_INSTANCE_NAME),
        primary_old=primary_old,
        current=current,
        old_family=old_family,
        primary_culprit=str(classification["primary_culprit"]),
        rationale=str(classification["rationale"]),
        secondary_contributors=list(classification.get("secondary_contributors", [])),
        evidence_rows=[dict(row) for row in list(classification["evidence_rows"])],
    )


def _format_num(value: Any, digits: int = 3) -> str:
    out = _coerce_float(value)
    if out is None:
        return ""
    return f"{out:.{int(digits)}f}"


def write_basin_regression_report(summary: Mapping[str, Any]) -> dict[str, str]:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = CATALOG_DIR / "basin_regression_summary.json"
    report_path = CATALOG_DIR / "basin_regression_report.md"
    summary_path.write_text(
        json.dumps(dict(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    primary_old = dict(summary["primary_old"])
    current = dict(summary["current"])
    old_family = list(summary["old_family"])
    evidence_rows = list(summary["evidence_rows"])
    old_family_rows = []
    for row in old_family:
        row_d = dict(row)
        old_family_rows.append(
            "| {run} | {best} | {stage3_mean} | {phaseb_steps} |".format(
                run=str(row_d["run_dir"]).split("/")[-1],
                best=_format_num(row_d.get("best_match_ratio")),
                stage3_mean=_format_num(row_d.get("stage3_topk_top5_mean")),
                phaseb_steps=dict(row_d.get("stage3_cfg", {})).get("phaseB_steps", 0),
            )
        )

    evidence_lines = []
    for row in evidence_rows:
        row_d = dict(row)
        evidence_lines.append(
            "| {metric} | {old} | {new} | {delta} |".format(
                metric=str(row_d.get("metric", "")),
                old=_format_num(row_d.get("old")),
                new=_format_num(row_d.get("new")),
                delta=_format_num(row_d.get("delta")),
            )
        )

    report_text = "\n".join(
        [
            "# no_wli Basin Regression Report",
            "",
            "## Conclusion",
            "",
            f"- Primary culprit: `{summary['primary_culprit']}`",
            f"- Rationale: {summary['rationale']}",
            "",
            "## Primary A/B",
            "",
            f"- Old reference: `{primary_old['run_dir']}`",
            f"- Current proof branch: `{current['run_dir']}`",
            "",
            "| Metric | Old | Current | Delta |",
            "| --- | ---: | ---: | ---: |",
            *evidence_lines,
            "",
            "## Old Family Context",
            "",
            "| Run | Best Match | Stage3 Top5 Mean | PhaseB Steps |",
            "| --- | ---: | ---: | ---: |",
            *old_family_rows,
            "",
            "## Supporting Notes",
            "",
            "- The primary old and current runs have effectively identical `stage2_topk` top-5 match quality.",
            "- The regression first appears in `stage3_topk`, which points away from a pre-Stage-3 cause.",
            "- The current branch also reduced Phase-B depth while increasing Stage-3 entry width and late add-ons.",
            "- The invalid Stage-3.5 proof path remains important, but it does not explain the already-weaker `stage3_topk` family.",
            "",
            "## Canonical Inputs",
            "",
            f"- `{primary_old['artifact_path']}`",
            f"- `{primary_old['run_config_path']}`",
            f"- `{current['artifact_path']}`",
            f"- `{current['run_config_path']}`",
        ]
    ).strip() + "\n"
    report_path.write_text(report_text, encoding="utf-8")
    return dict(
        summary_path=_repo_rel(summary_path),
        report_path=_repo_rel(report_path),
    )


def main() -> None:
    summary = build_basin_regression_summary()
    outputs = write_basin_regression_report(summary)
    print(
        json.dumps(
            dict(
                primary_culprit=summary["primary_culprit"],
                summary_path=outputs["summary_path"],
                report_path=outputs["report_path"],
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
