from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import ECDFCache


def _write_index(root: Path) -> None:
    (root / "ecdf").mkdir(parents=True, exist_ok=True)
    (root / "index.json").write_text(
        json.dumps(
            {
                "version": "test.v1",
                "base": ".",
                "ecdf_root": "ecdf",
                "joint_root": "joint",
                "models": {
                    "char": {
                        "ecdf_pattern": "ecdf/%%MODE%%_%%POS%%_%%N%%_%%STAT%%_%%WIN%%.npz"
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def _ecdf_path(root: Path) -> Path:
    return root / "ecdf" / "ltr_nose_1_logp_10.npz"


def _valid_meta() -> dict[str, object]:
    return {
        "model": "char",
        "direction": "ltr",
        "se_mode": "nose",
        "n": 1,
        "stat": "logp",
        "win_ngrams": 10,
    }


def _write_ecdf(root: Path, *, grid=None, q=None, meta=None) -> Path:
    path = _ecdf_path(root)
    np.savez(
        path,
        grid=np.asarray([0.0, 1.0] if grid is None else grid, dtype=np.float64),
        q=np.asarray([0.1, 0.9] if q is None else q, dtype=np.float64),
        meta_json=json.dumps(_valid_meta() if meta is None else meta),
    )
    return path


def test_ecdf_cache_reports_relative_asset_id_hash_meta_and_interp_dtype(tmp_path: Path) -> None:
    _write_index(tmp_path)
    _write_ecdf(tmp_path)

    cache = ECDFCache(tmp_path, prefer_float32=True)
    grid, q = cache.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)

    assert grid.shape == q.shape == (2,)
    assert cache.asset_id(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10) == "ecdf/ltr_nose_1_logp_10.npz"
    assert cache.meta(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)["model"] == "char"
    assert len(cache.meta_hash(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)) == 64
    assert cache.interp_dtype(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10) in {"float32", "float64"}


def test_ecdf_cache_rejects_missing_ecdf_with_clear_file_not_found(tmp_path: Path) -> None:
    _write_index(tmp_path)
    cache = ECDFCache(tmp_path)

    with pytest.raises(FileNotFoundError, match="ECDF file not found"):
        cache.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)


def test_ecdf_cache_rejects_malformed_q_range(tmp_path: Path) -> None:
    _write_index(tmp_path)
    _write_ecdf(tmp_path, q=[0.9, 0.1])
    cache = ECDFCache(tmp_path)

    with pytest.raises(ValueError, match="ECDF q must be strictly increasing"):
        cache.load(model="char", mode="ltr", pos="nose", n=1, stat="logp", win=10)
