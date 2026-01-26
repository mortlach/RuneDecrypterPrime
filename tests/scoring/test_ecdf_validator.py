from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from rune_decrypter_prime.scoring.language_model.ecdf_validator import validate_ecdf_npz


def _meta_base(*, win: int, n: int, stat: str = "logp") -> dict:
    return {
        "model": "char",
        "direction": "ltr",
        "se_mode": "nose",
        "n": int(n),
        "stat": stat,
        "win_ngrams": int(win),
        "window_def": {
            "win_ngrams": int(win),
            "span_formula": "nose: L_n = W + n - 1; wise: L_n = W + n + 1",
            "start_index_rule": "i = 0 .. T - L_max; L_max = max_n L_n",
            "tags": "wise uses [29]... [30], nose has no tags",
            "tags_start_id": 29,
            "tags_end_id": 30,
        },
        "smoothing": {"kind": "auto_gt", "alpha": 0.5},
        "oov_policy": "floor_min_seen",
        "mesh": {"kind": "linear", "params": {}, "num_knots": 5},
        "strict_increasing": {"enforce": True, "method": "nextafter"},
        "tie_policy": "builder nudges duplicate quantiles to enforce strict grid",
        "ecdf_canonical": True,
    }


def _write_npz(path: Path, *, grid: np.ndarray, q: np.ndarray, meta: dict | None = None) -> None:
    payload = {"grid": grid, "q": q}
    if meta is not None:
        payload["meta_json"] = np.array(json.dumps(meta), dtype=object)
    np.savez(path, **payload)


def test_validator_accepts_valid_asset(tmp_path: Path) -> None:
    grid = np.linspace(0.1, 0.9, 5, dtype=np.float64)
    q = np.linspace(0.2, 0.8, 5, dtype=np.float64)
    meta = _meta_base(win=10, n=4)
    fp = tmp_path / "ok.npz"
    _write_npz(fp, grid=grid, q=q, meta=meta)

    res = validate_ecdf_npz(fp, ecdf_clamp_min=0.25, ecdf_clamp_max=0.75)
    assert res.ok
    assert res.meta_hash is not None


def test_validator_rejects_missing_meta(tmp_path: Path) -> None:
    grid = np.linspace(0.1, 0.9, 5, dtype=np.float64)
    q = np.linspace(0.2, 0.8, 5, dtype=np.float64)
    fp = tmp_path / "no_meta.npz"
    _write_npz(fp, grid=grid, q=q, meta=None)

    res = validate_ecdf_npz(fp, ecdf_clamp_min=0.25, ecdf_clamp_max=0.75)
    assert not res.ok
    assert any("meta_json" in e for e in res.errors)


def test_validator_rejects_non_float64(tmp_path: Path) -> None:
    grid = np.linspace(0.1, 0.9, 5, dtype=np.float32)
    q = np.linspace(0.2, 0.8, 5, dtype=np.float64)
    meta = _meta_base(win=10, n=4)
    fp = tmp_path / "dtype.npz"
    _write_npz(fp, grid=grid, q=q, meta=meta)

    res = validate_ecdf_npz(fp, ecdf_clamp_min=0.25, ecdf_clamp_max=0.75)
    assert not res.ok
    assert any("grid dtype must be float64" in e for e in res.errors)


def test_validator_rejects_non_monotone(tmp_path: Path) -> None:
    grid = np.array([0.1, 0.2, 0.2, 0.4], dtype=np.float64)
    q = np.array([0.2, 0.3, 0.4, 0.5], dtype=np.float64)
    meta = _meta_base(win=10, n=4)
    fp = tmp_path / "mono.npz"
    _write_npz(fp, grid=grid, q=q, meta=meta)

    res = validate_ecdf_npz(fp, ecdf_clamp_min=0.25, ecdf_clamp_max=0.45)
    assert not res.ok
    assert any("grid must be strictly increasing" in e for e in res.errors)


def test_validator_rejects_clamp_outside_range(tmp_path: Path) -> None:
    grid = np.linspace(0.1, 0.9, 5, dtype=np.float64)
    q = np.linspace(0.2, 0.8, 5, dtype=np.float64)
    meta = _meta_base(win=10, n=4)
    fp = tmp_path / "clamp.npz"
    _write_npz(fp, grid=grid, q=q, meta=meta)

    res = validate_ecdf_npz(fp, ecdf_clamp_min=0.1, ecdf_clamp_max=0.9)
    assert not res.ok
    assert any("clamp range outside ECDF range" in e for e in res.errors)
