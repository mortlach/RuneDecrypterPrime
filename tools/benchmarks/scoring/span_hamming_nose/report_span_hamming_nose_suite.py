from __future__ import annotations

import csv
import json
import math
from array import array
from pathlib import Path
from typing import Any
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]

RUN_DIR_OVERRIDE: str | None = None
RUN_ROOTS = [
    Path("output/tools/benchmarks/scoring/span_hamming_nose_suite_merged"),
    Path("output/tools/benchmarks/scoring/span_hamming_nose_suite"),
]
WRITE_REPORT_FILE = False
REPORT_OUTPUT_PATH = Path("output/tools/benchmarks/scoring/span_hamming_nose_suite/report_latest.txt")


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _resolve_repo_path(path_like: Path | str | None) -> Path | None:
    if path_like is None:
        return None
    p = Path(path_like).expanduser()
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _rankdata_average(values: list[float]) -> list[float]:
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i + 1
        v = values[order[i]]
        while j < n and values[order[j]] == v:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = avg_rank
        i = j
    return ranks


def _auc_from_scores(pos: list[float], neg: list[float]) -> float | None:
    n_pos = len(pos)
    n_neg = len(neg)
    if n_pos == 0 or n_neg == 0:
        return None
    joined = pos + neg
    ranks = _rankdata_average(joined)
    sum_pos = sum(ranks[:n_pos])
    auc = (sum_pos - (n_pos * (n_pos + 1) / 2.0)) / (n_pos * n_neg)
    if not math.isfinite(auc):
        return None
    return float(auc)


def _fraction_at(values: list[float], target: float, tol: float = 1e-12) -> float | None:
    if not values:
        return None
    n = len(values)
    hit = sum(1 for v in values if abs(v - target) <= tol)
    return float(hit) / float(n)


def _quantile_safe(values: list[float], q: float) -> float | None:
    if not values:
        return None
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return None
    return float(np.quantile(arr, float(q)))


def _collect_samples(run_dir: Path, calibrations: dict[tuple[str, int], dict[str, Any]]) -> dict[tuple[str, int, str], dict[str, array]]:
    samples_csv = run_dir / "samples.csv"
    grouped: dict[tuple[str, int, str], dict[str, array]] = {}
    if not samples_csv.exists():
        return grouped
    with samples_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            direction = str(row.get("direction", "")).strip().lower()
            lb_raw = row.get("length_bucket")
            generator = str(row.get("generator", "")).strip().upper()
            if not direction or not lb_raw or not generator:
                continue
            try:
                length_bucket = int(lb_raw)
            except ValueError:
                continue
            key = (direction, length_bucket, generator)
            bucket = grouped.get(key)
            if bucket is None:
                bucket = {
                    "span_raw": array("d"),
                    "span_norm": array("d"),
                    "char1": array("d"),
                    "char2": array("d"),
                    "char3": array("d"),
                    "char4": array("d"),
                }
                grouped[key] = bucket
            span_raw = _safe_float(row.get("span_raw"))
            if span_raw is not None:
                bucket["span_raw"].append(span_raw)
                cal = calibrations.get((direction, length_bucket))
                if cal is not None:
                    denom = _safe_float(cal.get("denom"))
                    rand_ref = _safe_float(cal.get("rand_ref"))
                    if denom is not None and rand_ref is not None and denom > 0.0:
                        span_norm = (span_raw - rand_ref) / denom
                        if span_norm < 0.0:
                            span_norm = 0.0
                        elif span_norm > 1.0:
                            span_norm = 1.0
                        bucket["span_norm"].append(float(span_norm))
            char1 = _safe_float(row.get("char1_score"))
            if char1 is not None:
                bucket["char1"].append(char1)
            char2 = _safe_float(row.get("char2_score"))
            if char2 is not None:
                bucket["char2"].append(char2)
            char3 = _safe_float(row.get("char3_score"))
            if char3 is not None:
                bucket["char3"].append(char3)
            char4 = _safe_float(row.get("char4_score"))
            if char4 is not None:
                bucket["char4"].append(char4)
    return grouped


def build_report(run_dir: Path) -> str:
    calibration_path = run_dir / "calibration.json"
    summary_path = run_dir / "summary.csv"
    run_cfg_path = run_dir / "run_config.json"
    samples_path = run_dir / "samples.csv"
    if not calibration_path.exists():
        raise FileNotFoundError(f"Missing calibration file: {calibration_path}")
    payload = json.loads(calibration_path.read_text(encoding="utf-8"))
    calibrations = list(payload.get("calibrations", []))
    calibration_by_bucket: dict[tuple[str, int], dict[str, Any]] = {}
    for row in calibrations:
        direction = str(row.get("direction", "")).strip().lower()
        try:
            length_bucket = int(row.get("length_bucket", -1))
        except (TypeError, ValueError):
            continue
        if direction and length_bucket > 0:
            calibration_by_bucket[(direction, length_bucket)] = row

    run_cfg = {}
    if run_cfg_path.exists():
        try:
            run_cfg = json.loads(run_cfg_path.read_text(encoding="utf-8"))
        except Exception:
            run_cfg = {}

    grouped = _collect_samples(run_dir=run_dir, calibrations=calibration_by_bucket)
    stable = []
    for row in calibrations:
        if "unstable" in row:
            if not bool(row.get("unstable", True)):
                stable.append(row)
            continue
        if bool(row.get("span_norm_valid", False)):
            stable.append(row)

    lines = []
    lines.append(f"run_dir={run_dir}")
    if run_cfg:
        lines.append(
            "run_meta suite_version={suite} seed={seed} shard={idx}/{count}".format(
                suite=str(run_cfg.get("suite_version", "unknown")),
                seed=str(run_cfg.get("global_seed", "unknown")),
                idx=str(run_cfg.get("shard_index", "0")),
                count=str(run_cfg.get("shard_count", "1")),
            )
        )
    lines.append(f"calibration_rows={len(calibrations)}")
    lines.append(f"stable_rows={len(stable)}")
    lines.append(f"summary_csv_exists={summary_path.exists()}")
    lines.append(f"samples_csv_exists={samples_path.exists()}")
    for row in sorted(stable, key=lambda item: (item.get("direction", ""), int(item.get("length_bucket", 0)))):
        direction = str(row.get("direction", "")).strip().lower()
        length_bucket = int(row.get("length_bucket", 0))
        real = grouped.get((direction, length_bucket, "REAL"), {})
        rand = grouped.get((direction, length_bucket, "RAND_UNIGRAM"), {})
        shuffle = grouped.get((direction, length_bucket, "SHUFFLE_UNIGRAM"), {})
        real_span = list(real.get("span_raw", []))
        rand_span = list(rand.get("span_raw", []))
        shuffle_span = list(shuffle.get("span_raw", []))
        real_norm = list(real.get("span_norm", []))
        rand_norm = list(rand.get("span_norm", []))
        shuffle_norm = list(shuffle.get("span_norm", []))
        real_char1 = list(real.get("char1", []))
        rand_char1 = list(rand.get("char1", []))
        shuffle_char1 = list(shuffle.get("char1", []))
        real_char2 = list(real.get("char2", []))
        rand_char2 = list(rand.get("char2", []))
        shuffle_char2 = list(shuffle.get("char2", []))
        real_char3 = list(real.get("char3", []))
        rand_char3 = list(rand.get("char3", []))
        shuffle_char3 = list(shuffle.get("char3", []))
        real_char4 = list(real.get("char4", []))
        rand_char4 = list(rand.get("char4", []))
        shuffle_char4 = list(shuffle.get("char4", []))

        auc_span_rand = _auc_from_scores(real_span, rand_span)
        auc_span_shuffle = _auc_from_scores(real_span, shuffle_span)
        auc_norm_rand = _auc_from_scores(real_norm, rand_norm)
        auc_norm_shuffle = _auc_from_scores(real_norm, shuffle_norm)
        auc_char1_rand = _auc_from_scores(real_char1, rand_char1)
        auc_char1_shuffle = _auc_from_scores(real_char1, shuffle_char1)
        auc_char2_rand = _auc_from_scores(real_char2, rand_char2)
        auc_char2_shuffle = _auc_from_scores(real_char2, shuffle_char2)
        auc_char3_rand = _auc_from_scores(real_char3, rand_char3)
        auc_char3_shuffle = _auc_from_scores(real_char3, shuffle_char3)
        auc_char4_rand = _auc_from_scores(real_char4, rand_char4)
        auc_char4_shuffle = _auc_from_scores(real_char4, shuffle_char4)
        real_sat0 = _fraction_at(real_norm, 0.0)
        real_sat1 = _fraction_at(real_norm, 1.0)
        rand_sat0 = _fraction_at(rand_norm, 0.0)
        rand_sat1 = _fraction_at(rand_norm, 1.0)
        shuffle_sat0 = _fraction_at(shuffle_norm, 0.0)
        shuffle_sat1 = _fraction_at(shuffle_norm, 1.0)
        q999_span_real = _quantile_safe(real_span, 0.999)
        q999_span_rand = _quantile_safe(rand_span, 0.999)
        q999_span_shuffle = _quantile_safe(shuffle_span, 0.999)
        q999_char4_real = _quantile_safe(real_char4, 0.999)
        q999_char4_rand = _quantile_safe(rand_char4, 0.999)
        q999_char4_shuffle = _quantile_safe(shuffle_char4, 0.999)
        q999_char1_real = _quantile_safe(real_char1, 0.999)
        q999_char1_rand = _quantile_safe(rand_char1, 0.999)
        q999_char1_shuffle = _quantile_safe(shuffle_char1, 0.999)
        q999_char2_real = _quantile_safe(real_char2, 0.999)
        q999_char2_rand = _quantile_safe(rand_char2, 0.999)
        q999_char2_shuffle = _quantile_safe(shuffle_char2, 0.999)
        q999_char3_real = _quantile_safe(real_char3, 0.999)
        q999_char3_rand = _quantile_safe(rand_char3, 0.999)
        q999_char3_shuffle = _quantile_safe(shuffle_char3, 0.999)

        def _fmt(v: float | None) -> str:
            return "n/a" if v is None else f"{v:.4f}"

        lines.append(
            "stable direction={direction} length={length_bucket} denom={denom:.6f} "
            "n_real={n_real} n_rand={n_rand} n_shuffle={n_shuffle} "
            "auc_span_r={auc_sr} auc_span_s={auc_ss} "
            "auc_norm_r={auc_nr} auc_norm_s={auc_ns} "
            "auc_char1_r={auc_c1r} auc_char1_s={auc_c1s} "
            "auc_char2_r={auc_c2r} auc_char2_s={auc_c2s} "
            "auc_char3_r={auc_c3r} auc_char3_s={auc_c3s} "
            "auc_char4_r={auc_cr} auc_char4_s={auc_cs} "
            "sat_real_0={sat_r0} sat_real_1={sat_r1} "
            "sat_rand_0={sat_n0} sat_rand_1={sat_n1} "
            "sat_shuffle_0={sat_s0} sat_shuffle_1={sat_s1} "
            "q999_span_real={qsr} q999_span_rand={qsn} q999_span_shuffle={qss} "
            "q999_char1_real={q1r} q999_char1_rand={q1n} q999_char1_shuffle={q1s} "
            "q999_char2_real={q2r} q999_char2_rand={q2n} q999_char2_shuffle={q2s} "
            "q999_char3_real={q3r} q999_char3_rand={q3n} q999_char3_shuffle={q3s} "
            "q999_char4_real={qcr} q999_char4_rand={qcn} q999_char4_shuffle={qcs}".format(
                direction=direction,
                length_bucket=length_bucket,
                denom=float(row.get("denom", 0.0)),
                n_real=len(real_span),
                n_rand=len(rand_span),
                n_shuffle=len(shuffle_span),
                auc_sr=_fmt(auc_span_rand),
                auc_ss=_fmt(auc_span_shuffle),
                auc_nr=_fmt(auc_norm_rand),
                auc_ns=_fmt(auc_norm_shuffle),
                auc_c1r=_fmt(auc_char1_rand),
                auc_c1s=_fmt(auc_char1_shuffle),
                auc_c2r=_fmt(auc_char2_rand),
                auc_c2s=_fmt(auc_char2_shuffle),
                auc_c3r=_fmt(auc_char3_rand),
                auc_c3s=_fmt(auc_char3_shuffle),
                auc_cr=_fmt(auc_char4_rand),
                auc_cs=_fmt(auc_char4_shuffle),
                sat_r0=_fmt(real_sat0),
                sat_r1=_fmt(real_sat1),
                sat_n0=_fmt(rand_sat0),
                sat_n1=_fmt(rand_sat1),
                sat_s0=_fmt(shuffle_sat0),
                sat_s1=_fmt(shuffle_sat1),
                qsr=_fmt(q999_span_real),
                qsn=_fmt(q999_span_rand),
                qss=_fmt(q999_span_shuffle),
                q1r=_fmt(q999_char1_real),
                q1n=_fmt(q999_char1_rand),
                q1s=_fmt(q999_char1_shuffle),
                q2r=_fmt(q999_char2_real),
                q2n=_fmt(q999_char2_rand),
                q2s=_fmt(q999_char2_shuffle),
                q3r=_fmt(q999_char3_real),
                q3n=_fmt(q999_char3_rand),
                q3s=_fmt(q999_char3_shuffle),
                qcr=_fmt(q999_char4_real),
                qcn=_fmt(q999_char4_rand),
                qcs=_fmt(q999_char4_shuffle),
            )
        )
    return "\n".join(lines)


def _resolve_latest_run_dir(roots: list[Path]) -> Path:
    if not roots:
        raise ValueError("roots must be non-empty")

    primary = roots[0]
    primary_candidates: list[Path] = []
    if primary.exists():
        for p in primary.iterdir():
            if p.is_dir() and "__span_hamming_nose_suite" in p.name:
                primary_candidates.append(p)
    if primary_candidates:
        return sorted(primary_candidates, key=lambda p: p.name)[-1]

    fallback_candidates: list[Path] = []
    for root in roots[1:]:
        if not root.exists():
            continue
        for p in root.iterdir():
            if p.is_dir() and "__span_hamming_nose_suite" in p.name:
                fallback_candidates.append(p)
    if not fallback_candidates:
        raise FileNotFoundError(
            "No suite runs found under roots: " + ", ".join(str(r.resolve()) for r in roots)
        )
    return sorted(fallback_candidates, key=lambda p: p.name)[-1]


def main() -> int:
    if RUN_DIR_OVERRIDE is not None:
        run_dir = _resolve_repo_path(RUN_DIR_OVERRIDE)
        assert run_dir is not None
    else:
        roots: list[Path] = []
        for p in RUN_ROOTS:
            rp = _resolve_repo_path(p)
            if rp is not None:
                roots.append(rp)
        run_dir = _resolve_latest_run_dir(roots)
    report = build_report(run_dir)
    print(report)
    if WRITE_REPORT_FILE:
        out_path = _resolve_repo_path(REPORT_OUTPUT_PATH)
        assert out_path is not None
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
