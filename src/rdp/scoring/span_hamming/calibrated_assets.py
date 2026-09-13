from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
from rdp.core.hamming_dictionary_policy import ensure_hamming_dictionary_policy


def _decode_meta_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, np.ndarray):
        if raw.shape == ():
            raw = raw.item()
        elif raw.size == 1:
            raw = raw.reshape(()).item()
    if isinstance(raw, (bytes, bytearray)):
        text = bytes(raw).decode("utf-8")
    elif isinstance(raw, str):
        text = raw
    else:
        raise ValueError("meta_json must be a UTF-8 string or bytes")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("meta_json must decode to a JSON object")
    return parsed


def _ensure_strict_increasing(values: np.ndarray, label: str) -> None:
    if values.ndim != 1:
        raise ValueError(f"{label} must be 1D")
    if values.size < 2:
        raise ValueError(f"{label} must contain at least 2 points")
    if not bool(np.all(np.diff(values) > 0.0)):
        raise ValueError(f"{label} must be strictly increasing")


@dataclass(frozen=True)
class SpanCalibrationRow:
    direction: str
    length_bucket: int
    span_neg_ref: float
    span_denom: float
    span_valid: bool
    char4_neg_ref: float | None
    char4_denom: float | None
    char4_valid: bool | None


@dataclass(frozen=True)
class SpanBucketScore:
    direction: str
    length_bucket: int
    x_span: float
    span_pct: float
    span_energy: float
    span_neg_ref: float
    span_denom: float


class SpanCalibratedAssets:
    """
    Dedicated loader/validator for phase-2 calibrated span assets.

    Contract:
      - combined_calibration.json with rows keyed by (direction, length_bucket)
      - ecdf/span_x/*.npz with grid/q/meta_json where meta carries the same key
    """

    def __init__(
        self,
        calibration_rows: Dict[Tuple[str, int], SpanCalibrationRow],
        ecdf_rows: Dict[Tuple[str, int], Tuple[np.ndarray, np.ndarray]],
        *,
        dictionary_policy: str | None = None,
    ) -> None:
        if not calibration_rows:
            raise ValueError("No calibration rows loaded")
        self._calibration_rows = calibration_rows
        self._ecdf_rows = ecdf_rows
        self.dictionary_policy = dictionary_policy
        by_dir: Dict[str, set[int]] = {}
        for direction, length_bucket in self._calibration_rows:
            by_dir.setdefault(direction, set()).add(length_bucket)
        self._length_buckets_by_direction: Dict[str, Tuple[int, ...]] = {
            direction: tuple(sorted(lengths))
            for direction, lengths in by_dir.items()
        }

    @classmethod
    def load(cls, assets_dir: str | Path) -> "SpanCalibratedAssets":
        root = Path(assets_dir).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"span_hamming_assets_dir not found: {root}")

        cal_fp = root / "combined_calibration.json"
        if not cal_fp.exists():
            raise FileNotFoundError(f"Missing calibration file: {cal_fp}")
        cal_raw = json.loads(cal_fp.read_text(encoding="utf-8"))
        if not isinstance(cal_raw, dict):
            raise ValueError("combined_calibration.json must be an object")
        cal_rows_raw = cal_raw.get("rows")
        if not isinstance(cal_rows_raw, list):
            raise ValueError("combined_calibration.json must contain list field 'rows'")

        dictionary_policy = None
        raw_policy = cal_raw.get("dictionary_policy", cal_raw.get("hamming_dictionary_policy"))
        if raw_policy is not None:
            dictionary_policy = ensure_hamming_dictionary_policy(raw_policy).value

        calibration_rows: Dict[Tuple[str, int], SpanCalibrationRow] = {}
        for row in cal_rows_raw:
            if not isinstance(row, dict):
                continue
            direction = str(row.get("direction", "")).strip().lower()
            length_bucket = int(row.get("length_bucket", -1))
            key = (direction, length_bucket)
            if not direction or length_bucket < 1:
                continue
            if key in calibration_rows:
                raise ValueError(f"Duplicate calibration bucket: {key}")
            span_neg_ref = float(row.get("span_neg_ref", 0.0))
            span_denom = float(row.get("span_denom", 0.0))
            span_valid = bool(row.get("span_valid", False))
            calibration_rows[key] = SpanCalibrationRow(
                direction=direction,
                length_bucket=length_bucket,
                span_neg_ref=span_neg_ref,
                span_denom=span_denom,
                span_valid=span_valid,
                char4_neg_ref=(
                    None if row.get("char4_neg_ref") is None else float(row.get("char4_neg_ref"))
                ),
                char4_denom=(
                    None if row.get("char4_denom") is None else float(row.get("char4_denom"))
                ),
                char4_valid=(
                    None if row.get("char4_valid") is None else bool(row.get("char4_valid"))
                ),
            )

        ecdf_dir = root / "ecdf" / "span_x"
        if not ecdf_dir.exists():
            raise FileNotFoundError(f"Missing span ECDF directory: {ecdf_dir}")

        ecdf_rows: Dict[Tuple[str, int], Tuple[np.ndarray, np.ndarray]] = {}
        files = sorted(ecdf_dir.glob("*.npz"))
        if not files:
            raise FileNotFoundError(f"No span ECDF files found under: {ecdf_dir}")
        for fp in files:
            arr = np.load(fp, allow_pickle=True)
            if "grid" not in arr or "q" not in arr or "meta_json" not in arr:
                raise ValueError(f"Span ECDF file missing required arrays: {fp}")
            grid = np.asarray(arr["grid"], dtype=np.float64)
            q = np.asarray(arr["q"], dtype=np.float64)
            meta = _decode_meta_json(arr["meta_json"])
            if str(meta.get("model", "")).strip().lower() != "span":
                raise ValueError(f"Span ECDF meta model must be 'span': {fp}")
            if str(meta.get("stat", "")).strip().lower() != "x_span":
                raise ValueError(f"Span ECDF meta stat must be 'x_span': {fp}")
            direction = str(meta.get("direction", "")).strip().lower()
            length_bucket = int(meta.get("length_bucket", -1))
            key = (direction, length_bucket)
            if key in ecdf_rows:
                raise ValueError(f"Duplicate span ECDF bucket: {key}")
            if key not in calibration_rows:
                raise ValueError(f"ECDF bucket has no calibration row: {key}")
            _ensure_strict_increasing(grid, f"grid ({fp.name})")
            _ensure_strict_increasing(q, f"q ({fp.name})")
            if grid.size != q.size:
                raise ValueError(f"grid/q size mismatch: {fp}")
            if not (0.0 <= float(q[0]) < float(q[-1]) <= 1.0):
                raise ValueError(f"q range must be within [0,1] and increasing: {fp}")
            ecdf_rows[key] = (grid, q)

        # Require ECDF presence for every valid span bucket.
        for key, row in calibration_rows.items():
            if row.span_valid and row.span_denom > 0.0 and key not in ecdf_rows:
                raise ValueError(f"Missing span ECDF for valid calibration bucket: {key}")

        return cls(
            calibration_rows=calibration_rows,
            ecdf_rows=ecdf_rows,
            dictionary_policy=dictionary_policy,
        )

    def available_directions(self) -> Tuple[str, ...]:
        return tuple(sorted(self._length_buckets_by_direction))

    def length_buckets(self, direction: str) -> Tuple[int, ...]:
        dir_norm = str(direction).strip().lower()
        if dir_norm not in self._length_buckets_by_direction:
            raise KeyError(f"No buckets for direction={dir_norm}")
        return self._length_buckets_by_direction[dir_norm]

    def select_bucket(self, direction: str, text_length: int) -> int:
        dir_norm = str(direction).strip().lower()
        L = int(text_length)
        if L < 1:
            raise ValueError("text_length must be >= 1")
        buckets = self.length_buckets(dir_norm)
        # nearest; tie-break to smaller bucket
        return min(buckets, key=lambda b: (abs(b - L), b))

    def score_span_raw(
        self,
        *,
        direction: str,
        text_length: int,
        span_raw: float,
        clamp_min: float,
        clamp_max: float,
    ) -> SpanBucketScore:
        dir_norm = str(direction).strip().lower()
        if not (0.0 < float(clamp_min) < float(clamp_max) < 1.0):
            raise ValueError("clamp_min/clamp_max must satisfy 0 < min < max < 1")
        bucket = self.select_bucket(dir_norm, int(text_length))
        return self.score_span_raw_in_bucket(
            direction=dir_norm,
            length_bucket=int(bucket),
            span_raw=span_raw,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )

    def score_span_raw_in_bucket(
        self,
        *,
        direction: str,
        length_bucket: int,
        span_raw: float,
        clamp_min: float,
        clamp_max: float,
    ) -> SpanBucketScore:
        dir_norm = str(direction).strip().lower()
        if not (0.0 < float(clamp_min) < float(clamp_max) < 1.0):
            raise ValueError("clamp_min/clamp_max must satisfy 0 < min < max < 1")
        bucket = int(length_bucket)
        key = (dir_norm, bucket)
        if key not in self._calibration_rows:
            raise KeyError(f"No calibration bucket for direction={dir_norm}, length_bucket={bucket}")
        row = self._calibration_rows[key]
        if not row.span_valid or not (row.span_denom > 0.0):
            raise ValueError(f"Invalid span calibration bucket: {key}")
        grid, q = self._ecdf_rows[key]
        x_span = (float(span_raw) - row.span_neg_ref) / row.span_denom
        span_pct = float(np.interp(x_span, grid, q, left=float(q[0]), right=float(q[-1])))
        span_pct = float(np.clip(span_pct, float(clamp_min), float(clamp_max)))
        span_energy = float(-np.log1p(-span_pct))
        return SpanBucketScore(
            direction=dir_norm,
            length_bucket=int(bucket),
            x_span=float(x_span),
            span_pct=span_pct,
            span_energy=span_energy,
            span_neg_ref=float(row.span_neg_ref),
            span_denom=float(row.span_denom),
        )


__all__ = [
    "SpanCalibratedAssets",
    "SpanCalibrationRow",
    "SpanBucketScore",
]

