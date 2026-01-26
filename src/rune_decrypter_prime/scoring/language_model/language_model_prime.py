# ============================================================
# rune_decrypter_prime/scoring/language_model/language_model_prime.py   (LM scorer)
# High-level scorer for WLI/CHAR across (FWD/REV × WISE/NOSE × n=1..4),
# backed by a compiled _fastlm transition model and an index.json-driven layout.
# ============================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Literal, Dict, Any, Optional, Sequence
import math
import os
import struct

import numpy as np
import zstandard as zstd

from . import _fastlm
from .paths import load_index, expand_pattern, default_lm_root

# Canonical LM defaults (single source of truth)
DEFAULT_SMOOTHING = "auto_gt"          # "none" | "lidstone" | "jeffreys" | "auto_gt"
DEFAULT_OOV_POLICY = "floor_min_seen"  # "floor_min_seen" | "lidstone"

DIR   = Literal["ltr", "rtl"]
SE    = Literal["wise", "nose", "WISE", "NOSE"]
MODEL = Literal["wli", "char", "WLI", "CHAR"]

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _norm_dir(direction: DIR) -> str:
    d = str(direction).lower()
    if d == "ltr":
        return "ltr"
    if d == "rtl":
        return "rtl"
    raise ValueError("direction must be 'ltr' or 'rtl'")


def _norm_se(se: SE) -> str:
    s = str(se).lower()
    if s in ("wise", "nose"):
        return s
    raise ValueError("se must be 'wise' or 'nose'")


def _norm_model(model: MODEL) -> str:
    m = str(model).lower()
    if m in ("wli", "char"):
        return m
    raise ValueError("model must be 'wli' or 'char'")


# Cache to avoid re-decompressing the same .bin.zst multiple times in a run.
# Keyed by absolute Path; values are writable C-contiguous arrays and the mask.
_load_bin_cache: dict[Path, tuple[np.ndarray, np.ndarray, np.ndarray, np.uint32]] = {}
_LOG_LOADS = bool(os.environ.get("RDP_LM_LOG_LOADS"))


def _load_bin(path: Path):
    """
    Read a combined .bin.zst with header "<4sBHIff" (magic 'WLI0') then:
      keys:uint64[M], logp:float32[M], cnts:uint64[M]

    Returns
    -------
    (keys, logp, cnts, mask):
        keys : np.ndarray[uint64, C]   — hash table keys
        logp : np.ndarray[float32, C]  — log-probabilities (will be smoothed in-place)
        cnts : np.ndarray[uint64, C]   — counts
        mask : np.uint32               — bitmask for linear-probing lookup (2^lg - 1)

    Notes
    -----
    • Uses a simple in-process cache so we only decompress and print once per file.
    • Arrays are copied into writable C-contiguous buffers; the native scorer
      may update `logp` when applying smoothing.
    """
    global _load_bin_cache

    if path in _load_bin_cache:
        return _load_bin_cache[path]

    if not path.exists():
        raise FileNotFoundError(f"LM file not found: {path}")

    if _LOG_LOADS:
        print(f"[lm] loading {path}")

    comp = path.read_bytes()
    dec = zstd.ZstdDecompressor().decompress(comp)
    buf = memoryview(dec)
    off = 0

    magic, version, lg_size, _zero, _mu_stub, _sigma_stub = struct.unpack_from("<4sBHIff", buf, off)
    off += struct.calcsize("<4sBHIff")
    if magic != b"WLI0":
        raise ValueError(f"Bad magic in {path}")

    table_size = 1 << lg_size
    mask = np.uint32((1 << lg_size) - 1)

    keys = np.frombuffer(buf[off: off + 8 * table_size], dtype="<u8"); off += 8 * table_size
    logp = np.frombuffer(buf[off: off + 4 * table_size], dtype="<f4"); off += 4 * table_size
    cnts = np.frombuffer(buf[off: off + 8 * table_size], dtype="<u8"); off += 8 * table_size

    # Return writable copies (native may smooth in-place)
    out = (
        np.array(keys, copy=True),
        np.array(logp, copy=True),
        np.array(cnts, copy=True),
        mask,
    )
    _load_bin_cache[path] = out
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Public structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SentScores:
    counts_sum: int
    logprob_sum: float
    z_sum: float
    madsum: float


# ──────────────────────────────────────────────────────────────────────────────
# Index-driven LanguageModelPrime
# ──────────────────────────────────────────────────────────────────────────────

class LanguageModelPrime:
    """
    High-level scorer for WLI/CHAR over (FWD/REV × WISE/NOSE × n=1..4).

    * Loads joint tables using <lm_root>/index.json patterns:
        models.<model>.joint_pattern
      e.g. "char/%%MODE%%/char29_joint_%%MODE%%_%%N%%_%%POS%%.bin.zst"
    * A single lm_root (resolved by default_lm_root()).
    * Lazily creates _fastlm.FastTransitionModel instances.
    """

    def __init__(
        self,
        lm_root: str | Path | None = None,
        smoothing: str | None = None,   # "none"|"lidstone"|"jeffreys"|"auto_gt"
        alpha: float = 0.5,             # used when smoothing == "lidstone"
        oov_policy: str | None = None,  # "floor_min_seen"|"lidstone"
        include_char: bool = True,
    ):
        self.root: Path = Path(lm_root) if lm_root else default_lm_root()
        self.idx = load_index(self.root)
        self.include_char = include_char

        # Canonical option maps
        smap = {"none": 0, "lidstone": 1, "jeffreys": 2, "auto_gt": 3}
        omap = {"floor_min_seen": 0, "lidstone": 1}

        # Coerce None → defaults
        self.smoothing = DEFAULT_SMOOTHING if smoothing is None else smoothing
        self.oov_policy = DEFAULT_OOV_POLICY if oov_policy is None else oov_policy

        if self.smoothing not in smap:
            raise ValueError("smoothing must be one of: " + ", ".join(smap))
        if self.oov_policy not in omap:
            raise ValueError("oov_policy must be one of: " + ", ".join(omap))

        self._smooth_mode = smap[self.smoothing]
        self._alpha = float(alpha)
        self._oov_mode = omap[self.oov_policy]
        self._cache: Dict[Tuple[str, str, str, int], _fastlm.FastTransitionModel] = {}

    # ---------- public API ----------

    def score(
        self,
        pt: List[List[int]],
        wli: Optional[List[List[List[int]]]],
        direction: DIR,
        se: SE,
        n: int,
        model: MODEL,
    ) -> List[SentScores]:
        """
        Per-sentence scoring. Returns List[SentScores], one per input sentence.

        Parameters
        ----------
        pt
            Nested int ids (0..30). For WISE, sentences must begin with 29 and end with 30.
        wli
            Nested pairs [pos, len] (required for model="wli"; ignored for "char").
        direction
            "ltr"/"rtl" (accepts "forward"/"reverse").
        se
            "wise"/"nose" (case-insensitive).
        n
            N-gram order (1..4).
        model
            "wli" or "char".
        """
        dtag = _norm_dir(direction)
        setag = _norm_se(se)
        mtag = _norm_model(model)

        self._validate(pt, wli, setag, mtag)
        mdl = self._ensure(dtag, setag, mtag, int(n))

        out: List[SentScores] = []
        for s_idx, pt_sent in enumerate(pt):
            p_arr = np.asarray(pt_sent, dtype=np.uint8)[None, :]  # (1, L)
            if mtag == "wli":
                pairs = np.asarray(wli[s_idx], dtype=np.uint8)
                if pairs.ndim != 2 or pairs.shape[1] != 2:
                    raise ValueError("wli sentence must be (L,2)")
                w_arr = pairs[None, :, :]  # (1, L, 2)
                lp   = float(mdl.batch_logp(   p_arr, w_arr, int(n), 0)[0])
                ct   = int(  mdl.batch_count(  p_arr, w_arr, int(n), 0)[0])
                zsum = float(mdl.batch_zsum(   p_arr, w_arr, int(n), 0)[0])
                msum = float(mdl.batch_madsum( p_arr, w_arr, int(n), 0)[0])
            else:
                lp   = float(mdl.batch_logp_char(  p_arr, int(n))[0])
                ct   = int(  mdl.batch_count_char( p_arr, int(n))[0])
                zsum = float(mdl.batch_zsum_char(  p_arr, int(n))[0])
                msum = float(mdl.batch_madsum_char(p_arr, int(n))[0])
            out.append(SentScores(ct, lp, zsum, msum))
        return out

    def score_random(
        self,
        pt: List[List[int]],
        wli: Optional[List[List[List[int]]]],
        direction: DIR,
        se: SE,
        n: int,
        model: MODEL,
        trials: int = 1,
        seed: int = 1234,
    ) -> Dict[str, Any]:
        """
        Randomised baseline (uniform 0..28 letters).
        For WISE: keep 29 at start and 30 at end; randomise interior only.
        Returns dict with 'means' and 'sds' per sentence and 'seconds' timing.
        """
        import time, random
        dtag = _norm_dir(direction)
        setag = _norm_se(se)
        mtag = _norm_model(model)
        self._validate(pt, wli, setag, mtag)
        rng = random.Random(seed)

        per_trial: List[List[SentScores]] = []
        t0 = time.perf_counter()
        for _ in range(trials):
            pt_r: List[List[int]] = []
            for sent in pt:
                L = len(sent)
                if setag == "wise" and L >= 2:
                    row = [29] + [rng.randrange(0, 29) for _ in range(L - 2)] + [30]
                else:
                    row = [rng.randrange(0, 29) for _ in range(L)]
                pt_r.append(row)
            per_trial.append(self.score(pt_r, wli, dtag, setag, n, mtag))
        elapsed = time.perf_counter() - t0

        S = len(pt)
        means: List[Tuple[float, float, float, float]] = []
        sds:   List[Tuple[float, float, float, float]] = []

        for s in range(S):
            cs = [per_trial[t][s].counts_sum  for t in range(trials)]
            ls = [per_trial[t][s].logprob_sum for t in range(trials)]
            zs = [per_trial[t][s].z_sum       for t in range(trials)]
            ms = [per_trial[t][s].madsum      for t in range(trials)]

            def msd(a):
                m = sum(a) / len(a)
                v = sum((x - m) * (x - m) for x in a) / max(1, len(a) - 1)
                return m, math.sqrt(v)

            mc, sc = msd(cs); ml, sl = msd(ls); mz, sz = msd(zs); mm, sm = msd(ms)
            means.append((mc, ml, mz, mm))
            sds.append((sc, sl, sz, sm))
        return {"means": means, "sds": sds, "seconds": elapsed}

    def wli_bigram_logp_and_counts(
        self,
        bigrams: Sequence[Sequence[int]] | np.ndarray,
        contexts: Sequence[Sequence[Sequence[int]]] | np.ndarray,
        *,
        direction: DIR = "rtl",
        se: SE = "nose",
        n: int = 2,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Aggregate raw log-probabilities and counts for WLI bigrams over given contexts.

        Parameters
        ----------
        bigrams :
            Array-like of shape (K, 2) containing rune indices in [0, 29).
        contexts :
            Array-like of shape (C, 2, 2) where each entry is [[pos1, len1], [pos2, len2]].
        direction, se, n :
            Passed to the underlying FastTransitionModel (n should remain 2 here).
        """
        big_arr = np.asarray(bigrams, dtype=np.uint8)
        if big_arr.ndim != 2 or big_arr.shape[1] != 2:
            raise ValueError("bigrams must be array-like with shape (K, 2)")
        ctx_arr = np.asarray(contexts, dtype=np.uint8)
        if ctx_arr.ndim != 3 or ctx_arr.shape[1:] != (2, 2):
            raise ValueError("contexts must be array-like with shape (C, 2, 2)")
        if ctx_arr.shape[0] == 0:
            raise ValueError("contexts must be non-empty")

        dtag = _norm_dir(direction)
        setag = _norm_se(se)
        mdl = self._ensure(dtag, setag, "wli", int(n))

        pt_batch = np.ascontiguousarray(big_arr, dtype=np.uint8)
        K = pt_batch.shape[0]
        logp_acc = np.full(K, -np.inf, dtype=np.float64)
        count_acc = np.zeros(K, dtype=np.float64)

        for ctx in ctx_arr:
            wli_batch = np.broadcast_to(ctx, (K, 2, 2)).copy()
            lp = np.asarray(
                mdl.batch_logp(pt_batch, wli_batch, int(n), 0),
                dtype=np.float64,
            ).reshape(-1)
            ct_vals = np.asarray(
                mdl.batch_count(pt_batch, wli_batch, int(n), 0),
                dtype=np.float64,
            ).reshape(-1)
            logp_acc = np.logaddexp(logp_acc, lp)
            count_acc += ct_vals

        return logp_acc, count_acc

    # ---------- internals ----------

    def _joint_path(self, direction: str, se: str, model: str, n: int) -> Path:
        """
        Resolve joint-table path using index.json pattern for the model.
        Example (char):
          "char/%%MODE%%/char29_joint_%%MODE%%_%%N%%_%%POS%%.bin.zst"
        """
        pat = self.idx.models[_norm_model(model)]["joint_pattern"]
        return expand_pattern(self.root, pat, mode=_norm_dir(direction), pos=_norm_se(se), n=int(n))

    def _ensure(self, direction: str, se: str, model: str, n: int) -> _fastlm.FastTransitionModel:
        key = (_norm_dir(direction), _norm_se(se), _norm_model(model), int(n))
        mdl = getattr(self, "_cache", {}).get(key)
        if mdl is not None:
            return mdl
        path = self._joint_path(*key)
        keys, logp, cnts, mask = _load_bin(path)
        mdl = _fastlm.FastTransitionModel(
            keys, logp, cnts, int(mask),
            self._smooth_mode, self._alpha, self._oov_mode, False
        )
        self._cache[key] = mdl
        return mdl

    @staticmethod
    def _validate(
        pt: List[List[int]],
        wli: Optional[List[List[List[int]]]],
        se: str,
        model: str,
    ) -> None:
        if _norm_model(model) == "wli" and wli is None:
            raise ValueError("WLI model requires wli input")
        if _norm_model(model) == "wli":
            if len(pt) != len(wli):
                raise ValueError("pt and wli must have same number of sentences")
            for s, (p, wl) in enumerate(zip(pt, wli)):
                if len(p) != len(wl):
                    raise ValueError(f"sentence {s}: pt and wli length mismatch")
                for t, pr in enumerate(p):
                    if not (0 <= pr <= 30):
                        raise ValueError(f"pt[{s}][{t}] outside [0..30]")
                for t, (pos, L) in enumerate(wl):
                    if L == 0:
                        if pos != 0:
                            raise ValueError(f"wli[{s}][{t}] tag must be [0,0]")
                        if _norm_se(se) == "wise":
                            if p[t] not in (29, 30):
                                raise ValueError(f"wli tag at {s},{t} must align to 29/30 in pt")
                    else:
                        if not (0 <= pos < L <= 63):
                            raise ValueError(f"wli[{s}][{t}] pos/len out of range")
            if _norm_se(se) == "wise":
                for s, p in enumerate(pt):
                    if p and (p[0] != 29 or p[-1] != 30):
                        raise ValueError(f"WISE sentence {s} must start with 29 and end with 30")
            else:  # NOSE
                for s, p in enumerate(pt):
                    for tok in p:
                        if tok in (29, 30):
                            raise ValueError(f"NOSE sentence {s} must not contain 29/30")
        else:  # char
            if _norm_se(se) == "wise":
                for s, p in enumerate(pt):
                    if p and (p[0] != 29 or p[-1] != 30):
                        raise ValueError(f"WISE sentence {s} must start with 29 and end with 30")
            else:
                for s, p in enumerate(pt):
                    for tok in p:
                        if tok in (29, 30):
                            raise ValueError(f"NOSE sentence {s} must not contain 29/30")
