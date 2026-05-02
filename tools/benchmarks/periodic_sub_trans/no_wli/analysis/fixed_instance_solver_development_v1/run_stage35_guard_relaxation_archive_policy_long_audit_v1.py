from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage35_guard_relaxation_archive_policy_long_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()

RUN_LABEL = "stage35_guard_relaxation_archive_policy_long_audit_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
NO_WLI_OUTPUT_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli"
MAX_WALLCLOCK_SECONDS = 8 * 60 * 60
PROGRESS_EVERY_SOURCES = 5
PARTIAL_WRITE_EVERY_SOURCES = 5
MAX_BEST_INSTANCE_SOURCES = 100000
MAX_STAGE35_SUMMARY_SOURCES = 100000
SEARCH_RELAXATION_BANDS = [0.0, -0.005, -0.01, -0.025, -0.05, -0.1]
SCORE_MIN_GAINS = [0.0]


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(result):
        return float(default)
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _truth_match(plaintext_idx: Any, target_plaintext_idx: Any) -> float:
    pt = [int(x) for x in list(plaintext_idx or [])]
    target = [int(x) for x in list(target_plaintext_idx or [])]
    if not pt or not target:
        return 0.0
    count = min(len(pt), len(target))
    if count <= 0:
        return 0.0
    same = sum(1 for idx in range(count) if int(pt[idx]) == int(target[idx]))
    return float(same / len(target))


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _fixture_search_from_path(path: Path) -> tuple[int, int]:
    text = _repo_rel(path)
    fixture_match = re.search(r"seed(\d+)", text)
    search_match = re.search(r"search(\d+)", text)
    fixture_seed = int(fixture_match.group(1)) if fixture_match else 0
    search_seed = int(search_match.group(1)) if search_match else 0
    return fixture_seed, search_seed


def discover_sources() -> list[dict[str, Any]]:
    best_sources: list[dict[str, Any]] = []
    stage35_sources: list[dict[str, Any]] = []
    for path in NO_WLI_OUTPUT_ROOT.rglob("best_instance.json"):
        best_sources.append({"source_type": "best_instance", "path": path})
        if len(best_sources) >= MAX_BEST_INSTANCE_SOURCES:
            break
    for path in NO_WLI_OUTPUT_ROOT.rglob("stage35_summary.json"):
        stage35_sources.append({"source_type": "stage35_summary", "path": path})
        if len(stage35_sources) >= MAX_STAGE35_SUMMARY_SOURCES:
            break
    sources = best_sources + stage35_sources
    sources.sort(key=lambda item: _repo_rel(Path(item["path"])))
    return sources


def _candidate_payload_for_stage35_summary(path: Path) -> dict[str, Any]:
    summary_path = path.parent / "summary.json"
    if summary_path.exists():
        try:
            return _read_json(summary_path)
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _artifact_for_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    relpath = str(payload.get("artifact_relpath", "") or "")
    if not relpath:
        return {}
    path = REPO_ROOT / relpath
    if not path.exists():
        return {}
    try:
        return _read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}


def _source_case(
    *,
    source_type: str,
    path: Path,
    payload: Mapping[str, Any],
    artifact: Mapping[str, Any],
    stage35: Mapping[str, Any],
) -> dict[str, Any]:
    fixture_seed, search_seed = _fixture_search_from_path(path)
    fixture_seed = _safe_int(
        artifact.get("instance_source_key_seed", payload.get("fixture_seed", fixture_seed)),
        fixture_seed,
    )
    search_seed = _safe_int(artifact.get("search_seed", payload.get("search_seed", search_seed)), search_seed)
    return {
        "source_type": source_type,
        "source_relpath": _repo_rel(path),
        "fixture_seed": fixture_seed,
        "search_seed": search_seed,
        "target_plaintext_idx": artifact.get("target_plaintext_idx", []) or [],
        "retained_best_match_ratio": _safe_float(artifact.get("best_match_ratio")),
        "stage35_selected": _safe_int(stage35.get("selected", artifact.get("stage35_selected", 0))),
        "stage35_accept_reason": str(
            stage35.get("accept_reason", artifact.get("stage35_accept_reason", "")) or ""
        ),
    }


def _baseline_from_stage35_summary(
    *,
    payload: Mapping[str, Any],
    stage35: Mapping[str, Any],
    target_plaintext_idx: Any,
) -> dict[str, Any]:
    baseline_score = _safe_float(stage35.get("baseline_score"))
    baseline_search_score = _safe_float(stage35.get("baseline_search_score"))
    selected_match = _safe_float(payload.get("selected_candidate_final_match"))
    if selected_match <= 0.0:
        selected_match = _truth_match(
            stage35.get("baseline_plaintext_idx", []),
            target_plaintext_idx,
        )
    return {
        "baseline_score": baseline_score,
        "baseline_search_score": baseline_search_score,
        "selected_match": selected_match,
        "baseline_candidate_hash": str(
            stage35.get("baseline_candidate_hash", payload.get("selected_candidate_hash", "")) or ""
        ),
    }


def _baseline_from_best_instance(
    *,
    artifact: Mapping[str, Any],
    target_plaintext_idx: Any,
) -> dict[str, Any]:
    seed_rows = list(artifact.get("stage35_seed_rows", []) or [])
    baseline = dict(seed_rows[0]) if seed_rows else {}
    baseline_score = _safe_float(baseline.get("score"))
    baseline_search_score = _safe_float(baseline.get("search_score"))
    baseline_pt = baseline.get("plaintext_idx", []) or artifact.get("final_best_plaintext_idx", [])
    selected_match = _truth_match(baseline_pt, target_plaintext_idx)
    if selected_match <= 0.0:
        selected_match = _safe_float(artifact.get("best_match_ratio"))
    return {
        "baseline_score": baseline_score,
        "baseline_search_score": baseline_search_score,
        "selected_match": selected_match,
        "baseline_candidate_hash": str(baseline.get("candidate_hash", "") or ""),
    }


def _iter_archive_rows(
    *,
    source_type: str,
    artifact: Mapping[str, Any],
    stage35: Mapping[str, Any],
) -> Iterable[Mapping[str, Any]]:
    if source_type == "best_instance":
        return list(artifact.get("stage35_archive", []) or [])
    return list(stage35.get("archive_rows", []) or [])


def _process_source(source: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = Path(source["path"])
    source_type = str(source["source_type"])
    payload: dict[str, Any] = {}
    artifact: dict[str, Any] = {}
    stage35: dict[str, Any] = {}
    if source_type == "best_instance":
        artifact = _read_json(path)
        stage35 = {
            "selected": artifact.get("stage35_selected", 0),
            "accept_reason": artifact.get("stage35_accept_reason", ""),
        }
    else:
        stage35 = _read_json(path)
        payload = _candidate_payload_for_stage35_summary(path)
        artifact = _artifact_for_payload(payload)
    case = _source_case(
        source_type=source_type,
        path=path,
        payload=payload,
        artifact=artifact,
        stage35=stage35,
    )
    target_plaintext = case["target_plaintext_idx"]
    if not target_plaintext:
        return [], dict(case, skipped=1, skip_reason="missing_target_plaintext")
    archive_rows = list(
        _iter_archive_rows(source_type=source_type, artifact=artifact, stage35=stage35)
    )
    if not archive_rows:
        return [], dict(case, skipped=1, skip_reason="missing_archive_rows")

    if source_type == "best_instance":
        baseline = _baseline_from_best_instance(
            artifact=artifact,
            target_plaintext_idx=target_plaintext,
        )
    else:
        baseline = _baseline_from_stage35_summary(
            payload=payload,
            stage35=stage35,
            target_plaintext_idx=target_plaintext,
        )
    selected_match = _safe_float(baseline.get("selected_match"))
    baseline_score = _safe_float(baseline.get("baseline_score"))
    baseline_search_score = _safe_float(baseline.get("baseline_search_score"))

    rows: list[dict[str, Any]] = []
    for raw_row in archive_rows:
        row = dict(raw_row)
        truth = _truth_match(row.get("plaintext_idx", []), target_plaintext)
        score = _safe_float(row.get("score"))
        search_score = _safe_float(row.get("search_score"))
        score_delta = score - baseline_score
        search_delta = search_score - baseline_search_score
        truth_delta = truth - selected_match
        non_noop = int(abs(score_delta) > 1e-12 or abs(search_delta) > 1e-12)
        rows.append(
            {
                "source_type": source_type,
                "source_relpath": case["source_relpath"],
                "fixture_seed": case["fixture_seed"],
                "search_seed": case["search_seed"],
                "stage35_selected": case["stage35_selected"],
                "stage35_accept_reason": case["stage35_accept_reason"],
                "retained_best_match_ratio": round(
                    float(case["retained_best_match_ratio"]), 6
                ),
                "selected_match": round(float(selected_match), 6),
                "baseline_score": round(float(baseline_score), 12),
                "baseline_search_score": round(float(baseline_search_score), 12),
                "baseline_candidate_hash": str(
                    baseline.get("baseline_candidate_hash", "") or ""
                ),
                "archive_rank": _safe_int(row.get("archive_rank")),
                "candidate_hash": str(row.get("candidate_hash", "") or ""),
                "truth_match": round(float(truth), 6),
                "truth_delta_vs_selected": round(float(truth_delta), 6),
                "score": round(float(score), 12),
                "score_delta_vs_baseline": round(float(score_delta), 12),
                "search_score": round(float(search_score), 12),
                "search_delta_vs_baseline": round(float(search_delta), 12),
                "strict_guard_passing": int(score_delta >= 0.0 and search_delta >= 0.0),
                "non_noop": non_noop,
                "truth_positive": int(truth_delta > 0.0),
                "truth_negative": int(truth_delta < 0.0),
                "search_score_failing": int(search_delta < 0.0),
                "blocked_truth_positive": int(
                    truth_delta > 0.0 and score_delta >= 0.0 and search_delta < 0.0
                ),
                "lane": str(row.get("lane", "") or ""),
                "seed_source": str(row.get("seed_source", "") or ""),
                "stage3_source": str(row.get("stage3_source", "") or ""),
                "move_type": str(row.get("move_type", "") or ""),
                "target_slice": row.get("target_slice", ""),
            }
        )

    best_truth = max(rows, key=lambda item: float(item["truth_match"]))
    case_summary = dict(
        case,
        skipped=0,
        skip_reason="",
        archive_rows=len(rows),
        strict_guard_passing_non_noop_rows=sum(
            1
            for row in rows
            if int(row["strict_guard_passing"]) == 1 and int(row["non_noop"]) == 1
        ),
        truth_positive_rows=sum(1 for row in rows if int(row["truth_positive"]) == 1),
        blocked_truth_positive_rows=sum(
            1 for row in rows if int(row["blocked_truth_positive"]) == 1
        ),
        best_truth_archive_rank=int(best_truth["archive_rank"]),
        best_truth_candidate_hash=str(best_truth["candidate_hash"]),
        best_truth_match=float(best_truth["truth_match"]),
        best_truth_delta_vs_selected=float(best_truth["truth_delta_vs_selected"]),
        best_truth_search_delta_vs_baseline=float(
            best_truth["search_delta_vs_baseline"]
        ),
    )
    case_summary.pop("target_plaintext_idx", None)
    return rows, case_summary


def _select_for_policy(rows: list[dict[str, Any]], *, score_min_gain: float, search_floor: float) -> dict[str, Any] | None:
    passing = [
        row
        for row in rows
        if int(row["non_noop"]) == 1
        and float(row["score_delta_vs_baseline"]) >= float(score_min_gain)
        and float(row["search_delta_vs_baseline"]) >= float(search_floor)
    ]
    if not passing:
        return None
    return sorted(
        passing,
        key=lambda row: (
            -float(row["score_delta_vs_baseline"]),
            -float(row["search_delta_vs_baseline"]),
            int(row["archive_rank"]),
        ),
    )[0]


def build_policy_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in case_rows:
        by_source.setdefault(str(row["source_relpath"]), []).append(row)
    policy_rows: list[dict[str, Any]] = []
    for source_relpath, rows in by_source.items():
        first = rows[0]
        for score_min_gain in SCORE_MIN_GAINS:
            for search_floor in SEARCH_RELAXATION_BANDS:
                selected = _select_for_policy(
                    rows,
                    score_min_gain=score_min_gain,
                    search_floor=search_floor,
                )
                if selected is None:
                    policy_rows.append(
                        {
                            "source_relpath": source_relpath,
                            "source_type": first["source_type"],
                            "fixture_seed": first["fixture_seed"],
                            "search_seed": first["search_seed"],
                            "score_min_gain": score_min_gain,
                            "search_delta_floor": search_floor,
                            "selected": 0,
                            "archive_rank": 0,
                            "candidate_hash": "",
                            "truth_delta_vs_selected": 0.0,
                            "score_delta_vs_baseline": 0.0,
                            "search_delta_vs_baseline": 0.0,
                            "truth_positive": 0,
                            "truth_negative": 0,
                        }
                    )
                else:
                    policy_rows.append(
                        {
                            "source_relpath": source_relpath,
                            "source_type": first["source_type"],
                            "fixture_seed": first["fixture_seed"],
                            "search_seed": first["search_seed"],
                            "score_min_gain": score_min_gain,
                            "search_delta_floor": search_floor,
                            "selected": 1,
                            "archive_rank": selected["archive_rank"],
                            "candidate_hash": selected["candidate_hash"],
                            "truth_delta_vs_selected": selected[
                                "truth_delta_vs_selected"
                            ],
                            "score_delta_vs_baseline": selected[
                                "score_delta_vs_baseline"
                            ],
                            "search_delta_vs_baseline": selected[
                                "search_delta_vs_baseline"
                            ],
                            "truth_positive": selected["truth_positive"],
                            "truth_negative": selected["truth_negative"],
                        }
                    )
    return policy_rows


def summarize_policies(policy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[float, float], list[dict[str, Any]]] = {}
    for row in policy_rows:
        key = (float(row["score_min_gain"]), float(row["search_delta_floor"]))
        grouped.setdefault(key, []).append(row)
    summaries: list[dict[str, Any]] = []
    for (score_min_gain, search_floor), rows in sorted(grouped.items()):
        selected_rows = [row for row in rows if int(row["selected"]) == 1]
        truth_deltas = [float(row["truth_delta_vs_selected"]) for row in selected_rows]
        summaries.append(
            {
                "score_min_gain": score_min_gain,
                "search_delta_floor": search_floor,
                "sources": len(rows),
                "selected_sources": len(selected_rows),
                "truth_positive_selected": sum(
                    1 for row in selected_rows if int(row["truth_positive"]) == 1
                ),
                "truth_negative_selected": sum(
                    1 for row in selected_rows if int(row["truth_negative"]) == 1
                ),
                "mean_truth_delta": round(
                    sum(truth_deltas) / len(truth_deltas) if truth_deltas else 0.0,
                    6,
                ),
                "max_truth_delta": round(max(truth_deltas) if truth_deltas else 0.0, 6),
                "min_truth_delta": round(min(truth_deltas) if truth_deltas else 0.0, 6),
            }
        )
    return summaries


def write_outputs(
    *,
    output_dir: Path,
    all_rows: list[dict[str, Any]],
    case_summaries: list[dict[str, Any]],
    skipped_summaries: list[dict[str, Any]],
    completed_sources: int,
    total_sources: int,
    status: str,
    started: float,
) -> None:
    policy_rows = build_policy_rows(all_rows)
    policy_summary_rows = summarize_policies(policy_rows)
    _write_csv(output_dir / "stage35_guard_relaxation_archive_rows.csv", all_rows)
    _write_csv(output_dir / "stage35_guard_relaxation_case_summary_rows.csv", case_summaries)
    _write_csv(output_dir / "stage35_guard_relaxation_skipped_sources.csv", skipped_summaries)
    _write_csv(output_dir / "stage35_guard_relaxation_policy_selection_rows.csv", policy_rows)
    _write_csv(output_dir / "stage35_guard_relaxation_policy_summary_rows.csv", policy_summary_rows)
    elapsed = float(time.perf_counter() - started)
    summary = {
        "run_label": RUN_LABEL,
        "status": status,
        "output_dir": _repo_rel(output_dir),
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "completed_sources": completed_sources,
        "total_sources": total_sources,
        "coverage": (
            float(completed_sources / total_sources) if int(total_sources) > 0 else 0.0
        ),
        "archive_rows": len(all_rows),
        "case_summaries": len(case_summaries),
        "skipped_sources": len(skipped_summaries),
        "sources_with_blocked_truth_positive_rows": sum(
            1
            for row in case_summaries
            if int(row.get("blocked_truth_positive_rows", 0) or 0) > 0
        ),
        "elapsed_seconds": elapsed,
        "updated_utc": _utc_now_text(),
        "recommended_next": (
            "analyze_policy_summary_then_choose_guard_relaxation_or_close_before_runtime"
        ),
    }
    _write_json(output_dir / "stage35_guard_relaxation_summary.json", summary)
    readout = build_readout(
        summary=summary,
        policy_summary_rows=policy_summary_rows,
    )
    (output_dir / "stage35_guard_relaxation_readout.md").write_text(
        readout,
        encoding="utf-8",
    )


def build_readout(
    *,
    summary: Mapping[str, Any],
    policy_summary_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# Stage35 Guard-Relaxation Archive Policy Long Audit v1",
        "",
        "Question:",
        "",
        "- across retained Stage 3.5 archive surfaces, does relaxing the search-score",
        "  guard recover truth-positive rows, and how often does it admit truth-negative",
        "  rows?",
        "",
        "Run budget:",
        "",
        f"- max wallclock seconds: `{MAX_WALLCLOCK_SECONDS}`",
        "- stop condition: all discovered sources processed or wallclock budget reached",
        "",
        "Coverage:",
        "",
        f"- status: `{summary['status']}`",
        f"- completed sources: `{summary['completed_sources']} / {summary['total_sources']}`",
        f"- archive rows: `{summary['archive_rows']}`",
        f"- skipped sources: `{summary['skipped_sources']}`",
        f"- sources with blocked truth-positive rows: `{summary['sources_with_blocked_truth_positive_rows']}`",
        "",
        "Policy Summary:",
        "",
        "| search delta floor | selected sources | truth positive | truth negative | mean truth delta | min truth delta | max truth delta |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in policy_summary_rows:
        lines.append(
            "| "
            f"`{float(row['search_delta_floor']):+.3f}` | "
            f"`{row['selected_sources']}` | "
            f"`{row['truth_positive_selected']}` | "
            f"`{row['truth_negative_selected']}` | "
            f"`{float(row['mean_truth_delta']):+.6f}` | "
            f"`{float(row['min_truth_delta']):+.6f}` | "
            f"`{float(row['max_truth_delta']):+.6f}` |"
        )
    lines.extend(
        [
            "",
            "Recommended Next:",
            "",
            "- analyze `stage35_guard_relaxation_policy_summary_rows.csv` before any",
            "  additional runtime",
            "- prefer a policy that recovers blocked truth-positive rows only if it keeps",
            "  truth-negative selections acceptably rare",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_audit() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    sources = discover_sources()
    total_sources = len(sources)
    print(
        json.dumps(
            {
                "event": "start",
                "run_label": RUN_LABEL,
                "output_dir": _repo_rel(output_dir),
                "total_sources": total_sources,
                "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
                "utc": _utc_now_text(),
            },
            sort_keys=True,
        ),
        flush=True,
    )

    started = time.perf_counter()
    all_rows: list[dict[str, Any]] = []
    case_summaries: list[dict[str, Any]] = []
    skipped_summaries: list[dict[str, Any]] = []
    completed_sources = 0
    status = "completed"
    for index, source in enumerate(sources, start=1):
        elapsed = float(time.perf_counter() - started)
        if elapsed >= MAX_WALLCLOCK_SECONDS:
            status = "wallclock_budget_reached"
            break
        try:
            rows, case_summary = _process_source(source)
        except Exception as exc:  # noqa: BLE001 - extraction must be salvageable.
            path = Path(source["path"])
            case_summary = {
                "source_type": str(source["source_type"]),
                "source_relpath": _repo_rel(path),
                "fixture_seed": 0,
                "search_seed": 0,
                "skipped": 1,
                "skip_reason": f"{type(exc).__name__}: {exc}",
            }
            rows = []
        if rows:
            all_rows.extend(rows)
            case_summaries.append(case_summary)
        else:
            skipped_summaries.append(case_summary)
        completed_sources = index
        if (
            completed_sources % PARTIAL_WRITE_EVERY_SOURCES == 0
            or completed_sources == total_sources
        ):
            write_outputs(
                output_dir=output_dir,
                all_rows=all_rows,
                case_summaries=case_summaries,
                skipped_summaries=skipped_summaries,
                completed_sources=completed_sources,
                total_sources=total_sources,
                status="partial" if completed_sources < total_sources else status,
                started=started,
            )
        if (
            completed_sources % PROGRESS_EVERY_SOURCES == 0
            or completed_sources == total_sources
        ):
            elapsed = float(time.perf_counter() - started)
            rate = float(completed_sources / elapsed) if elapsed > 0 else 0.0
            remaining = max(total_sources - completed_sources, 0)
            eta_seconds = float(remaining / rate) if rate > 0 else 0.0
            print(
                json.dumps(
                    {
                        "event": "progress",
                        "completed_sources": completed_sources,
                        "total_sources": total_sources,
                        "archive_rows": len(all_rows),
                        "elapsed_seconds": round(elapsed, 3),
                        "eta_seconds": round(eta_seconds, 3),
                        "utc": _utc_now_text(),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    write_outputs(
        output_dir=output_dir,
        all_rows=all_rows,
        case_summaries=case_summaries,
        skipped_summaries=skipped_summaries,
        completed_sources=completed_sources,
        total_sources=total_sources,
        status=status,
        started=started,
    )
    final_summary = _read_json(output_dir / "stage35_guard_relaxation_summary.json")
    print(json.dumps(dict(final_summary, event="finish"), sort_keys=True), flush=True)
    return final_summary


def main() -> None:
    run_audit()


if __name__ == "__main__":
    main()
