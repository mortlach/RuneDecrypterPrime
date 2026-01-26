# tests/scoring/test_lm_raw_data_integrity.py
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Dict

import numpy as np
import pytest
import zstandard as zstd

from rune_decrypter_prime.scoring.language_model.language_model_prime import _load_bin
from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import ECDFCache
from rune_decrypter_prime.scoring.language_model.paths import load_index, expand_pattern

from tests.scoring._helpers.lm_test_guard import require_full_lm_assets


BASELINE_PATH = Path(__file__).resolve().parent / "_baselines" / "scorer_drift_baseline.json"


def _maybe_load_baseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_joint_header(path: Path) -> dict:
    """Read the small header embedded in joint table files.

    Format is defined in language_model_prime._load_bin:
        magic (4s), version (B), lg_size (H), zero (I), mu_stub (f), sigma_stub (f)
    """
    hdr_fmt = "<4sBHIff"
    hdr_n = struct.calcsize(hdr_fmt)

    with path.open("rb") as f:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(f) as r:
            raw = r.read(hdr_n)

    magic, version, lg_size, zero, mu_stub, sigma_stub = struct.unpack(hdr_fmt, raw)
    return {
        "magic": magic.decode("ascii", errors="replace"),
        "version": int(version),
        "lg_size": int(lg_size),
        "zero": int(zero),
        "mu_stub": float(mu_stub),
        "sigma_stub": float(sigma_stub),
    }


@pytest.mark.tier_a
def test_joint_tables_have_expected_shapes_and_zero_counts() -> None:
    lm_root, idx = require_full_lm_assets()
    out: Dict[str, dict] = {}

    for model in ("char", "wli"):
        model_cfg = idx.models[model]
        joint_pat = model_cfg["joint_pattern"]

        for mode in ("ltr", "rtl"):
            for pos in ("nose", "wise"):
                for n in (1, 2, 3, 4):
                    fp = expand_pattern(lm_root, joint_pat, mode=mode, pos=pos, n=n)

                    header = _read_joint_header(fp)

                    # _load_bin returns (keys, logp, cnts, probe_mask) in this branch.
                    keys, logp, cnts, probe_mask = _load_bin(fp)
                    nz_mask = cnts > 0

                    # Header/table consistency
                    assert header["magic"] == "WLI0"
                    assert (1 << header["lg_size"]) == int(keys.size)
                    assert int(logp.size) == int(keys.size) == int(cnts.size)
                    assert int(probe_mask) == (1 << header["lg_size"]) - 1

                    # Types and basic invariants
                    assert keys.dtype == np.uint64
                    assert cnts.dtype == np.uint64
                    assert logp.dtype == np.float32

                    nz = int(nz_mask.sum())
                    total = int(cnts.size)
                    zeros = total - nz

                    assert total > 0
                    assert nz > 0
                    assert zeros > 0  # any realistic n-gram table has unseen entries

                    # Non-zero entries should be finite and (as log-probabilities) typically <= 0
                    logp_nz = logp[nz_mask]
                    assert np.isfinite(logp_nz).all()
                    assert float(logp_nz.max()) <= 1e-6

                    # Counts for non-zero entries must be >= 1
                    assert int(cnts[nz_mask].min()) >= 1

                    out[f"{model}:{mode}:{pos}:n{n}"] = {
                        "table_size": total,
                        "nonzero": nz,
                        "zeros": zeros,
                        "zero_frac": float(zeros / total),
                        "header": header,
                    }

    # Optional drift alarm: if a baseline exists, compare to it.
    baseline = _maybe_load_baseline()
    if baseline is None:
        pytest.skip(
            "No drift baseline found. "
            "Run tests/scoring/generate_scorer_baselines.py in PyCharm to generate one."
        )

    fp0 = baseline.get("lm_joint_fingerprint", {})
    tol = float(baseline.get("tolerances", {}).get("float_abs", 1e-6))

    # Compare stable fields (sizes + zero counts).
    for k, v in out.items():
        if k not in fp0:
            continue
        b = fp0[k]
        assert int(v["table_size"]) == int(b["table_size"])
        assert int(v["nonzero"]) == int(b["nonzero"])
        assert int(v["zeros"]) == int(b["zeros"])
        assert float(v["zero_frac"]) == pytest.approx(float(b["zero_frac"]), abs=tol)


@pytest.mark.tier_a
def test_ecdf_tables_are_monotone_and_end_at_0_1() -> None:
    lm_root, _ = require_full_lm_assets()
    ecdf = ECDFCache(lm_root)

    baseline = _maybe_load_baseline()
    tol = float(baseline.get("tolerances", {}).get("float_abs", 1e-6)) if baseline else 1e-6
    fp0 = baseline.get("lm_ecdf_fingerprint", {}) if baseline else {}

    for model in ("char", "wli"):
        for mode in ("ltr", "rtl"):
            for pos in ("nose", "wise"):
                for n in (1, 2, 3, 4):
                    for stat in ("logp", "zsum", "madsum"):
                        try:
                            grid, q = ecdf.load(model=model, mode=mode, pos=pos, n=n, stat=stat)
                        except FileNotFoundError:
                            continue

                        assert grid.size > 0
                        assert q.size == grid.size
                        assert bool(np.all(np.diff(grid) > 0.0))  # strictly increasing
                        assert bool(np.all(np.diff(q) > 0.0))     # strictly increasing
                        assert 0.0 <= float(q[0]) < float(q[-1]) <= 1.0

                        key = f"{model}:{mode}:{pos}:n{n}:{stat}"
                        if key in fp0:
                            b = fp0[key]
                            assert int(grid.size) == int(b["grid_len"])
                            assert float(grid.min()) == pytest.approx(float(b["grid_min"]), abs=tol)
                            assert float(grid.max()) == pytest.approx(float(b["grid_max"]), abs=tol)
                            assert float(q.min()) == pytest.approx(float(b["q_min"]), abs=tol)
                            assert float(q.max()) == pytest.approx(float(b["q_max"]), abs=tol)
