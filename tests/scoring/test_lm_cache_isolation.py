from __future__ import annotations
import json
import struct
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import zstandard as zstd
import rune_decrypter_prime.scoring.language_model.language_model_prime as lmp
from rune_decrypter_prime.scoring.language_model.language_model_prime import (
    LanguageModelPrime,
    _load_bin,
)


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


def _write_joint(root: Path) -> Path:
    path = root / "char" / "ltr" / "char29_joint_ltr_1_nose.bin.zst"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = struct.pack("<4sBHIff", b"WLI0", 1, 0, 0, 0.0, 0.0)
    keys = np.zeros(1, dtype=np.uint64)
    logp = np.zeros(1, dtype=np.float32)
    cnts = np.ones(1, dtype=np.uint64)
    raw = header + keys.tobytes() + logp.tobytes() + cnts.tobytes()
    comp = zstd.ZstdCompressor().compress(raw)
    path.write_bytes(comp)
    return path


def test_lm_cache_isolation(tmp_path: Path, monkeypatch) -> None:
    _write_index(tmp_path)
    _write_joint(tmp_path)

    class _StubFastModel:
        def __init__(self, keys, logp, cnts, mask, *_args):
            self.keys = keys
            self.logp = logp
            self.cnts = cnts
            self.mask = mask

    monkeypatch.setattr(
        lmp, "_fastlm", SimpleNamespace(FastTransitionModel=_StubFastModel)
    )
    lm1 = LanguageModelPrime(lm_root=tmp_path, smoothing="none")
    m1 = lm1._ensure("ltr", "nose", "char", 1)
    lm2 = LanguageModelPrime(lm_root=tmp_path, smoothing="lidstone")
    m2 = lm2._ensure("ltr", "nose", "char", 1)
    assert m1.logp is not m2.logp
    assert not np.shares_memory(m1.logp, m2.logp)
    m1.logp[0] = -99.0
    assert float(m2.logp[0]) != -99.0
    path = lm1._joint_path("ltr", "nose", "char", 1)
    _, logp2, _, _ = _load_bin(path, cache=lm1._bin_cache)
    assert logp2 is m1.logp
