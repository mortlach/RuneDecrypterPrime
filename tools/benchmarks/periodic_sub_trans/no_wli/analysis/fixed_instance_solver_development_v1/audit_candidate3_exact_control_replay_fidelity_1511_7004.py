from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "audit_candidate3_exact_control_replay_fidelity_1511_7004.py"
    )


REPO_ROOT = _find_repo_root()
RETAINED_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260414T020217422155Z__bench_solve_pipeline_no_wli__9557c0f/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed1511__search7004.json"
)
REPLAY_BUNDLE_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260416T163546Z__candidate3_phasec_anchor_swap_exact_control_"
    "1511_search7004_stage3_replay_v1"
)
RUN_LABEL = "candidate3_exact_control_replay_fidelity_1511_search7004_v1"
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

ORDERED_IDENTITY_SURFACE_NAMES = (
    "phaseB_downstream_selected_ordered_hashes",
    "phaseB_topk_saved_ordered_hashes",
    "phaseC_start_ordered_identities",
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_str(value: Any) -> str:
    return str(value or "")


def _ordered_hashes_from_phaseb_downstream_selected_summaries(
    payload: Mapping[str, Any],
) -> list[str] | None:
    rows = list(payload.get("phaseB_downstream_selected_summaries", []) or [])
    if rows:
        return [
            _safe_str(row.get("candidate_hash") or row.get("end_hash"))
            for row in rows
            if _safe_str(row.get("candidate_hash") or row.get("end_hash"))
        ]
    candidate_pool_rows = sorted(
        [
            dict(row)
            for row in list(payload.get("phaseC_candidate_pool_rows", []) or [])
            if _safe_str(row.get("source")) == "phaseA_selected"
        ],
        key=lambda row: _safe_int(row.get("source_rank")),
    )
    if not candidate_pool_rows:
        return None
    return [
        _safe_str(row.get("candidate_hash") or row.get("end_hash"))
        for row in candidate_pool_rows
        if _safe_str(row.get("candidate_hash") or row.get("end_hash"))
    ]


def _ordered_phaseb_topk_saved_summaries_from_retained_artifact(
    artifact: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows = sorted(
        [
            dict(row)
            for row in list(artifact.get("stage3_topk", []) or [])
            if _safe_str(row.get("source")) == "phaseB_topk"
        ],
        key=lambda row: _safe_int(row.get("rank")),
    )
    summaries: list[dict[str, Any]] = []
    for saved_rank, row in enumerate(rows, start=1):
        candidate_hash = _safe_str(row.get("candidate_hash") or row.get("end_hash"))
        summaries.append(
            {
                "saved_rank": int(saved_rank),
                "stage3_topk_rank": _safe_int(row.get("rank") or saved_rank),
                "candidate_hash": candidate_hash,
                "end_hash": candidate_hash,
                "source": _safe_str(row.get("source")),
                "match_ratio": _safe_float(row.get("match_ratio")),
            }
        )
    return summaries


def _ordered_phaseb_topk_saved_summaries_from_replay_flow(
    flow: Mapping[str, Any],
) -> list[dict[str, Any]]:
    saved_rows = list(flow.get("phaseB_topk_saved_summaries", []) or [])
    if saved_rows:
        return [dict(row) for row in saved_rows]
    topk_rows = sorted(
        [
            dict(row)
            for row in list(flow.get("stage3_topk_payload", []) or [])
            if _safe_str(row.get("source")) == "phaseB_topk"
        ],
        key=lambda row: _safe_int(row.get("rank")),
    )
    summaries: list[dict[str, Any]] = []
    for saved_rank, row in enumerate(topk_rows, start=1):
        candidate_hash = _safe_str(row.get("candidate_hash") or row.get("end_hash"))
        summaries.append(
            {
                "saved_rank": int(saved_rank),
                "stage3_topk_rank": _safe_int(row.get("rank") or saved_rank),
                "candidate_hash": candidate_hash,
                "end_hash": candidate_hash,
                "source": _safe_str(row.get("source")),
                "match_ratio": _safe_float(row.get("match_ratio")),
            }
        )
    return summaries


def _ordered_candidate_hashes(
    rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    hashes: list[str] = []
    for row in rows:
        candidate_hash = _safe_str(row.get("candidate_hash") or row.get("end_hash"))
        if candidate_hash:
            hashes.append(candidate_hash)
    return hashes


def _ordered_phasec_start_identities(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for start_rank, row in enumerate(rows, start=1):
        out.append(
            {
                "start_rank": int(start_rank),
                "source": _safe_str(row.get("source")),
                "source_rank": _safe_int(row.get("source_rank")),
                "candidate_hash": _safe_str(row.get("candidate_hash") or row.get("end_hash")),
                "final_match": _safe_float(row.get("final_match")),
            }
        )
    return out


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    if isinstance(value, float):
        if value != value:
            return "nan"
        return round(value, 6)
    return value


def _build_surface_comparison(
    *,
    surface_name: str,
    retained_value: Any,
    replay_value: Any,
    note: str = "",
) -> dict[str, Any]:
    retained_norm = _normalize_value(retained_value)
    replay_norm = _normalize_value(replay_value)
    if retained_value is None or replay_value is None:
        status = "unavailable"
    elif retained_norm == replay_norm:
        status = "match"
    else:
        status = "mismatch"
    return {
        "surface_name": str(surface_name),
        "status": str(status),
        "retained_value": retained_norm,
        "replay_value": replay_norm,
        "note": str(note or ""),
    }


def _first_surface_by_status(
    surface_rows: Sequence[Mapping[str, Any]],
    *,
    status: str,
) -> str:
    for row in surface_rows:
        if _safe_str(row.get("status")) == status:
            return _safe_str(row.get("surface_name"))
    return ""


def _ordered_identity_contract_rows(
    surface_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    wanted = set(ORDERED_IDENTITY_SURFACE_NAMES)
    for row in surface_rows:
        surface_name = _safe_str(row.get("surface_name"))
        if surface_name not in wanted:
            continue
        out.append(
            {
                "surface_name": surface_name,
                "status": _safe_str(row.get("status")),
                "exact_ordered_identity_match": int(
                    1 if _safe_str(row.get("status")) == "match" else 0
                ),
                "retained_value": _normalize_value(row.get("retained_value")),
                "replay_value": _normalize_value(row.get("replay_value")),
                "note": _safe_str(row.get("note")),
            }
        )
    return out


def build_replay_fidelity_summary(
    *,
    retained_artifact: Mapping[str, Any],
    replay_flow: Mapping[str, Any],
) -> dict[str, Any]:
    retained_diag = dict(retained_artifact.get("stage3_diagnostics", {}) or {})
    retained_phaseb_topk_saved_summaries = (
        _ordered_phaseb_topk_saved_summaries_from_retained_artifact(retained_artifact)
    )
    replay_phaseb_topk_saved_summaries = (
        _ordered_phaseb_topk_saved_summaries_from_replay_flow(replay_flow)
    )
    retained_phasec_start_rows = _ordered_phasec_start_identities(
        list(retained_diag.get("phaseC_start_summaries", []) or [])
    )
    replay_phasec_start_rows = _ordered_phasec_start_identities(
        list(replay_flow.get("phaseC_start_summaries", []) or [])
    )

    surface_rows = [
        _build_surface_comparison(
            surface_name="phaseB_selected_unique_end_hash",
            retained_value=_safe_int(retained_diag.get("phaseB_selected_unique_end_hash")),
            replay_value=_safe_int(replay_flow.get("phaseB_selected_unique_end_hash")),
            note="persisted count only",
        ),
        _build_surface_comparison(
            surface_name="phaseB_downstream_selected_count",
            retained_value=_safe_int(retained_diag.get("phaseB_downstream_selected_count")),
            replay_value=_safe_int(replay_flow.get("phaseB_downstream_selected_count")),
            note="persisted count only",
        ),
        _build_surface_comparison(
            surface_name="phaseB_downstream_selected_ordered_hashes",
            retained_value=_ordered_hashes_from_phaseb_downstream_selected_summaries(
                retained_diag
            ),
            replay_value=_ordered_hashes_from_phaseb_downstream_selected_summaries(
                replay_flow
            ),
            note=(
                "retained side reconstructs ordered Phase-B downstream identities "
                "from persisted phaseC_candidate_pool_rows filtered to phaseA_selected; "
                "replay side uses persisted phaseB_downstream_selected_summaries when present"
            ),
        ),
        _build_surface_comparison(
            surface_name="phaseB_topk_saved_count",
            retained_value=_safe_int(retained_diag.get("phaseB_topk_saved_count")),
            replay_value=_safe_int(replay_flow.get("phaseB_topk_saved_count")),
            note="persisted count",
        ),
        _build_surface_comparison(
            surface_name="phaseB_topk_saved_ordered_hashes",
            retained_value=_ordered_candidate_hashes(retained_phaseb_topk_saved_summaries),
            replay_value=_ordered_candidate_hashes(replay_phaseb_topk_saved_summaries),
            note=(
                "retained side reconstructed from saved stage3_topk rows; replay side "
                "uses saved summaries when present, else saved stage3_topk_payload"
            ),
        ),
        _build_surface_comparison(
            surface_name="phaseC_candidate_pool_source_counts",
            retained_value=dict(retained_diag.get("phaseC_candidate_pool_source_counts", {}) or {}),
            replay_value=dict(replay_flow.get("phaseC_candidate_pool_source_counts", {}) or {}),
            note="persisted source counts",
        ),
        _build_surface_comparison(
            surface_name="phaseC_start_source_counts",
            retained_value=dict(retained_diag.get("phaseC_start_source_counts", {}) or {}),
            replay_value=dict(replay_flow.get("phaseC_start_source_counts", {}) or {}),
            note="persisted source counts",
        ),
        _build_surface_comparison(
            surface_name="phaseC_start_ordered_identities",
            retained_value=retained_phasec_start_rows,
            replay_value=replay_phasec_start_rows,
            note="ordered identities built from persisted phaseC_start_summaries",
        ),
    ]

    first_mismatch_surface = _first_surface_by_status(surface_rows, status="mismatch")
    first_unavailable_surface = _first_surface_by_status(
        surface_rows,
        status="unavailable",
    )
    ordered_identity_contract_rows = _ordered_identity_contract_rows(surface_rows)
    return {
        "run_label": str(RUN_LABEL),
        "fixture_seed": _safe_int(retained_artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(retained_artifact.get("search_seed")),
        "surface_rows": list(surface_rows),
        "ordered_identity_contract_rows": ordered_identity_contract_rows,
        "ordered_identity_contract_all_match": int(
            1
            if ordered_identity_contract_rows
            and all(
                _safe_str(row.get("status")) == "match"
                for row in ordered_identity_contract_rows
            )
            else 0
        ),
        "first_actual_mismatch_surface": str(first_mismatch_surface),
        "first_unavailable_surface": str(first_unavailable_surface),
        "retained_phaseb_topk_saved_summaries": retained_phaseb_topk_saved_summaries,
        "replay_phaseb_topk_saved_summaries": replay_phaseb_topk_saved_summaries,
        "retained_phasec_start_identities": retained_phasec_start_rows,
        "replay_phasec_start_identities": replay_phasec_start_rows,
    }


def write_replay_fidelity_markdown(
    output_dir: Path,
    *,
    retained_artifact_relpath: str,
    replay_bundle_relpath: str,
    replay_stage3_flow_relpath: str,
    summary: Mapping[str, Any],
) -> None:
    lines = [
        "# Candidate 3 Exact Control Replay-Fidelity Audit: 1511 / search7004",
        "",
        "Question:",
        "- along the exact control lane that already completed, where does replay drift first appear relative to the frozen retained case?",
        "",
        "Inputs:",
        f"- retained artifact: `{retained_artifact_relpath}`",
        f"- replay bundle: `{replay_bundle_relpath}`",
        f"- replay flow: `{replay_stage3_flow_relpath}`",
        "",
        "Surface walk in pipeline order:",
    ]
    for row in list(summary.get("surface_rows", []) or []):
        lines.append(
            f"- `{row.get('surface_name')}`: `{row.get('status')}`"
        )
        retained_value = json.dumps(row.get("retained_value"), sort_keys=True)
        replay_value = json.dumps(row.get("replay_value"), sort_keys=True)
        lines.append(f"  retained: `{retained_value}`")
        lines.append(f"  replay: `{replay_value}`")
        note = _safe_str(row.get("note"))
        if note:
            lines.append(f"  note: {note}")
    lines.extend(
        [
            "",
            "Key read:",
            (
                f"- first unavailable surface: "
                f"`{summary.get('first_unavailable_surface') or 'none'}`"
            ),
        (
            f"- first actual mismatch: "
            f"`{summary.get('first_actual_mismatch_surface') or 'none'}`"
        ),
        (
            "- ordered-identity replay contract satisfied: "
            f"`{int(summary.get('ordered_identity_contract_all_match', 0) or 0)}`"
        ),
        "",
        "Interpretation:",
        "- the strongest frozen retained identity comparison currently available on this case now starts one step earlier than before",
        "- ordered Phase-B downstream selected identities can be reconstructed on the retained side from persisted phaseC_candidate_pool_rows filtered to phaseA_selected",
        "- on this rerun the first actual mismatch is already at ordered Phase-B downstream identities, before the saved Phase-B top-k and Phase-C start surfaces",
        ]
    )
    (output_dir / "replay_fidelity_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_audit() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    retained_artifact_path = REPO_ROOT / RETAINED_ARTIFACT_REL_PATH
    replay_bundle_path = REPO_ROOT / REPLAY_BUNDLE_REL_PATH
    replay_stage3_flow_path = replay_bundle_path / "resume_bundle" / "stage3_flow.json"

    retained_artifact = _load_json(retained_artifact_path)
    replay_flow = _load_json(replay_stage3_flow_path)

    summary = build_replay_fidelity_summary(
        retained_artifact=retained_artifact,
        replay_flow=replay_flow,
    )
    summary = {
        **summary,
        "retained_artifact_relpath": _relative_path(retained_artifact_path),
        "replay_bundle_relpath": _relative_path(replay_bundle_path),
        "replay_stage3_flow_relpath": _relative_path(replay_stage3_flow_path),
    }
    _write_json(output_dir / "replay_fidelity_summary.json", summary)
    _write_json(output_dir / "surface_rows.json", summary["surface_rows"])
    write_replay_fidelity_markdown(
        output_dir,
        retained_artifact_relpath=summary["retained_artifact_relpath"],
        replay_bundle_relpath=summary["replay_bundle_relpath"],
        replay_stage3_flow_relpath=summary["replay_stage3_flow_relpath"],
        summary=summary,
    )
    run_summary = {
        "output_dir": _relative_path(output_dir),
        "fixture_seed": _safe_int(summary.get("fixture_seed")),
        "search_seed": _safe_int(summary.get("search_seed")),
        "first_unavailable_surface": _safe_str(summary.get("first_unavailable_surface")),
        "first_actual_mismatch_surface": _safe_str(
            summary.get("first_actual_mismatch_surface")
        ),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_audit(), sort_keys=True))


if __name__ == "__main__":
    main()
