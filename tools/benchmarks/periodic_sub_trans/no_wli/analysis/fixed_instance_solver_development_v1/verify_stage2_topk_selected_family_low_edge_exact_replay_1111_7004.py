from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Callable, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod  # noqa: E402
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    extract_fixed_instance_solver_development_v1 as base_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    extract_stage2_topk_family_representative_policy_audit_v1 as policy_mod,
)


FIXTURE_SEED = 1111
SEARCH_SEED = 7004
RUN_LABEL = "stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1"
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
)
ENABLE_STAGE35 = False
POLICY_ID = "selected_family_low_edge_eps_0p016_v1"
POLICY_SCORE_BAND_EPS = 0.016
POLICY_FAMILY_VIEW_ID = policy_mod.PRIMARY_VIEW_ID


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_str(value: Any) -> str:
    return str(value or "")


def _load_source_inventory_row(*, search_seed: int) -> dict[str, Any]:
    for row in base_mod._read_csv_rows(base_mod.PANEL_INVENTORY_CSV):
        if (
            _safe_int(row.get("fixture_seed")) == FIXTURE_SEED
            and _safe_int(row.get("search_seed")) == int(search_seed)
        ):
            return dict(row)
    raise RuntimeError(
        f"Missing fixed-panel inventory row for {FIXTURE_SEED}/search{int(search_seed)}"
    )


def _source_artifact_relpath(*, search_seed: int) -> Path:
    inventory_row = _load_source_inventory_row(search_seed=int(search_seed))
    report_dir = Path(_safe_str(inventory_row.get("source_report_dir")))
    return report_dir / "final_instances" / (
        f"fixture_001__p9_c3_l1000__text0__seed{FIXTURE_SEED}__search{int(search_seed)}.json"
    )


def _first_finite_match_row(
    rows: list[Mapping[str, Any]],
) -> Mapping[str, Any]:
    best_row: Mapping[str, Any] = {}
    best_match = float("-inf")
    for row in rows:
        match_ratio = _safe_float(row.get("match_ratio"))
        if math.isfinite(match_ratio) and match_ratio > best_match:
            best_match = match_ratio
            best_row = dict(row)
    return dict(best_row)


def extract_retained_stage3_reference(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    best_truth_start = dict(diagnostics.get("phaseC_best_truth_start_summary", {}) or {})
    best_truth_match = _safe_float(best_truth_start.get("final_match"))
    if math.isfinite(best_truth_match):
        return {
            "match_ratio": float(best_truth_match),
            "source": "phaseC_best_truth_start_summary",
            "stage3_source": _safe_str(best_truth_start.get("source")),
            "candidate_hash": _safe_str(best_truth_start.get("candidate_hash")),
            "source_rank": _safe_int(best_truth_start.get("source_rank")),
        }

    disagreement = dict(diagnostics.get("phaseC_truth_disagreement_summary", {}) or {})
    disagreement_match = _safe_float(disagreement.get("best_truth_match"))
    if math.isfinite(disagreement_match):
        return {
            "match_ratio": float(disagreement_match),
            "source": "phaseC_truth_disagreement_summary",
            "stage3_source": _safe_str(disagreement.get("best_truth_source")),
            "candidate_hash": _safe_str(disagreement.get("best_truth_candidate_hash")),
            "source_rank": 0,
        }

    truth_diag_rows = [
        dict(row)
        for row in list(
            (artifact.get("truth_diagnostics", {}) or {}).get(
                "stage3_topk_truth_diagnostics",
                [],
            )
            or []
        )
    ]
    truth_diag_best = _first_finite_match_row(truth_diag_rows)
    truth_diag_match = _safe_float(truth_diag_best.get("match_ratio"))
    if math.isfinite(truth_diag_match):
        return {
            "match_ratio": float(truth_diag_match),
            "source": "truth_diagnostics.stage3_topk_truth_diagnostics",
            "stage3_source": _safe_str(truth_diag_best.get("source")),
            "candidate_hash": _safe_str(truth_diag_best.get("candidate_hash")),
            "source_rank": _safe_int(truth_diag_best.get("rank")),
        }

    stage3_topk_rows = [dict(row) for row in list(artifact.get("stage3_topk", []) or [])]
    stage3_topk_best = _first_finite_match_row(stage3_topk_rows)
    stage3_topk_match = _safe_float(stage3_topk_best.get("match_ratio"))
    if math.isfinite(stage3_topk_match):
        return {
            "match_ratio": float(stage3_topk_match),
            "source": "stage3_topk",
            "stage3_source": _safe_str(stage3_topk_best.get("source")),
            "candidate_hash": _safe_str(stage3_topk_best.get("candidate_hash")),
            "source_rank": _safe_int(stage3_topk_best.get("rank")),
        }

    artifact_best_match = _safe_float(artifact.get("best_match_ratio"))
    return {
        "match_ratio": float(artifact_best_match),
        "source": "artifact_best_fallback",
        "stage3_source": _safe_str(artifact.get("best_stage")),
        "candidate_hash": "",
        "source_rank": 0,
    }


def _build_stage2_resume_override(
    saved_bundle: Mapping[str, Any],
    *,
    override_row: Mapping[str, Any],
) -> resume_mod.Stage2ResumeInputs:
    base_resume = saved_bundle["stage2_resume"]
    return resume_mod.Stage2ResumeInputs(
        best2_key=list(override_row.get("key", []) or []),
        best2_pt=list(base_resume.best2_pt),
        best2_score=_safe_float(override_row.get("score_stage2")),
        best2_match=_safe_float(override_row.get("truth_match")),
        best2_preview=_safe_str(base_resume.best2_preview),
        stage2_promoted=[dict(row) for row in list(base_resume.stage2_promoted)],
        stage2_entry_score=_safe_float(base_resume.stage2_entry_score),
        stage2_entry_score_judge=_safe_float(base_resume.stage2_entry_score_judge),
        stage2_topk_row_count=_safe_int(base_resume.stage2_topk_row_count),
        stage2_promote_top_cfg=_safe_int(base_resume.stage2_promote_top_cfg),
        stage2_promoted_from_topk_count=_safe_int(
            base_resume.stage2_promoted_from_topk_count
        ),
    )


def build_exact_replay_summary(
    *,
    case: Any,
    payload: Mapping[str, Any],
    baseline_row: Mapping[str, Any],
    candidate_row: Mapping[str, Any],
    candidate_prep: Mapping[str, Any],
    run_label: str,
    search_seed: int,
) -> dict[str, Any]:
    retained_stage3_reference = extract_retained_stage3_reference(case.artifact)
    baseline_best_match_ratio = _safe_float(case.artifact.get("best_match_ratio"))
    resume_best_match_ratio = _safe_float(payload.get("resume_best_match_ratio"))
    return {
        "run_label": str(run_label),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "source_run_dir_relpath": _relative_path(case.run_dir),
        "fixture_seed": FIXTURE_SEED,
        "search_seed": int(search_seed),
        "candidate_policy_id": POLICY_ID,
        "family_view_id": POLICY_FAMILY_VIEW_ID,
        "score_band_eps": POLICY_SCORE_BAND_EPS,
        "baseline_best_stage": _safe_str(case.artifact.get("best_stage")),
        "baseline_best_match_ratio": float(baseline_best_match_ratio),
        "retained_stage3_reference_match_ratio": float(
            _safe_float(retained_stage3_reference.get("match_ratio"))
        ),
        "retained_stage3_reference_source": _safe_str(
            retained_stage3_reference.get("source")
        ),
        "retained_stage3_reference_stage3_source": _safe_str(
            retained_stage3_reference.get("stage3_source")
        ),
        "resume_best_stage": _safe_str(payload.get("resume_best_stage")),
        "resume_best_match_ratio": float(resume_best_match_ratio),
        "resume_best_score": _safe_float(payload.get("resume_best_score")),
        "match_delta_vs_baseline": float(
            resume_best_match_ratio - baseline_best_match_ratio
        ),
        "match_delta_vs_retained_stage3_reference": float(
            resume_best_match_ratio
            - _safe_float(retained_stage3_reference.get("match_ratio"))
        ),
        "resume_source": _safe_str(payload.get("resume_source")),
        "stage35_enabled_effective": _safe_int(
            payload.get("stage35_enabled_effective")
        ),
        "baseline_row_id": _safe_str(baseline_row.get("row_id")),
        "baseline_row_truth_match": _safe_float(baseline_row.get("truth_match")),
        "candidate_row_id": _safe_str(candidate_row.get("row_id")),
        "candidate_row_truth_match": _safe_float(candidate_row.get("truth_match")),
        "candidate_truth_delta_vs_baseline_row": (
            _safe_float(candidate_row.get("truth_match"))
            - _safe_float(baseline_row.get("truth_match"))
        ),
        "candidate_init3_count": _safe_int(candidate_prep.get("init3_n")),
        "candidate_stage3_promoted_keys_count": _safe_int(
            candidate_prep.get("stage3_promoted_keys_count")
        ),
        "phasea_gate_action_applied": _safe_int(
            payload.get("phasea_gate_action_applied")
        ),
        "phasea_gate_action_contract_id": _safe_str(
            ((payload.get("phasea_gate_action") or {}).get("action_contract_id"))
        ),
        "phasea_gate_action_mode": _safe_str(
            ((payload.get("phasea_gate_action") or {}).get("action_contract_mode"))
        ),
        "phasea_gate_action_reason": _safe_str(
            ((payload.get("phasea_gate_action") or {}).get("action_reason"))
        ),
        "phasea_gate_action_gate_verdict": _safe_str(
            ((payload.get("phasea_gate_action") or {}).get("gate_verdict"))
        ),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(float(seconds))))
    hours, rem = divmod(total_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _print_progress(message: str) -> None:
    print(f"[{_utc_now_iso()}] {message}", flush=True)


def write_exact_replay_markdown(
    output_dir: Path,
    *,
    summary: Mapping[str, Any],
) -> None:
    lines = [
        f"# Selected-Family Low-Edge Exact Replay: {FIXTURE_SEED} / search{SEARCH_SEED}",
        "",
        "Question:",
        (
            "- if the concrete upstream selector is applied on retained "
            f"`{FIXTURE_SEED}/search{SEARCH_SEED}`, does the exact Stage-3 replay "
            "beat the retained baseline or retained Stage-3 reference?"
        ),
        "",
        "Policy:",
        f"- family view: `{summary.get('family_view_id')}`",
        f"- selector: `{summary.get('candidate_policy_id')}`",
        f"- score band eps: `{summary.get('score_band_eps'):.3f}`",
        "",
        "Retained baseline versus replay:",
        f"- source: `{summary.get('source_artifact_relpath')}`",
        f"- baseline best: `{summary.get('baseline_best_stage')}` / `{summary.get('baseline_best_match_ratio'):.3f}`",
        (
            "- retained Stage-3 reference: "
            f"`{summary.get('retained_stage3_reference_source')}` / "
            f"`{summary.get('retained_stage3_reference_stage3_source')}` / "
            f"`{summary.get('retained_stage3_reference_match_ratio'):.3f}`"
        ),
        f"- replay best: `{summary.get('resume_best_stage')}` / `{summary.get('resume_best_match_ratio'):.3f}`",
        f"- match delta versus baseline: `{summary.get('match_delta_vs_baseline'):.3f}`",
        (
            "- match delta versus retained Stage-3 reference: "
            f"`{summary.get('match_delta_vs_retained_stage3_reference'):.3f}`"
        ),
        "",
        "Selector handoff details:",
        f"- baseline row: `{summary.get('baseline_row_id')}` / `{summary.get('baseline_row_truth_match'):.3f}`",
        f"- candidate row: `{summary.get('candidate_row_id')}` / `{summary.get('candidate_row_truth_match'):.3f}`",
        f"- candidate truth delta versus baseline row: `{summary.get('candidate_truth_delta_vs_baseline_row'):.3f}`",
        f"- candidate init3 count: `{summary.get('candidate_init3_count')}`",
        f"- candidate promoted-keys count: `{summary.get('candidate_stage3_promoted_keys_count')}`",
        "",
        "Scope note:",
        "- stage35 stays disabled so the read stays focused on the upstream selector's Stage-3 effect rather than downstream substitution",
    ]
    (output_dir / "selected_family_low_edge_exact_replay_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_verification(
    *,
    search_seed: int | None = None,
    run_label: str | None = None,
    phasea_provisional_gate_action_decider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ]
    | None = None,
    phasea_gate_action_decider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ]
    | None = None,
    scope_note_override: str | None = None,
) -> dict[str, Any]:
    started_at = monotonic()
    started_at_utc = _utc_now_iso()
    search_seed_i = int(SEARCH_SEED if search_seed is None else search_seed)
    run_label_s = str(RUN_LABEL if run_label is None else run_label)
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{run_label_s}"
    output_dir.mkdir(parents=True, exist_ok=False)
    attempt_status_path = output_dir / "attempt_status.json"

    source_artifact_relpath = _source_artifact_relpath(search_seed=search_seed_i)
    case = resume_mod.load_artifact_case(artifact_path=REPO_ROOT / source_artifact_relpath)
    saved_bundle = resume_mod.prepare_stage3_resume_inputs_from_case(
        case,
        case.run_config,
        prefer_saved_stage3_prep=True,
    )
    topk_rows = policy_mod._topk_rows(final_instance=case.artifact)
    _, baseline_row, family_rows = policy_mod._family_rows_for_selected(
        rows=topk_rows,
        columns=_safe_int(case.artifact.get("columns")),
    )
    candidate_row = policy_mod.select_selected_family_low_edge_row(
        family_rows=family_rows,
        selected_row=baseline_row,
        score_band_eps=POLICY_SCORE_BAND_EPS,
    )
    stage2_resume_override = _build_stage2_resume_override(
        saved_bundle,
        override_row=candidate_row,
    )
    stage3_prep_override = resume_mod._build_stage3_prep_from_stage2_resume(
        resume=stage2_resume_override,
        artifact=case.artifact,
        run_config=case.run_config,
    )

    resume_bundle_dir = output_dir / "resume_bundle"
    resume_bundle_dir.mkdir(parents=True, exist_ok=False)
    scope_note = str(
        scope_note_override
        or (
            "exact retained replay uses the concrete upstream selector while "
            "keeping stage35 disabled so the read stays focused on the "
            "Stage-3 execution effect"
        )
    )
    _write_json(
        output_dir / "attempt_manifest.json",
        {
            "run_label": str(run_label_s),
            "source_artifact_relpath": _relative_path(case.artifact_path),
            "source_run_dir_relpath": _relative_path(case.run_dir),
            "enable_stage35": int(1 if bool(ENABLE_STAGE35) else 0),
            "candidate_policy_id": POLICY_ID,
            "family_view_id": POLICY_FAMILY_VIEW_ID,
            "score_band_eps": POLICY_SCORE_BAND_EPS,
            "scope_note": scope_note,
            "phasea_provisional_gate_action_enabled": int(
                1 if callable(phasea_provisional_gate_action_decider) else 0
            ),
            "phasea_gate_action_enabled": int(
                1 if callable(phasea_gate_action_decider) else 0
            ),
        },
    )
    _write_json(
        attempt_status_path,
        {
            "status": "running",
            "completed": 0,
            "resume_bundle_written": 0,
            "started_at_utc": started_at_utc,
            "updated_at_utc": started_at_utc,
            "run_label": str(run_label_s),
            "output_dir": _relative_path(output_dir),
            "resume_bundle_dir": _relative_path(resume_bundle_dir),
            "source_artifact_relpath": _relative_path(case.artifact_path),
            "source_run_dir_relpath": _relative_path(case.run_dir),
            "candidate_policy_id": POLICY_ID,
            "family_view_id": POLICY_FAMILY_VIEW_ID,
            "score_band_eps": POLICY_SCORE_BAND_EPS,
            "scope_note": scope_note,
            "phasea_provisional_gate_action_enabled": int(
                1 if callable(phasea_provisional_gate_action_decider) else 0
            ),
            "phasea_gate_action_enabled": int(
                1 if callable(phasea_gate_action_decider) else 0
            ),
            "stage3_resume_status_json_relpath": _relative_path(
                resume_bundle_dir / resume_mod.STAGE3_RESUME_STATUS_JSON_NAME
            ),
            "stage3_resume_progress_jsonl_relpath": _relative_path(
                resume_bundle_dir / resume_mod.STAGE3_RESUME_PROGRESS_JSONL_NAME
            ),
            "phasea_provisional_gate_snapshots_jsonl_relpath": _relative_path(
                resume_bundle_dir
                / resume_mod.PHASEA_PROVISIONAL_GATE_SNAPSHOTS_JSONL_NAME
            ),
            "phasea_gate_snapshot_json_relpath": _relative_path(
                resume_bundle_dir / resume_mod.PHASEA_GATE_SNAPSHOT_JSON_NAME
            ),
            "phasec_start_checkpoint_relpath": _relative_path(
                resume_bundle_dir / "phasec_start_checkpoints.jsonl"
            ),
        },
    )
    _print_progress(
        "run_started "
        f"label={run_label_s} "
        f"output_dir={_relative_path(output_dir)} "
        f"source_artifact={_relative_path(case.artifact_path)} "
        f"candidate_policy={POLICY_ID} "
        f"family_view={POLICY_FAMILY_VIEW_ID} "
        f"score_band_eps={POLICY_SCORE_BAND_EPS:.3f}"
    )
    try:
        payload = resume_mod.run_stage3_resume_from_artifact(
            case,
            output_dir=resume_bundle_dir,
            enable_stage35=ENABLE_STAGE35,
            stage2_resume_override=stage2_resume_override,
            stage3_prep_override=stage3_prep_override,
            resume_source_override="selected_family_low_edge_eps_0p016_override",
            phasea_provisional_gate_action_decider=phasea_provisional_gate_action_decider,
            phasea_gate_action_decider=phasea_gate_action_decider,
        )
    except BaseException as exc:
        elapsed_seconds = float(monotonic() - started_at)
        _write_json(
            attempt_status_path,
            {
                "status": "interrupted_or_failed",
                "completed": 0,
                "resume_bundle_written": int(
                    1 if (resume_bundle_dir / "summary.json").exists() else 0
                ),
                "started_at_utc": started_at_utc,
                "updated_at_utc": _utc_now_iso(),
                "run_label": str(run_label_s),
                "output_dir": _relative_path(output_dir),
                "resume_bundle_dir": _relative_path(resume_bundle_dir),
                "source_artifact_relpath": _relative_path(case.artifact_path),
                "candidate_policy_id": POLICY_ID,
                "family_view_id": POLICY_FAMILY_VIEW_ID,
                "score_band_eps": POLICY_SCORE_BAND_EPS,
                "scope_note": scope_note,
                "phasea_provisional_gate_action_enabled": int(
                    1 if callable(phasea_provisional_gate_action_decider) else 0
                ),
                "phasea_gate_action_enabled": int(
                    1 if callable(phasea_gate_action_decider) else 0
                ),
                "elapsed": _format_duration(elapsed_seconds),
                "elapsed_seconds": elapsed_seconds,
                "error_type": str(type(exc).__name__),
                "error_message": str(exc),
                "stage3_resume_status_json_relpath": _relative_path(
                    resume_bundle_dir / resume_mod.STAGE3_RESUME_STATUS_JSON_NAME
                ),
                "stage3_resume_progress_jsonl_relpath": _relative_path(
                    resume_bundle_dir / resume_mod.STAGE3_RESUME_PROGRESS_JSONL_NAME
                ),
                "phasea_provisional_gate_snapshots_jsonl_relpath": _relative_path(
                    resume_bundle_dir
                    / resume_mod.PHASEA_PROVISIONAL_GATE_SNAPSHOTS_JSONL_NAME
                ),
                "phasea_gate_snapshot_json_relpath": _relative_path(
                    resume_bundle_dir / resume_mod.PHASEA_GATE_SNAPSHOT_JSON_NAME
                ),
                "phasec_start_checkpoint_relpath": _relative_path(
                    resume_bundle_dir / "phasec_start_checkpoints.jsonl"
                ),
            },
        )
        _print_progress(
            "run_interrupted "
            f"label={run_label_s} "
            f"elapsed={_format_duration(elapsed_seconds)} "
            f"error_type={type(exc).__name__} "
            f"output_dir={_relative_path(output_dir)}"
        )
        raise
    resume_mod.write_resume_bundle(payload, output_dir=resume_bundle_dir)
    summary = build_exact_replay_summary(
        case=case,
        payload=payload,
        baseline_row=baseline_row,
        candidate_row=candidate_row,
        candidate_prep=stage3_prep_override,
        run_label=run_label_s,
        search_seed=search_seed_i,
    )
    _write_json(output_dir / "selected_family_low_edge_exact_replay_summary.json", summary)
    write_exact_replay_markdown(output_dir, summary=summary)
    run_summary = {
        "output_dir": _relative_path(output_dir),
        "resume_bundle_dir": _relative_path(resume_bundle_dir),
        "source_artifact_relpath": str(summary["source_artifact_relpath"]),
        "fixture_seed": int(summary["fixture_seed"]),
        "search_seed": int(summary["search_seed"]),
        "candidate_policy_id": str(summary["candidate_policy_id"]),
        "baseline_best_match_ratio": float(summary["baseline_best_match_ratio"]),
        "retained_stage3_reference_match_ratio": float(
            summary["retained_stage3_reference_match_ratio"]
        ),
        "resume_best_match_ratio": float(summary["resume_best_match_ratio"]),
        "match_delta_vs_baseline": float(summary["match_delta_vs_baseline"]),
        "match_delta_vs_retained_stage3_reference": float(
            summary["match_delta_vs_retained_stage3_reference"]
        ),
        "phasea_gate_action_applied": int(
            _safe_int(summary.get("phasea_gate_action_applied"))
        ),
        "phasea_gate_action_contract_id": str(
            summary.get("phasea_gate_action_contract_id", "")
        ),
        "phasea_gate_action_mode": str(summary.get("phasea_gate_action_mode", "")),
        "phasea_gate_action_reason": str(summary.get("phasea_gate_action_reason", "")),
        "phasea_gate_action_gate_verdict": str(
            summary.get("phasea_gate_action_gate_verdict", "")
        ),
        "stage3_resume_status_json_relpath": str(
            payload.get("stage3_resume_status_json_relpath", "")
        ),
        "stage3_resume_progress_jsonl_relpath": str(
            payload.get("stage3_resume_progress_jsonl_relpath", "")
        ),
        "phasea_provisional_gate_snapshots_jsonl_relpath": str(
            payload.get("phasea_provisional_gate_snapshots_jsonl_relpath", "")
        ),
        "phasea_gate_snapshot_json_relpath": str(
            payload.get("phasea_gate_snapshot_json_relpath", "")
        ),
        "phasec_start_checkpoint_relpath": str(
            payload.get("phasec_start_checkpoint_relpath", "")
        ),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    elapsed_seconds = float(monotonic() - started_at)
    _write_json(
        attempt_status_path,
        {
            "status": "completed",
            "completed": 1,
            "resume_bundle_written": 1,
            "started_at_utc": started_at_utc,
            "updated_at_utc": _utc_now_iso(),
            "run_label": str(run_label_s),
            "output_dir": _relative_path(output_dir),
            "resume_bundle_dir": _relative_path(resume_bundle_dir),
            "source_artifact_relpath": _relative_path(case.artifact_path),
            "candidate_policy_id": POLICY_ID,
            "family_view_id": POLICY_FAMILY_VIEW_ID,
            "score_band_eps": POLICY_SCORE_BAND_EPS,
            "scope_note": scope_note,
            "phasea_provisional_gate_action_enabled": int(
                1 if callable(phasea_provisional_gate_action_decider) else 0
            ),
            "phasea_gate_action_enabled": int(
                1 if callable(phasea_gate_action_decider) else 0
            ),
            "elapsed": _format_duration(elapsed_seconds),
            "elapsed_seconds": elapsed_seconds,
            "resume_best_match_ratio": float(summary["resume_best_match_ratio"]),
            "match_delta_vs_baseline": float(summary["match_delta_vs_baseline"]),
            "match_delta_vs_retained_stage3_reference": float(
                summary["match_delta_vs_retained_stage3_reference"]
            ),
            "phasea_gate_action_applied": int(
                _safe_int(summary.get("phasea_gate_action_applied"))
            ),
            "phasea_gate_action_contract_id": str(
                summary.get("phasea_gate_action_contract_id", "")
            ),
            "phasea_gate_action_mode": str(summary.get("phasea_gate_action_mode", "")),
            "phasea_gate_action_reason": str(
                summary.get("phasea_gate_action_reason", "")
            ),
            "phasea_gate_action_gate_verdict": str(
                summary.get("phasea_gate_action_gate_verdict", "")
            ),
            "stage3_resume_status_json_relpath": str(
                payload.get("stage3_resume_status_json_relpath", "")
            ),
            "stage3_resume_progress_jsonl_relpath": str(
                payload.get("stage3_resume_progress_jsonl_relpath", "")
            ),
            "phasea_provisional_gate_snapshots_jsonl_relpath": str(
                payload.get("phasea_provisional_gate_snapshots_jsonl_relpath", "")
            ),
            "phasea_gate_snapshot_json_relpath": str(
                payload.get("phasea_gate_snapshot_json_relpath", "")
            ),
            "phasec_start_checkpoint_relpath": str(
                payload.get("phasec_start_checkpoint_relpath", "")
            ),
        },
    )
    _print_progress(
        "run_finished "
        f"label={run_label_s} "
        f"elapsed={_format_duration(elapsed_seconds)} "
        f"resume_best_match={_safe_float(summary.get('resume_best_match_ratio')):.3f} "
        f"delta_vs_baseline={_safe_float(summary.get('match_delta_vs_baseline')):.3f} "
        f"output_dir={_relative_path(output_dir)}"
    )
    return run_summary


def main() -> None:
    summary = run_verification()
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
