from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]


# =============================================================================
# Config block (IDE-friendly; no CLI)
# =============================================================================

# Point at either a merged run directory OR a merged zip.
# (If both are set, ZIP wins.)
MERGED_ZIP_PATH: Path | None = None
MERGED_RUN_ROOT: Path = Path("output/tools/benchmarks/scoring/span_hamming_nose_suite_merged")
MERGED_RUN_DIR: Path | None = None  # e.g. Path("output/.../__span_hamming_nose_suite_merged")

# Output folder for the generated assets (safe default: under output/).
OUTPUT_ASSET_ROOT: Path = Path("output/tools/benchmarks/scoring/span_hamming_nose_assets_v1")

# Which generator defines the negative baseline distribution.
NEG_GENERATOR: str = "RAND_UNIGRAM"  # or "SHUFFLE_UNIGRAM"

# ECDF mesh size: larger = smoother interpolation, still small files.
Q_KNOTS: int = 2049

# Span scope label for asset naming/metadata.
# This builder scores full sampled text spans (no LM-style winN windowing in these assets).
SPAN_SCOPE_LABEL: str = "fulltext"

# If True, rebuild OUTPUT_ASSET_ROOT from scratch.
CLEAN_OUTPUT_DIR: bool = True

# Metrics:
WRITE_METRICS: bool = True
BOOTSTRAP_ROUNDS: int = 300  # set 0 to disable CI
BOOTSTRAP_ALPHA: float = 0.05  # 95% CI


# =============================================================================
# Helpers
# =============================================================================

@dataclass(frozen=True)
class BucketKey:
    direction: str
    length_bucket: int


@dataclass(frozen=True)
class SampleRow:
    direction: str
    length_bucket: int
    generator: str
    span_raw: float
    char1_score: float
    char2_score: float
    char3_score: float
    char4_score: float


@dataclass(frozen=True)
class CalibRefs:
    real_ref: float
    neg_ref: float
    denom: float
    n_real: int
    n_neg: int

    @property
    def valid(self) -> bool:
        return bool(self.denom > 0.0)


def _group_rows(
    rows: list[SampleRow],
) -> dict[tuple[str, int, str], list[SampleRow]]:
    grouped: dict[tuple[str, int, str], list[SampleRow]] = {}
    for row in rows:
        key = (row.direction, int(row.length_bucket), row.generator)
        bucket = grouped.get(key)
        if bucket is None:
            bucket = []
            grouped[key] = bucket
        bucket.append(row)
    return grouped


def _resolve_repo_path(path_like: Path | str | None) -> Path | None:
    if path_like is None:
        return None
    p = Path(path_like).expanduser()
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _load_run_dir() -> Path:
    if MERGED_ZIP_PATH is not None:
        zfp = _resolve_repo_path(MERGED_ZIP_PATH)
        assert zfp is not None
        if not zfp.exists():
            raise FileNotFoundError(f"MERGED_ZIP_PATH not found: {zfp}")

        extract_root = zfp.parent / f"_{zfp.stem}__extract"
        if extract_root.exists():
            shutil.rmtree(extract_root)
        extract_root.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zfp, "r") as z:
            z.extractall(extract_root)

        dirs = [p for p in extract_root.iterdir() if p.is_dir()]
        if len(dirs) != 1:
            raise ValueError(f"Expected exactly one folder in zip extract, found {len(dirs)}")
        return dirs[0].resolve()

    if MERGED_RUN_DIR is not None:
        run_dir = _resolve_repo_path(MERGED_RUN_DIR)
        assert run_dir is not None
        if not run_dir.exists():
            raise FileNotFoundError(f"MERGED_RUN_DIR not found: {run_dir}")
        return run_dir

    run_root = _resolve_repo_path(MERGED_RUN_ROOT)
    assert run_root is not None
    if not run_root.exists():
        raise FileNotFoundError(f"MERGED_RUN_ROOT not found: {run_root}")
    candidates = [
        p for p in run_root.iterdir() if p.is_dir() and "__span_hamming_nose_suite_merged" in p.name
    ]
    if not candidates:
        raise FileNotFoundError(f"No merged run directories found under: {run_root}")
    return sorted(candidates, key=lambda p: p.name)[-1].resolve()


def _read_samples(run_dir: Path) -> list[SampleRow]:
    fp = run_dir / "samples.csv"
    if not fp.exists():
        raise FileNotFoundError(f"Missing samples.csv: {fp}")

    rows: list[SampleRow] = []
    with fp.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "direction",
            "length_bucket",
            "generator",
            "span_raw",
            "char1_score",
            "char2_score",
            "char3_score",
            "char4_score",
        }
        fields = set(reader.fieldnames or [])
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"samples.csv missing required columns: {', '.join(missing)}")
        for row in reader:
            try:
                rows.append(
                    SampleRow(
                        direction=str(row.get("direction", "")).strip().lower(),
                        length_bucket=int(row.get("length_bucket", 0)),
                        generator=str(row.get("generator", "")).strip().upper(),
                        span_raw=float(row.get("span_raw", "nan")),
                        char1_score=float(row.get("char1_score", "nan")),
                        char2_score=float(row.get("char2_score", "nan")),
                        char3_score=float(row.get("char3_score", "nan")),
                        char4_score=float(row.get("char4_score", "nan")),
                    )
                )
            except Exception:
                continue
    return rows


def _read_run_config(run_dir: Path) -> dict[str, Any]:
    fp = run_dir / "run_config.json"
    if not fp.exists():
        return {}
    return json.loads(fp.read_text(encoding="utf-8"))


def _bucket_keys(rows: list[SampleRow]) -> list[BucketKey]:
    keys = []
    for (d, lb) in sorted({(r.direction, r.length_bucket) for r in rows}):
        keys.append(BucketKey(direction=str(d), length_bucket=int(lb)))
    return keys


def _median_refs(values_real: np.ndarray, values_neg: np.ndarray) -> CalibRefs:
    real = np.asarray(values_real, dtype=np.float64)
    neg = np.asarray(values_neg, dtype=np.float64)
    real = real[np.isfinite(real)]
    neg = neg[np.isfinite(neg)]

    real_ref = float(np.median(real)) if real.size else 0.0
    neg_ref = float(np.median(neg)) if neg.size else 0.0
    denom = float(real_ref - neg_ref)

    return CalibRefs(
        real_ref=real_ref,
        neg_ref=neg_ref,
        denom=denom,
        n_real=int(real.size),
        n_neg=int(neg.size),
    )


def _q_mesh(knots: int) -> np.ndarray:
    if int(knots) < 8:
        raise ValueError("Q_KNOTS must be >= 8")
    q = np.linspace(0.0, 1.0, int(knots), dtype=np.float64)
    if q.size > 1 and not bool(np.all(np.diff(q) > 0.0)):
        raise ValueError("q mesh must be strictly increasing")
    return q


def _enforce_strict_increasing(grid: np.ndarray) -> np.ndarray:
    g = np.asarray(grid, dtype=np.float64).copy()
    for i in range(1, g.size):
        if not (g[i] > g[i - 1]):
            g[i] = np.nextafter(g[i - 1], np.float64(np.inf))
    if g.size > 1 and not bool(np.all(np.diff(g) > 0.0)):
        raise ValueError("Failed to enforce strict grid monotonicity")
    return g


def _auc_binary(pos_scores: np.ndarray, neg_scores: np.ndarray) -> float:
    pos = np.asarray(pos_scores, dtype=np.float64)
    neg = np.asarray(neg_scores, dtype=np.float64)
    pos = pos[np.isfinite(pos)]
    neg = neg[np.isfinite(neg)]
    if pos.size == 0 or neg.size == 0:
        return float("nan")

    # Mann-Whitney AUC with average ranks for ties.
    scores = np.concatenate([pos, neg])
    labels = np.concatenate([np.ones(pos.size, dtype=np.int8), np.zeros(neg.size, dtype=np.int8)])

    order = np.argsort(scores, kind="mergesort")  # stable/deterministic
    scores_sorted = scores[order]
    labels_sorted = labels[order]

    # Average ranks for ties.
    ranks = np.empty(scores_sorted.size, dtype=np.float64)
    i = 0
    r = 1.0
    while i < scores_sorted.size:
        j = i + 1
        while j < scores_sorted.size and scores_sorted[j] == scores_sorted[i]:
            j += 1
        r_avg = 0.5 * (r + (r + (j - i) - 1))
        ranks[i:j] = r_avg
        r += (j - i)
        i = j

    n_pos = float(pos.size)
    n_neg = float(neg.size)
    sum_ranks_pos = float(ranks[labels_sorted == 1].sum())
    auc = (sum_ranks_pos - n_pos * (n_pos + 1.0) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _bootstrap_auc(
    rng: np.random.Generator,
    pos: np.ndarray,
    neg: np.ndarray,
    rounds: int,
    alpha: float,
) -> tuple[float, float]:
    pos = np.asarray(pos, dtype=np.float64)
    neg = np.asarray(neg, dtype=np.float64)
    pos = pos[np.isfinite(pos)]
    neg = neg[np.isfinite(neg)]
    if pos.size == 0 or neg.size == 0 or rounds <= 0:
        return (float("nan"), float("nan"))

    aucs = np.empty(int(rounds), dtype=np.float64)
    for i in range(int(rounds)):
        pos_s = pos[rng.integers(0, pos.size, size=pos.size)]
        neg_s = neg[rng.integers(0, neg.size, size=neg.size)]
        aucs[i] = _auc_binary(pos_s, neg_s)

    lo = float(np.quantile(aucs, alpha / 2.0))
    hi = float(np.quantile(aucs, 1.0 - alpha / 2.0))
    return (lo, hi)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _char_scores(rows: list[SampleRow], n: int) -> np.ndarray:
    if int(n) == 1:
        return np.asarray([r.char1_score for r in rows], dtype=np.float64)
    if int(n) == 2:
        return np.asarray([r.char2_score for r in rows], dtype=np.float64)
    if int(n) == 3:
        return np.asarray([r.char3_score for r in rows], dtype=np.float64)
    if int(n) == 4:
        return np.asarray([r.char4_score for r in rows], dtype=np.float64)
    raise ValueError(f"Unsupported char n: {n}")


# =============================================================================
# Build
# =============================================================================

def build_assets() -> None:
    run_dir = _load_run_dir()
    rows = _read_samples(run_dir)
    run_cfg = _read_run_config(run_dir)
    grouped = _group_rows(rows)
    bucket_keys = _bucket_keys(rows)

    neg = str(NEG_GENERATOR).strip().upper()
    if neg not in {r.generator for r in rows}:
        raise ValueError(f"NEG_GENERATOR={neg} not present in samples.csv generators")

    out_root = _resolve_repo_path(OUTPUT_ASSET_ROOT)
    assert out_root is not None
    if CLEAN_OUTPUT_DIR and out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # ---------- Combined calibration ----------
    cal_rows: list[dict[str, Any]] = []
    for key in bucket_keys:
        sub_real = grouped.get((key.direction, int(key.length_bucket), "REAL"), [])
        sub_neg = grouped.get((key.direction, int(key.length_bucket), neg), [])

        span_refs = _median_refs(
            np.asarray([r.span_raw for r in sub_real], dtype=np.float64),
            np.asarray([r.span_raw for r in sub_neg], dtype=np.float64),
        )
        char_refs = {
            int(n): _median_refs(
                _char_scores(sub_real, int(n)),
                _char_scores(sub_neg, int(n)),
            )
            for n in (1, 2, 3, 4)
        }

        row = {
            "direction": key.direction,
            "length_bucket": key.length_bucket,

            "span_real_ref": span_refs.real_ref,
            "span_neg_ref": span_refs.neg_ref,
            "span_denom": span_refs.denom,
            "span_n_real": span_refs.n_real,
            "span_n_neg": span_refs.n_neg,
            "span_valid": bool(span_refs.valid),
        }
        for n in (1, 2, 3, 4):
            refs = char_refs[int(n)]
            row[f"char{n}_real_ref"] = refs.real_ref
            row[f"char{n}_neg_ref"] = refs.neg_ref
            row[f"char{n}_denom"] = refs.denom
            row[f"char{n}_n_real"] = refs.n_real
            row[f"char{n}_n_neg"] = refs.n_neg
            row[f"char{n}_valid"] = bool(refs.valid)

        cal_rows.append(row)

    provenance = {
        "suite_version": run_cfg.get("suite_version"),
        "global_seed": run_cfg.get("global_seed"),
        "corpus_list_hash": run_cfg.get("corpus_list_hash"),
        "created_at_utc": run_cfg.get("created_at_utc"),
    }
    run_cfg_bytes = json.dumps(run_cfg, sort_keys=True, separators=(",", ":")).encode("utf-8")

    combined_cal = {
        "version": "v1",
        "asset_kind": "span_hamming_nose_combined_calibration",
        "source_run_dir": str(run_dir),
        "neg_generator": neg,
        "span_scope_label": str(SPAN_SCOPE_LABEL),
        "provenance": provenance,
        "source_run_config_sha256": _sha256_bytes(run_cfg_bytes),
        "notes": {
            "span_x_formula": "x_span = (span_raw - span_neg_ref) / span_denom  (unclamped)",
            "char_norm_formula": "charN_norm = clamp((charN_score - charN_neg_ref) / charN_denom, 0, 1)",
            "span_norm_formula": "span_norm = clamp((span_raw - span_neg_ref) / span_denom, 0, 1)",
        },
        "rows": cal_rows,
    }
    (out_root / "combined_calibration.json").write_text(
        json.dumps(combined_cal, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # ---------- Span-x ECDF assets ----------
    q = _q_mesh(Q_KNOTS)
    ecdf_dir = out_root / "ecdf" / "span_x"
    ecdf_dir.mkdir(parents=True, exist_ok=True)

    # Index calibration rows for quick lookup.
    cal_by_bucket: dict[tuple[str, int], dict[str, Any]] = {
        (r["direction"], int(r["length_bucket"])): r for r in cal_rows
    }

    ecdf_audit: list[dict[str, Any]] = []
    for key in bucket_keys:
        row = cal_by_bucket[(key.direction, key.length_bucket)]
        if not bool(row["span_valid"]):
            continue

        denom = float(row["span_denom"])
        neg_ref = float(row["span_neg_ref"])

        sub_neg = grouped.get((key.direction, int(key.length_bucket), neg), [])
        x = (
            np.asarray([r.span_raw for r in sub_neg], dtype=np.float64) - neg_ref
        ) / denom
        x = x[np.isfinite(x)]
        if x.size < 50:
            raise ValueError(f"Too few NEG samples for ECDF: direction={key.direction} lb={key.length_bucket} n={x.size}")

        try:
            grid = np.quantile(x, q, method="linear")
        except TypeError:
            grid = np.quantile(x, q, interpolation="linear")

        grid = _enforce_strict_increasing(np.asarray(grid, dtype=np.float64))

        meta = {
            "version": "v1",
            "kind": "ecdf",
            "model": "span",
            "stat": "x_span",
            "direction": key.direction,
            "length_bucket": int(key.length_bucket),
            "neg_generator": neg,
            "neg_samples": int(x.size),
            "mesh": {"kind": "linear", "num_knots": int(Q_KNOTS)},
            "strict_increasing": {"enforce": True, "method": "nextafter"},
            "source_run": run_dir.name,
        }
        meta_json = json.dumps(meta, sort_keys=True, separators=(",", ":"))

        out_fp = ecdf_dir / f"{key.direction}_nose_span_lb{key.length_bucket}_{SPAN_SCOPE_LABEL}_x_span.npz"
        np.savez(
            out_fp,
            grid=grid.astype(np.float64),
            q=q.astype(np.float64),
            meta_json=np.array(meta_json, dtype=np.str_),  # no object dtype / no pickle
        )

        ecdf_audit.append(
            {
                "path": str(out_fp.relative_to(out_root)).replace("\\", "/"),
                "grid_min": float(grid[0]),
                "grid_max": float(grid[-1]),
                "meta_sha256": _sha256_bytes(meta_json.encode("utf-8")),
            }
        )

    (out_root / "ecdf_audit.json").write_text(
        json.dumps({"version": "v1", "files": ecdf_audit}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # ---------- Metrics (AUC + optional bootstrap CI) ----------
    if WRITE_METRICS:
        global_seed = int(run_cfg.get("global_seed", 0))
        metrics_rows: list[dict[str, Any]] = []

        for key in bucket_keys:
            sub_real = grouped.get((key.direction, int(key.length_bucket), "REAL"), [])
            sub_neg = grouped.get((key.direction, int(key.length_bucket), neg), [])
            span_real = np.asarray([r.span_raw for r in sub_real], dtype=np.float64)
            span_neg = np.asarray([r.span_raw for r in sub_neg], dtype=np.float64)
            char_real = {
                int(n): _char_scores(sub_real, int(n))
                for n in (1, 2, 3, 4)
            }
            char_neg = {
                int(n): _char_scores(sub_neg, int(n))
                for n in (1, 2, 3, 4)
            }

            # Span raw AUC.
            auc_span_raw = _auc_binary(span_real, span_neg)

            auc_char = {
                int(n): _auc_binary(char_real[int(n)], char_neg[int(n)])
                for n in (1, 2, 3, 4)
            }

            row = {
                "direction": key.direction,
                "length_bucket": int(key.length_bucket),
                "neg_generator": neg,
                "n_real": int(len(span_real)),
                "n_neg": int(len(span_neg)),
                "auc_span_raw": float(auc_span_raw),
                "auc_char1": float(auc_char[1]),
                "auc_char2": float(auc_char[2]),
                "auc_char3": float(auc_char[3]),
                "auc_char4": float(auc_char[4]),
            }

            if BOOTSTRAP_ROUNDS > 0:
                # Deterministic per-bucket seed derivation.
                seed = (global_seed * 1315423911 + key.length_bucket * 2654435761 + (1 if key.direction == "ltr" else 2)) & 0xFFFFFFFF
                rng = np.random.default_rng(seed)

                lo, hi = _bootstrap_auc(
                    rng,
                    span_real,
                    span_neg,
                    rounds=int(BOOTSTRAP_ROUNDS),
                    alpha=float(BOOTSTRAP_ALPHA),
                )
                row["auc_span_raw_ci"] = [float(lo), float(hi)]

                for n in (1, 2, 3, 4):
                    lo, hi = _bootstrap_auc(
                        rng,
                        char_real[int(n)],
                        char_neg[int(n)],
                        rounds=int(BOOTSTRAP_ROUNDS),
                        alpha=float(BOOTSTRAP_ALPHA),
                    )
                    row[f"auc_char{n}_ci"] = [float(lo), float(hi)]

            metrics_rows.append(row)

        metrics = {
            "version": "v1",
            "asset_kind": "span_hamming_nose_metrics",
            "source_run_dir": str(run_dir),
            "neg_generator": neg,
            "provenance": provenance,
            "source_run_config_sha256": _sha256_bytes(run_cfg_bytes),
            "bootstrap_rounds": int(BOOTSTRAP_ROUNDS),
            "bootstrap_alpha": float(BOOTSTRAP_ALPHA),
            "rows": metrics_rows,
        }
        (out_root / "metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(f"[assets] wrote: {out_root}")


if __name__ == "__main__":
    build_assets()
