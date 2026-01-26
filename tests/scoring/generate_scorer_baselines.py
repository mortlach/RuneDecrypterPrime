# tests/scoring/generate_scorer_baselines.py
#
# PyCharm-friendly baseline generator.
#
# Run this file directly (Run ▶) to generate/update:
#   tests/scoring/_baselines/scorer_drift_baseline.json
#
# The baseline is used as a *drift alarm* for:
#   - LM asset fingerprints (sizes, zero counts, header stubs, ranges)
#   - Kaeding-style avg logp sanity statistics (English vs random; SD scales with length)
#
# The repo does not ship the full LM tables. If they are missing, this script will explain what is absent.

from __future__ import annotations

import json
import math
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from rune_decrypter_prime.core.config import CipherConfig, ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device, Direction, ObjectiveFamily, ObjectiveSpec, SeMode, Stat
from rune_decrypter_prime.scoring.language_model.language_model_prime import _load_bin
from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import ECDFCache
from rune_decrypter_prime.scoring.language_model.paths import default_lm_root, load_index, expand_pattern

from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext, plaintext1, word_breaks1


BASELINE_PATH = Path(__file__).resolve().parent / "_baselines" / "scorer_drift_baseline.json"


def _mk_cipher_cfg(length: int, *, device: Device = Device.CPU, encoding_dir: Direction = Direction.LTR) -> CipherConfig:
    # Minimal CipherConfig: build_scorer uses device/encoding and doesn't require keyops for pure scoring.
    ct = list(range(length))
    wli = [(i, i + 1) for i in range(length)]
    return CipherConfig(ciphertext=ct, wli_data=wli, key_length=None, device=device, encoding_dir=encoding_dir)


def _mk_avg_logp_scorer(win: int, *, encoding_dir: Direction = Direction.LTR) -> Any:
    # Kaeding-style: average log-probability of tetragrams (or n-grams) over a passage.
    s_cfg = ScoringConfig(
        objective=ObjectiveSpec(family=ObjectiveFamily.AVG, stat=Stat.LOGP, win=int(win)),
        se_mode=SeMode.NOSE,
        encoding_dir=encoding_dir,
        include_char=True,
        use_word_breaks=False,
        char_weights={4: 1.0},
        wli_weights={},
        dtype="float32",
    ).asdict()
    c_cfg = _mk_cipher_cfg(win, encoding_dir=encoding_dir).asdict()
    return build_scorer(c_cfg, s_cfg)


def _kaeding_stats(rng: np.random.Generator) -> Dict[str, Any]:
    # Use the shipped test plaintexts (29-char alphabet indices) as a stable reference.
    pt = np.asarray(long_plaintext, dtype=np.uint8)
    assert pt.ndim == 1 and pt.size >= 1500

    out: Dict[str, Any] = {}

    for N in (100, 1000):
        scorer = _mk_avg_logp_scorer(N, encoding_dir=Direction.LTR)

        # Random contiguous passages (English-ish)
        K = 80 if N == 100 else 40
        scores_real: List[float] = []
        scores_rand: List[float] = []

        for _ in range(K):
            start = int(rng.integers(0, pt.size - N))
            block = pt[start : start + N]
            # Kaeding's "fitness" is an average log probability per tetragram.
            scores_real.append(float(scorer.score(block, None)))

            # Random control (uniform 0..28)
            block_r = rng.integers(0, 29, size=N, dtype=np.uint8)
            scores_rand.append(float(scorer.score(block_r, None)))

        out[f"N{N}"] = {
            "K": K,
            "real_mean": float(np.mean(scores_real)),
            "real_std": float(np.std(scores_real, ddof=0)),
            "rand_mean": float(np.mean(scores_rand)),
            "rand_std": float(np.std(scores_rand, ddof=0)),
        }

    # One fixed, reproducible score for the standard test plaintext (with its real WLI).
    # Even though the Kaeding scorer ignores WLI, we keep this as a consistent debug anchor.
    anchor = np.asarray(plaintext1, dtype=np.uint8)
    scorer_anchor = _mk_avg_logp_scorer(int(anchor.size), encoding_dir=Direction.LTR)
    out["anchor_plaintext1_len"] = int(anchor.size)
    out["anchor_plaintext1_avglogp"] = float(scorer_anchor.score(anchor, word_breaks1))

    return out


def _fingerprint_joint_tables(lm_root: Path, idx: Any) -> Dict[str, Any]:
    # Produce lightweight but conclusive fingerprints: sizes, zeros, header stubs, and value ranges.
    # This is intended for drift detection, *not* for shipping data.
    out: Dict[str, Any] = {}

    for model in ("char", "wli"):
        model_cfg = idx.models.get(model, {})
        joint_pat = model_cfg.get("joint_pattern")
        if not joint_pat:
            continue
        for mode in ("ltr", "rtl"):
            for pos in ("nose", "wise"):
                for n in (1, 2, 3, 4):
                    fp = expand_pattern(lm_root, joint_pat, mode=mode, pos=pos, n=n)
                    if not fp.exists():
                        continue
                    # _load_bin returns (keys, logp, cnts, probe_mask).
                    keys, logp, cnts, probe_mask = _load_bin(fp)
                    nz_mask = cnts > 0

                    nz = int(nz_mask.sum())
                    total = int(cnts.size)
                    zeros = int(total - nz)

                    # Ranges over non-zero entries (the only ones that should matter to scoring).
                    logp_nz = logp[nz_mask]
                    cnts_nz = cnts[nz_mask]

                    # Values for zero-count entries are still part of the file; we fingerprint them
                    # as "what OOV/zero aliases to" at the *asset* level (not the runtime smoothing).
                    logp_z = logp[~nz_mask]
                    # Use a tiny summary to keep the baseline small but informative.
                    zero_logp_min = float(logp_z.min()) if logp_z.size else None
                    zero_logp_max = float(logp_z.max()) if logp_z.size else None
                    # If all zero entries share exactly one value, this will be 1.
                    zero_logp_unique = int(np.unique(logp_z).size) if logp_z.size else 0

                    # Safety: a couple of small invariants.
                    assert int(keys.size) > 0
                    assert int(logp.size) == int(keys.size) == int(cnts.size)
                    assert int(nz_mask.sum()) > 0
                    assert int(cnts_nz.min()) >= 1
                    assert np.isfinite(logp_nz).all()

                    key = f"{model}:{mode}:{pos}:n{n}"
                    out[key] = {
                        "path": str(fp.relative_to(lm_root)),
                        "table_size": total,
                        "nonzero": nz,
                        "zeros": zeros,
                        "zero_frac": float(zeros / total),
                        "count_min": int(cnts_nz.min()),
                        "count_max": int(cnts_nz.max()),
                        "logp_min": float(logp_nz.min()),
                        "logp_max": float(logp_nz.max()),
                        "zero_logp_min": zero_logp_min,
                        "zero_logp_max": zero_logp_max,
                        "zero_logp_unique": zero_logp_unique,
                    }

    return out


def _fingerprint_ecdf_tables(lm_root: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    ecdf = ECDFCache(lm_root)

    for model in ("char", "wli"):
        for mode in ("ltr", "rtl"):
            for pos in ("nose", "wise"):
                for n in (1, 2, 3, 4):
                    for stat in ("logp", "zsum", "madsum"):
                        try:
                            grid, q = ecdf.load(model=model, mode=mode, pos=pos, n=n, stat=stat)
                        except FileNotFoundError:
                            continue

                        key = f"{model}:{mode}:{pos}:n{n}:{stat}"
                        out[key] = {
                            "grid_len": int(grid.size),
                            "grid_min": float(grid.min()) if grid.size else None,
                            "grid_max": float(grid.max()) if grid.size else None,
                            "q_min": float(q.min()) if q.size else None,
                            "q_max": float(q.max()) if q.size else None,
                            "grid_monotone": bool(np.all(np.diff(grid) > 0.0)) if grid.size > 1 else True,
                            "q_monotone": bool(np.all(np.diff(q) >= 0.0)) if q.size > 1 else True,
                            "q_ends_01": bool((abs(float(q[0]) - 0.0) < 1e-6) and (abs(float(q[-1]) - 1.0) < 1e-6)) if q.size else False,
                        }

    return out


def generate(*, seed: int = 12345) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)

    lm_root = default_lm_root().resolve()
    if not lm_root.exists():
        raise RuntimeError(f"LM root not found: {lm_root}")

    idx = load_index(lm_root)

    baseline: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": int(seed),
        "lm_root": str(lm_root),
        "platform": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "kaeding_style": _kaeding_stats(rng),
        "lm_joint_fingerprint": _fingerprint_joint_tables(lm_root, idx),
        "lm_ecdf_fingerprint": _fingerprint_ecdf_tables(lm_root),
        "tolerances": {
            # floats drift a little with platform/BLAS; keep tolerances explicit.
            "float_abs": 1e-6,
            "float_rel": 1e-6,
        },
    }
    return baseline


def main() -> None:
    baseline = generate()
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote scorer drift baseline to:\n  {BASELINE_PATH}")


if __name__ == "__main__":
    main()
