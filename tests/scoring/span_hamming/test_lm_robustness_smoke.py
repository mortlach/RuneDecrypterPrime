from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext
from rune_decrypter_prime.scoring.span_hamming import (
    SpanCalibratedAssets,
    SpanHammingBackend,
    SpanHammingConfig,
    SpanHammingLmAssetsV2,
)
from tools.benchmarks.scoring.span_hamming_nose.usage_benchmark_common import (
    SpanHammingBenchmarkRuntimeConfig,
    corrupt_with_random,
    make_block_shuffle,
    make_fragment_soup,
    make_random_text,
    score_text_with_assets,
    summarize_numeric,
)


pytestmark = pytest.mark.tier_a


def _build_span_wordlists_from_real_text() -> dict[int, list[list[int]]]:
    pt = np.asarray(long_plaintext, dtype=np.uint8)
    out: dict[int, list[list[int]]] = {}
    for L in (5, 6, 7, 8):
        uniq: set[tuple[int, ...]] = set()
        rows: list[list[int]] = []
        stop = max(0, pt.size - L + 1)
        for i in range(0, stop, 2):
            key = tuple(int(v) for v in pt[i : i + L])
            if key in uniq:
                continue
            uniq.add(key)
            rows.append(list(key))
        out[L] = rows
    return out


def _write_span_assets(root: Path, *, length_bucket: int) -> Path:
    assets = root / "span_assets"
    ecdf_dir = assets / "ecdf" / "span_x"
    ecdf_dir.mkdir(parents=True, exist_ok=True)
    cal = {
        "version": "v1",
        "rows": [
            {
                "direction": "ltr",
                "length_bucket": int(length_bucket),
                "span_neg_ref": 0.25,
                "span_denom": 0.45,
                "span_valid": True,
                "char4_neg_ref": -11.0,
                "char4_denom": 1.0,
                "char4_valid": True,
            }
        ],
    }
    (assets / "combined_calibration.json").write_text(json.dumps(cal), encoding="utf-8")
    meta = {
        "model": "span",
        "stat": "x_span",
        "direction": "ltr",
        "length_bucket": int(length_bucket),
    }
    np.savez(
        ecdf_dir / f"ltr_nose_span_lb{int(length_bucket)}_fulltext_x_span.npz",
        grid=np.asarray([-1.0, 0.0, 1.0], dtype=np.float64),
        q=np.asarray([0.05, 0.5, 0.95], dtype=np.float64),
        meta_json=np.array(json.dumps(meta), dtype=np.str_),
    )
    return assets


def _write_lm_assets(root: Path, *, length_bucket: int) -> Path:
    fp = root / "span_lm_assets.json"
    payload = {
        "asset_kind": "span_hamming_nose_lm_assets",
        "profile_vector_length": 4,
        "profile_length_bins": [5, 6, 7, 8],
        "profile_vector_measures": ["span_raw_by_len"],
        "real_generator": "REAL",
        "profile_tables": {
            "span_raw_by_len": {
                "ltr": {
                    str(int(length_bucket)): {
                        "references": {
                            "real_mean_profile": [0.05, 0.10, 0.25, 0.60],
                            "noise_mean_profile": [0.55, 0.25, 0.15, 0.05],
                            "real_count": 1,
                            "noise_count": 1,
                        },
                        "generators": {
                            "REAL": {
                                "ecdf": {
                                    "profile_margin_l1": {
                                        "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                        "breakpoints": [-2.0, -1.0, 0.0, 1.0, 2.0],
                                    },
                                    "mean_bin_index": {
                                        "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                        "breakpoints": [0.0, 0.8, 1.5, 2.3, 3.0],
                                    },
                                    "mean_bin_value": {
                                        "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                        "breakpoints": [5.0, 5.8, 6.5, 7.3, 8.0],
                                    },
                                    "tail_mass_by_start_index": {
                                        "0": {
                                            "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                            "breakpoints": [1.0, 1.0, 1.0, 1.0, 1.0],
                                        },
                                        "1": {
                                            "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                            "breakpoints": [0.10, 0.20, 0.40, 0.70, 0.90],
                                        },
                                        "2": {
                                            "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                            "breakpoints": [0.05, 0.10, 0.20, 0.50, 0.80],
                                        },
                                        "3": {
                                            "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                            "breakpoints": [0.00, 0.05, 0.10, 0.30, 0.60],
                                        },
                                    }
                                }
                            }
                        },
                        "combined_noise": {
                            "ecdf": {
                                "profile_margin_l1": {
                                    "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                    "breakpoints": [-2.0, -1.0, 0.0, 1.0, 2.0],
                                },
                                "mean_bin_index": {
                                    "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                    "breakpoints": [0.0, 0.8, 1.5, 2.3, 3.0],
                                },
                                "mean_bin_value": {
                                    "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                    "breakpoints": [5.0, 5.8, 6.5, 7.3, 8.0],
                                },
                                "tail_mass_by_start_index": {
                                    "0": {
                                        "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                        "breakpoints": [1.0, 1.0, 1.0, 1.0, 1.0],
                                    },
                                    "1": {
                                        "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                        "breakpoints": [0.10, 0.20, 0.40, 0.70, 0.90],
                                    },
                                    "2": {
                                        "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                        "breakpoints": [0.05, 0.10, 0.20, 0.50, 0.80],
                                    },
                                    "3": {
                                        "quantile_grid": [0.05, 0.20, 0.50, 0.80, 0.95],
                                        "breakpoints": [0.00, 0.05, 0.10, 0.30, 0.60],
                                    },
                                }
                            }
                        },
                    }
                }
            }
        },
    }
    fp.write_text(json.dumps(payload), encoding="utf-8")
    return fp


def _mk_runtime_bundle(tmp_path: Path, *, length_bucket: int = 400):
    backend = SpanHammingBackend(
        config=SpanHammingConfig(len_min=5, len_max=8, max_hd=2),
        wordlists=_build_span_wordlists_from_real_text(),
    )
    span_assets = SpanCalibratedAssets.load(_write_span_assets(tmp_path, length_bucket=length_bucket))
    lm_assets = SpanHammingLmAssetsV2.load(_write_lm_assets(tmp_path, length_bucket=length_bucket))
    corpus = np.asarray(long_plaintext, dtype=np.uint8)
    return backend, span_assets, lm_assets, corpus


def _runtime_cfg(*, lm_weight: float, coverage_min: float = 0.0) -> SpanHammingBenchmarkRuntimeConfig:
    return SpanHammingBenchmarkRuntimeConfig(
        objective_family="pct",
        coverage_min=float(coverage_min),
        quality_min=0.0,
        span_pct_min=None,
        char_pct_min=None,
        combine_mode="min",
        weight_span=1.0,
        weight_char=0.0,
        use_char_channel=False,
        gate_fail_policy="score_floor",
        gate_score_floor=1e-6,
        lm_weight=float(lm_weight),
        lm_profile_source="span_raw_by_len",
        lm_tail_start_index=0,
    )


def test_corruption_curve_mean_scores_drop(tmp_path: Path) -> None:
    backend, span_assets, lm_assets, corpus = _mk_runtime_bundle(tmp_path)
    alphabet_size = int(np.max(corpus)) + 1
    length = 400
    anchor = corpus[300 : 300 + length].copy()

    base_means: dict[float, float] = {}
    total_means: dict[float, float] = {}
    for rate in (0.0, 0.20, 0.50, 1.0):
        rows = []
        for seed in range(16):
            rng = np.random.default_rng(1000 + seed + int(rate * 100))
            sample = corrupt_with_random(anchor, rate, alphabet_size, rng)
            rows.append(
                score_text_with_assets(
                    sample,
                    backend=backend,
                    span_assets=span_assets,
                    lm_assets=lm_assets,
                    direction="ltr",
                    runtime_config=_runtime_cfg(lm_weight=0.75),
                )
            )
        base_means[rate] = summarize_numeric(r.span_pct for r in rows)["mean"]
        total_means[rate] = summarize_numeric(r.final_pct for r in rows)["mean"]

    assert base_means[0.0] >= base_means[0.20]
    assert base_means[0.20] > base_means[0.50] > base_means[1.0]
    assert total_means[0.0] > total_means[1.0]
    assert total_means[0.20] > total_means[1.0]
    assert total_means[0.50] > total_means[1.0]


def test_fragment_soup_is_penalised_more_by_lm_than_base(tmp_path: Path) -> None:
    backend, span_assets, lm_assets, corpus = _mk_runtime_bundle(tmp_path)
    length = 400
    real = corpus[700 : 700 + length].copy()

    base_real = score_text_with_assets(
        real,
        backend=backend,
        span_assets=span_assets,
        lm_assets=lm_assets,
        direction="ltr",
        runtime_config=_runtime_cfg(lm_weight=0.0),
    ).final_pct
    lm_real = score_text_with_assets(
        real,
        backend=backend,
        span_assets=span_assets,
        lm_assets=lm_assets,
        direction="ltr",
        runtime_config=_runtime_cfg(lm_weight=0.75),
    ).final_pct

    base_fragment = []
    lm_fragment = []
    for seed in range(16):
        rng = np.random.default_rng(9000 + seed)
        sample = make_fragment_soup(corpus, length, rng, chunk_lengths=(5, 6))
        base_fragment.append(
            score_text_with_assets(
                sample,
                backend=backend,
                span_assets=span_assets,
                lm_assets=lm_assets,
                direction="ltr",
                runtime_config=_runtime_cfg(lm_weight=0.0),
            ).final_pct
        )
        lm_fragment.append(
            score_text_with_assets(
                sample,
                backend=backend,
                span_assets=span_assets,
                lm_assets=lm_assets,
                direction="ltr",
                runtime_config=_runtime_cfg(lm_weight=0.75),
            ).final_pct
        )

    base_gap = float(base_real - summarize_numeric(base_fragment)["mean"])
    lm_gap = float(lm_real - summarize_numeric(lm_fragment)["mean"])
    assert lm_gap > base_gap


def test_random_and_block_shuffle_stay_below_real_with_lm(tmp_path: Path) -> None:
    backend, span_assets, lm_assets, corpus = _mk_runtime_bundle(tmp_path)
    alphabet_size = int(np.max(corpus)) + 1
    length = 400
    real = corpus[1200 : 1200 + length].copy()
    real_score = score_text_with_assets(
        real,
        backend=backend,
        span_assets=span_assets,
        lm_assets=lm_assets,
        direction="ltr",
        runtime_config=_runtime_cfg(lm_weight=0.75),
    ).final_pct

    random_scores = []
    shuffled_scores = []
    for seed in range(12):
        rng = np.random.default_rng(12_000 + seed)
        random_scores.append(
            score_text_with_assets(
                make_random_text(length, alphabet_size, rng),
                backend=backend,
                span_assets=span_assets,
                lm_assets=lm_assets,
                direction="ltr",
                runtime_config=_runtime_cfg(lm_weight=0.75),
            ).final_pct
        )
        shuffled_scores.append(
            score_text_with_assets(
                make_block_shuffle(real, rng, block_size=4),
                backend=backend,
                span_assets=span_assets,
                lm_assets=lm_assets,
                direction="ltr",
                runtime_config=_runtime_cfg(lm_weight=0.75),
            ).final_pct
        )

    assert real_score > summarize_numeric(random_scores)["mean"]
    assert real_score > summarize_numeric(shuffled_scores)["mean"]


def test_gate_failed_rows_do_not_apply_lm_to_final_output(tmp_path: Path) -> None:
    backend, span_assets, lm_assets, corpus = _mk_runtime_bundle(tmp_path)
    sample = corpus[0:400].copy()

    scored = score_text_with_assets(
        sample,
        backend=backend,
        span_assets=span_assets,
        lm_assets=lm_assets,
        direction="ltr",
        runtime_config=_runtime_cfg(lm_weight=0.75, coverage_min=1.1),
    )

    assert bool(scored.gate_failed) is True
    assert bool(scored.lm_enabled) is True
    assert bool(scored.lm_applied_to_score) is False
    assert scored.runtime_total_pct == pytest.approx(scored.combined_pct, rel=0, abs=1e-12)
    assert scored.final_pct == pytest.approx(1e-6, rel=0, abs=1e-12)
