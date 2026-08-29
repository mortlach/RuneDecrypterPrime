from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.scoring.span_hamming.ecdf_interp import (
    clamp_pct,
    fix_strict_increasing_breakpoints,
    interp_pct,
    pct_to_energy,
)


def _normalise_profile(vec: Sequence[float]) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("profile vector must be 1D")
    total = float(np.sum(arr))
    if total <= 0.0:
        return np.zeros_like(arr, dtype=np.float64)
    return arr / total


def _l1_distance(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        raise ValueError("profile vectors must have same shape")
    return float(np.sum(np.abs(a - b)))


@dataclass(frozen=True)
class LmBucketScore:
    direction: str
    length_bucket: int
    profile_source: str
    profile_margin_l1_raw: float
    profile_margin_l1_pct_noise: float
    profile_margin_l1_energy: float
    profile_margin_l1_pct_real: float | None
    mean_bin_index_raw: float
    mean_bin_index_pct_noise: float
    mean_bin_index_energy: float
    mean_bin_index_pct_real: float | None
    mean_bin_length_raw: float
    mean_bin_length_pct_noise: float
    mean_bin_length_energy: float
    mean_bin_length_pct_real: float | None
    tail_mass_raw: float
    tail_mass_pct_noise: float
    tail_mass_energy: float
    tail_mass_pct_real: float | None


@dataclass(frozen=True)
class _BucketTable:
    direction: str
    length_bucket: int
    source_measure: str
    real_mean_profile: np.ndarray
    noise_mean_profile: np.ndarray
    margin_noise_breakpoints: np.ndarray
    margin_noise_q: np.ndarray
    margin_real_breakpoints: np.ndarray | None
    margin_real_q: np.ndarray | None
    mean_index_noise_breakpoints: np.ndarray
    mean_index_noise_q: np.ndarray
    mean_index_real_breakpoints: np.ndarray | None
    mean_index_real_q: np.ndarray | None
    mean_length_noise_breakpoints: np.ndarray
    mean_length_noise_q: np.ndarray
    mean_length_real_breakpoints: np.ndarray | None
    mean_length_real_q: np.ndarray | None
    tail_mass_noise_by_start_index: Dict[int, Tuple[np.ndarray, np.ndarray]]
    tail_mass_real_by_start_index: Dict[int, Tuple[np.ndarray, np.ndarray]]


def _load_scalar_ecdf(
    node: Dict[str, Any],
    *,
    feature_name: str,
    required: bool,
) -> Tuple[np.ndarray, np.ndarray] | Tuple[None, None]:
    if not isinstance(node, dict):
        if required:
            raise ValueError(f"Missing ecdf for feature={feature_name}")
        return None, None
    q = np.asarray(node.get("quantile_grid", []), dtype=np.float64)
    bp_raw = np.asarray(node.get("breakpoints", []), dtype=np.float64)
    if q.size < 2 or bp_raw.size != q.size:
        if required:
            raise ValueError(f"Invalid ecdf for feature={feature_name}")
        return None, None
    return fix_strict_increasing_breakpoints(bp_raw), q


def _interp_clamped_pct(
    raw_value: float,
    breakpoints: np.ndarray | None,
    q: np.ndarray | None,
    *,
    clamp_min: float,
    clamp_max: float,
) -> float | None:
    if breakpoints is None or q is None:
        return None
    pct = interp_pct(raw_value, breakpoints, q)
    return float(clamp_pct(pct, clamp_min, clamp_max))


class SpanHammingLmAssetsV2:
    def __init__(
        self,
        *,
        profile_vector_length: int,
        profile_length_bins: Tuple[int, ...],
        tables: Dict[Tuple[str, int, str], _BucketTable],
    ) -> None:
        if profile_vector_length < 1:
            raise ValueError("profile_vector_length must be >= 1")
        if len(profile_length_bins) != profile_vector_length:
            raise ValueError(
                "profile_vector_length must equal len(profile_length_bins)"
            )
        if not tables:
            raise ValueError("No LM bucket tables loaded")
        self.profile_vector_length = int(profile_vector_length)
        self.profile_length_bins = tuple(int(v) for v in profile_length_bins)
        self._tables = dict(tables)
        by_dir: Dict[str, set[int]] = {}
        for direction, bucket, _source in self._tables:
            by_dir.setdefault(direction, set()).add(int(bucket))
        self._length_buckets_by_direction = {
            direction: tuple(sorted(values)) for direction, values in by_dir.items()
        }

    @classmethod
    def load(cls, asset_json_path: str | Path) -> "SpanHammingLmAssetsV2":
        fp = Path(asset_json_path).expanduser().resolve()
        if not fp.exists():
            raise FileNotFoundError(f"LM assets JSON not found: {fp}")
        raw = json.loads(fp.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("LM assets JSON must be an object")

        if str(raw.get("asset_kind", "")).strip() != "span_hamming_nose_lm_assets":
            raise ValueError("asset_kind must be 'span_hamming_nose_lm_assets'")
        vector_length = int(raw.get("profile_vector_length", 0))
        length_bins = raw.get("profile_length_bins")
        if not isinstance(length_bins, list) or not length_bins:
            raise ValueError("profile_length_bins must be a non-empty list")
        profile_length_bins = tuple(int(v) for v in length_bins)
        if vector_length != len(profile_length_bins):
            raise ValueError(
                "profile_vector_length must equal len(profile_length_bins)"
            )

        profile_tables = raw.get("profile_tables")
        if not isinstance(profile_tables, dict):
            raise ValueError("profile_tables must be an object")
        real_generator = str(raw.get("real_generator", "REAL")).strip().upper()

        tables: Dict[Tuple[str, int, str], _BucketTable] = {}
        for source_measure, by_dir in profile_tables.items():
            if not isinstance(by_dir, dict):
                continue
            for direction, by_bucket in by_dir.items():
                dir_norm = str(direction).strip().lower()
                if not isinstance(by_bucket, dict):
                    continue
                for bucket_text, bucket_node in by_bucket.items():
                    if not isinstance(bucket_node, dict):
                        continue
                    bucket = int(bucket_text)
                    refs = bucket_node.get("references")
                    combined_noise = bucket_node.get("combined_noise")
                    if not isinstance(refs, dict) or not isinstance(
                        combined_noise, dict
                    ):
                        raise ValueError(
                            f"Missing references/combined_noise for source={source_measure}, key=({dir_norm},{bucket})"
                        )
                    real_mean = np.asarray(
                        refs.get("real_mean_profile", []), dtype=np.float64
                    )
                    noise_mean = np.asarray(
                        refs.get("noise_mean_profile", []), dtype=np.float64
                    )
                    if real_mean.shape != (vector_length,) or noise_mean.shape != (
                        vector_length,
                    ):
                        raise ValueError(
                            f"mean profiles must match profile_vector_length for source={source_measure}, key=({dir_norm},{bucket})"
                        )

                    ecdf_noise_all = combined_noise.get("ecdf", {})
                    if not isinstance(ecdf_noise_all, dict):
                        raise ValueError(
                            f"Invalid combined_noise ecdf map for source={source_measure}, key=({dir_norm},{bucket})"
                        )
                    bp_noise, q_noise = _load_scalar_ecdf(
                        ecdf_noise_all.get("profile_margin_l1", {}),
                        feature_name="profile_margin_l1",
                        required=True,
                    )
                    mean_index_bp_noise, mean_index_q_noise = _load_scalar_ecdf(
                        ecdf_noise_all.get("mean_bin_index", {}),
                        feature_name="mean_bin_index",
                        required=True,
                    )
                    mean_length_bp_noise, mean_length_q_noise = _load_scalar_ecdf(
                        ecdf_noise_all.get("mean_bin_value", {}),
                        feature_name="mean_bin_value",
                        required=True,
                    )
                    tail_mass_noise_map_raw = ecdf_noise_all.get(
                        "tail_mass_by_start_index", {}
                    )
                    if not isinstance(tail_mass_noise_map_raw, dict):
                        raise ValueError(
                            f"Invalid tail_mass_by_start_index ecdf for source={source_measure}, key=({dir_norm},{bucket})"
                        )
                    tail_mass_noise_by_start_index: Dict[
                        int, Tuple[np.ndarray, np.ndarray]
                    ] = {}
                    for start_text, start_node in tail_mass_noise_map_raw.items():
                        start_index = int(start_text)
                        bp_tail, q_tail = _load_scalar_ecdf(
                            start_node,
                            feature_name=f"tail_mass_by_start_index[{start_index}]",
                            required=True,
                        )
                        tail_mass_noise_by_start_index[start_index] = (bp_tail, q_tail)

                    real_bp: np.ndarray | None = None
                    real_q: np.ndarray | None = None
                    mean_index_real_bp: np.ndarray | None = None
                    mean_index_real_q: np.ndarray | None = None
                    mean_length_real_bp: np.ndarray | None = None
                    mean_length_real_q: np.ndarray | None = None
                    tail_mass_real_by_start_index: Dict[
                        int, Tuple[np.ndarray, np.ndarray]
                    ] = {}
                    generators = bucket_node.get("generators", {})
                    if isinstance(generators, dict) and real_generator in generators:
                        ecdf_real_all = generators.get(real_generator, {}).get(
                            "ecdf", {}
                        )
                        if isinstance(ecdf_real_all, dict):
                            real_bp, real_q = _load_scalar_ecdf(
                                ecdf_real_all.get("profile_margin_l1", {}),
                                feature_name="profile_margin_l1_real",
                                required=False,
                            )
                            mean_index_real_bp, mean_index_real_q = _load_scalar_ecdf(
                                ecdf_real_all.get("mean_bin_index", {}),
                                feature_name="mean_bin_index_real",
                                required=False,
                            )
                            mean_length_real_bp, mean_length_real_q = _load_scalar_ecdf(
                                ecdf_real_all.get("mean_bin_value", {}),
                                feature_name="mean_bin_value_real",
                                required=False,
                            )
                            tail_mass_real_raw = ecdf_real_all.get(
                                "tail_mass_by_start_index", {}
                            )
                            if isinstance(tail_mass_real_raw, dict):
                                for (
                                    start_text,
                                    start_node,
                                ) in tail_mass_real_raw.items():
                                    start_index = int(start_text)
                                    bp_tail_real, q_tail_real = _load_scalar_ecdf(
                                        start_node,
                                        feature_name=f"tail_mass_by_start_index_real[{start_index}]",
                                        required=False,
                                    )
                                    if (
                                        bp_tail_real is not None
                                        and q_tail_real is not None
                                    ):
                                        tail_mass_real_by_start_index[start_index] = (
                                            bp_tail_real,
                                            q_tail_real,
                                        )

                    key = (dir_norm, bucket, str(source_measure))
                    tables[key] = _BucketTable(
                        direction=dir_norm,
                        length_bucket=bucket,
                        source_measure=str(source_measure),
                        real_mean_profile=real_mean,
                        noise_mean_profile=noise_mean,
                        margin_noise_breakpoints=bp_noise,
                        margin_noise_q=q_noise,
                        margin_real_breakpoints=real_bp,
                        margin_real_q=real_q,
                        mean_index_noise_breakpoints=mean_index_bp_noise,
                        mean_index_noise_q=mean_index_q_noise,
                        mean_index_real_breakpoints=mean_index_real_bp,
                        mean_index_real_q=mean_index_real_q,
                        mean_length_noise_breakpoints=mean_length_bp_noise,
                        mean_length_noise_q=mean_length_q_noise,
                        mean_length_real_breakpoints=mean_length_real_bp,
                        mean_length_real_q=mean_length_real_q,
                        tail_mass_noise_by_start_index=tail_mass_noise_by_start_index,
                        tail_mass_real_by_start_index=tail_mass_real_by_start_index,
                    )

        return cls(
            profile_vector_length=vector_length,
            profile_length_bins=profile_length_bins,
            tables=tables,
        )

    def available_sources(self) -> Tuple[str, ...]:
        return tuple(sorted({source for _, _, source in self._tables}))

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
        return min(buckets, key=lambda b: (abs(b - L), b))

    def score_profile_margin_l1_in_bucket(
        self,
        *,
        stats: Any,
        direction: str,
        length_bucket: int,
        clamp_min: float,
        clamp_max: float,
        profile_source: str = "span_raw_by_len",
        tail_start_index: int = 0,
    ) -> LmBucketScore:
        dir_norm = str(direction).strip().lower()
        source = str(profile_source).strip()
        key = (dir_norm, int(length_bucket), source)
        if key not in self._tables:
            raise KeyError(
                f"No LM table for direction={dir_norm}, length_bucket={int(length_bucket)}, source={source}"
            )
        table = self._tables[key]

        stats_bins = tuple(int(v) for v in getattr(stats, "length_bins", ()))
        if stats_bins != self.profile_length_bins:
            raise ValueError(
                f"Span stats length_bins mismatch: runtime={stats_bins} asset={self.profile_length_bins}"
            )
        source_values = tuple(float(v) for v in getattr(stats, source, ()))
        if len(source_values) != self.profile_vector_length:
            raise ValueError(
                f"Profile source '{source}' length mismatch: {len(source_values)} != {self.profile_vector_length}"
            )
        profile = _normalise_profile(source_values)

        margin_raw = _l1_distance(profile, table.noise_mean_profile) - _l1_distance(
            profile, table.real_mean_profile
        )
        pct_noise = _interp_clamped_pct(
            margin_raw,
            table.margin_noise_breakpoints,
            table.margin_noise_q,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
        if pct_noise is None:
            raise ValueError("Missing combined_noise percentile for profile_margin_l1")
        energy_noise = pct_to_energy(pct_noise)
        pct_real = _interp_clamped_pct(
            margin_raw,
            table.margin_real_breakpoints,
            table.margin_real_q,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )

        if not (0 <= int(tail_start_index) < self.profile_vector_length):
            raise ValueError(
                f"tail_start_index must be in [0,{self.profile_vector_length - 1}]"
            )
        mean_bin_index = float(
            np.sum(profile * np.arange(self.profile_vector_length, dtype=np.float64))
        )
        mean_bin_length = float(
            np.sum(profile * np.asarray(self.profile_length_bins, dtype=np.float64))
        )
        tail_mass = float(np.sum(profile[int(tail_start_index) :]))
        mean_index_pct_noise = _interp_clamped_pct(
            mean_bin_index,
            table.mean_index_noise_breakpoints,
            table.mean_index_noise_q,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
        if mean_index_pct_noise is None:
            raise ValueError("Missing combined_noise percentile for mean_bin_index")
        mean_index_energy = pct_to_energy(mean_index_pct_noise)
        mean_index_pct_real = _interp_clamped_pct(
            mean_bin_index,
            table.mean_index_real_breakpoints,
            table.mean_index_real_q,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
        mean_length_pct_noise = _interp_clamped_pct(
            mean_bin_length,
            table.mean_length_noise_breakpoints,
            table.mean_length_noise_q,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
        if mean_length_pct_noise is None:
            raise ValueError("Missing combined_noise percentile for mean_bin_value")
        mean_length_energy = pct_to_energy(mean_length_pct_noise)
        mean_length_pct_real = _interp_clamped_pct(
            mean_bin_length,
            table.mean_length_real_breakpoints,
            table.mean_length_real_q,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
        if int(tail_start_index) not in table.tail_mass_noise_by_start_index:
            raise KeyError(
                f"Missing tail_mass_by_start_index ecdf for start_index={int(tail_start_index)}"
            )
        tail_noise_bp, tail_noise_q = table.tail_mass_noise_by_start_index[
            int(tail_start_index)
        ]
        tail_pct_noise = _interp_clamped_pct(
            tail_mass,
            tail_noise_bp,
            tail_noise_q,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
        if tail_pct_noise is None:
            raise ValueError(
                "Missing combined_noise percentile for tail_mass_by_start_index"
            )
        tail_energy = pct_to_energy(tail_pct_noise)
        tail_pct_real = None
        if int(tail_start_index) in table.tail_mass_real_by_start_index:
            tail_real_bp, tail_real_q = table.tail_mass_real_by_start_index[
                int(tail_start_index)
            ]
            tail_pct_real = _interp_clamped_pct(
                tail_mass,
                tail_real_bp,
                tail_real_q,
                clamp_min=clamp_min,
                clamp_max=clamp_max,
            )

        return LmBucketScore(
            direction=dir_norm,
            length_bucket=int(length_bucket),
            profile_source=source,
            profile_margin_l1_raw=float(margin_raw),
            profile_margin_l1_pct_noise=float(pct_noise),
            profile_margin_l1_energy=float(energy_noise),
            profile_margin_l1_pct_real=(None if pct_real is None else float(pct_real)),
            mean_bin_index_raw=mean_bin_index,
            mean_bin_index_pct_noise=float(mean_index_pct_noise),
            mean_bin_index_energy=float(mean_index_energy),
            mean_bin_index_pct_real=(
                None if mean_index_pct_real is None else float(mean_index_pct_real)
            ),
            mean_bin_length_raw=mean_bin_length,
            mean_bin_length_pct_noise=float(mean_length_pct_noise),
            mean_bin_length_energy=float(mean_length_energy),
            mean_bin_length_pct_real=(
                None if mean_length_pct_real is None else float(mean_length_pct_real)
            ),
            tail_mass_raw=tail_mass,
            tail_mass_pct_noise=float(tail_pct_noise),
            tail_mass_energy=float(tail_energy),
            tail_mass_pct_real=(
                None if tail_pct_real is None else float(tail_pct_real)
            ),
        )


__all__ = [
    "SpanHammingLmAssetsV2",
    "LmBucketScore",
]
