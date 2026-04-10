from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.iteration_identity import (
    build_proven_solved_key_from_row,
)


def derive_outcome_code(*, status: Any, stop_reason: Any) -> str:
    s = str(status or "").strip().lower()
    r = str(stop_reason or "").strip().lower()
    if s == "skipped_proven" or ("autoskip_proven" in r):
        return "skipped_proven"
    if s == "solved":
        return "solved"
    if "time_cap" in r:
        return "time_cap"
    if "stage2_cap" in r:
        return "stage2_cap"
    if "weak_stage2" in r:
        return "weak_stage2"
    if s == "stalled" or "stalled_no_improve" in r:
        return "stalled_stage3"
    if s in {"error", "crash"}:
        return "crash"
    return "unsolved"


def build_summary(
    *,
    tiers: Sequence[Any],
    instances: Sequence[Dict[str, Any]],
    solve_match_threshold: float,
    derive_outcome_code_fn: Callable[..., str],
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"tiers": {}}
    for t in tiers:
        rs = [r for r in instances if str(r["tier"]) == str(t.name)]
        if not rs:
            continue
        arr = np.asarray([float(r["best_match_ratio"]) for r in rs], dtype=np.float64)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            continue
        outcome_counts: Dict[str, int] = {}
        for row in rs:
            code = str(row["outcome_code"])
            outcome_counts[code] = int(outcome_counts.get(code, 0) + 1)
        summary["tiers"][str(t.name)] = dict(
            n=int(len(rs)),
            solved_rate=float(np.mean(arr >= float(solve_match_threshold))),
            best_match_p50=float(np.percentile(arr, 50)),
            best_match_p90=float(np.percentile(arr, 90)),
            outcome_counts={str(k): int(v) for k, v in sorted(outcome_counts.items(), key=lambda kv: kv[0])},
        )
    return summary


def load_proven_solved_index(path: Path, *, min_match: float) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
    out: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    if not path.exists():
        return out
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("status", "")).strip().lower() != "solved":
                    continue
                try:
                    best_match = float(str(row.get("best_match_ratio", "nan")).strip())
                except Exception:
                    best_match = float("nan")
                if not np.isfinite(best_match) or best_match < float(min_match):
                    continue
                ts = str(row.get("timestamp_utc", "")).strip()
                try:
                    key = build_proven_solved_key_from_row(row)
                except Exception:
                    continue
                prev = out.get(key)
                if (prev is None) or (ts >= str(prev.get("timestamp_utc", ""))):
                    out[key] = dict(
                        timestamp_utc=ts,
                        run_id=str(row.get("run_id", "")).strip(),
                        instance_input_mode=str(
                            row.get("instance_input_mode", "generated") or "generated"
                        ),
                        instance_fixture_id=str(
                            row.get("instance_fixture_id", "") or ""
                        ).strip(),
                        instance_source_key_seed=str(
                            row.get("instance_source_key_seed", "")
                        ).strip(),
                        search_seed=str(row.get("search_seed", "")).strip(),
                        best_match_ratio=float(best_match),
                        best_stage=str(row.get("best_stage", "")).strip(),
                        total_seconds=str(row.get("total_seconds", "")).strip(),
                        total_evals=str(row.get("total_evals", "")).strip(),
                    )
    except Exception:
        return {}
    return out
