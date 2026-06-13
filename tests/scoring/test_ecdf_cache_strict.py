from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import ECDFCache


def _write_index(root: Path) -> None:
    data = {
        "version": "v1",
        "base": "char29",
        "ecdf_root": "ecdf",
        "joint_root": ".",
        "models": {
            "char": {
                "n": [1],
                "stats": ["logp"],
                "joint_pattern": "char/%%MODE%%/char29_joint_%%MODE%%_%%N%%_%%POS%%.bin.zst",
                "ecdf_pattern": "ecdf/char/%%MODE%%/%%MODE%%_%%POS%%_char_n%%N%%_win10_%%STAT%%.npz",
            }
        },
    }
    (root / "index.json").write_text(json.dumps(data), encoding="utf-8")


def _meta_base(*, win: int, n: int, stat: str = "logp", direction: str = "ltr", se: str = "nose") -> dict:
    return {
        "model": "char",
        "direction": direction,
        "se_mode": se,
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
        "mesh": {"kind": "linear", "params": {}, "num_knots": 4},
        "strict_increasing": {"enforce": True, "method": "nextafter"},
        "tie_policy": "builder nudges duplicate quantiles to enforce strict grid",
        "ecdf_canonical": True,
    }


def _write_ecdf(root: Path, *, grid: np.ndarray, q: np.ndarray, meta: dict) -> Path:
    path = root / "ecdf" / "char" / "ltr" / "ltr_nose_char_n1_win10_logp.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, grid=grid, q=q, meta_json=np.array(json.dumps(meta), dtype=object))
    return path


def test_ecdf_cache_loads_and_records_meta(tmp_path: Path) -> None:
    _write_index(tmp_path)
    grid = np.linspace(0.1, 0.4, 4, dtype=np.float64)
    q = np.linspace(0.2, 0.5, 4, dtype=np.float64)
    meta = _meta_base(win=10, n=1)
    _write_ecdf(tmp_path, grid=grid, q=q, meta=meta)

    ecdf = ECDFCache(root=tmp_path)
    g, qq = ecdf.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)
    assert g.size == qq.size == 4
    assert ecdf.meta_hash(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)
    assert ecdf.interp_dtype(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10) in {"float32", "float64"}
    ecdf.validate_clamp_range(
        model="char",
        mode="ltr",
        pos="nose",
        n=1,
        stat="logp",
        win=10,
        clamp_min=0.25,
        clamp_max=0.45,
    )


def test_ecdf_cache_falls_back_to_float64_interp(tmp_path: Path) -> None:
    _write_index(tmp_path)
    grid = np.array([1.0, 1.0 + 1e-12, 1.0 + 2e-12, 1.0 + 3e-12], dtype=np.float64)
    q = np.array([0.2, 0.3, 0.4, 0.5], dtype=np.float64)
    meta = _meta_base(win=10, n=1)
    _write_ecdf(tmp_path, grid=grid, q=q, meta=meta)

    ecdf = ECDFCache(root=tmp_path)
    g, _ = ecdf.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)
    assert g.dtype == np.float64
    assert ecdf.interp_dtype(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10) == "float64"


def test_ecdf_cache_rejects_meta_mismatch(tmp_path: Path) -> None:
    _write_index(tmp_path)
    grid = np.linspace(0.1, 0.4, 4, dtype=np.float64)
    q = np.linspace(0.2, 0.5, 4, dtype=np.float64)
    meta = _meta_base(win=10, n=1, direction="rtl")
    _write_ecdf(tmp_path, grid=grid, q=q, meta=meta)

    ecdf = ECDFCache(root=tmp_path)
    with pytest.raises(ValueError, match="direction mismatch"):
        _ = ecdf.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)


def test_ecdf_cache_rejects_missing_meta_json(tmp_path: Path) -> None:
    _write_index(tmp_path)
    path = tmp_path / "ecdf" / "char" / "ltr" / "ltr_nose_char_n1_win10_logp.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    grid = np.linspace(0.1, 0.4, 4, dtype=np.float64)
    q = np.linspace(0.2, 0.5, 4, dtype=np.float64)
    np.savez(path, grid=grid, q=q)

    ecdf = ECDFCache(root=tmp_path)
    with pytest.raises(ValueError, match="meta_json missing"):
        _ = ecdf.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)


def test_ecdf_cache_rejects_win_mismatch(tmp_path: Path) -> None:
    _write_index(tmp_path)
    grid = np.linspace(0.1, 0.4, 4, dtype=np.float64)
    q = np.linspace(0.2, 0.5, 4, dtype=np.float64)
    meta = _meta_base(win=10, n=1)
    _write_ecdf(tmp_path, grid=grid, q=q, meta=meta)

    ecdf = ECDFCache(root=tmp_path)
    _ = ecdf.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)
    with pytest.raises(ValueError, match="win_ngrams mismatch"):
        _ = ecdf.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=12)


def test_ecdf_cache_float32_requires_monotone_q(tmp_path: Path) -> None:
    _write_index(tmp_path)
    grid = np.linspace(0.1, 0.4, 4, dtype=np.float64)
    # Tiny deltas collapse in float32 and should force float64 interp.
    q = np.array([0.1, 0.1 + 1e-12, 0.1 + 2e-12, 0.1 + 3e-12], dtype=np.float64)
    meta = _meta_base(win=10, n=1)
    _write_ecdf(tmp_path, grid=grid, q=q, meta=meta)

    ecdf = ECDFCache(root=tmp_path)
    g, _ = ecdf.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)
    assert g.dtype == np.float64
    assert ecdf.interp_dtype(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10) == "float64"
