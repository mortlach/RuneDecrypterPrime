# language_model_prime.py
from __future__ import annotations
import math, time, random, struct
from dataclasses import dataclass
from typing import List, Tuple, Literal, Dict, Any, Optional
from pathlib import Path

import numpy as np
import zstandard as zstd
import _fastlm  # the self-contained C++ extension you compiled (_fastlm.pyd / .so)

DIR   = Literal["fwd","rev","forward","reverse"]
SE    = Literal["wise","nose","WISE","NOSE"]
MODEL = Literal["wli","char","WLI","CHAR"]

@dataclass
class SentScores:
    counts_sum: int
    logprob_sum: float
    z_sum: float
    madsum: float

class LanguageModelPrime:
    """
    High-level scorer for WLI/CHAR models over (FWD/REV × WISE/NOSE × n=1..4).

    - Loads combo .bin.zst files lazily and instantiates _fastlm.FastTransitionModel
      with chosen smoothing/OOV settings (no rebuild needed).
    - Exposes per-sentence scoring for counts / logprob / z-sum / MAD-sum.
    - Provides randomized baselines (uniform letters; WISE keeps 29/30 at ends).
    """

    def __init__(self,
                 bins_dir: str | Path = "./bin_sparse_2",
                 smoothing: str = "auto_gt",   # "none"|"lidstone"|"jeffreys"|"auto_gt"
                 alpha: float = 0.5,           # used if smoothing == "lidstone"
                 oov_policy: str = "floor_min_seen",  # "floor_min_seen"|"lidstone"
                 include_char: bool = True):
        self.bins_dir = Path(bins_dir)
        self.include_char = include_char

        smap = {"none":0, "lidstone":1, "jeffreys":2, "auto_gt":3}
        omap = {"floor_min_seen":0, "lidstone":1}
        if smoothing not in smap: raise ValueError("smoothing must be one of: " + ", ".join(smap))
        if oov_policy not in omap: raise ValueError("oov_policy must be one of: " + ", ".join(omap))

        self._smooth_mode = smap[smoothing]
        self._alpha = float(alpha)
        self._oov_mode = omap[oov_policy]
        self._cache: Dict[Tuple[str,str,str,int], _fastlm.FastTransitionModel] = {}

    # ---------------- Public API ----------------

    def score(self,
              pt: List[List[int]],
              wli: Optional[List[List[List[int]]]],
              direction: DIR, se: SE, n: int, model: MODEL) -> List[SentScores]:
        """
        Per-sentence scoring. Returns List[SentScores] with one entry per sentence.

        - pt: nested int ids (0..30); WISE must begin with 29 and end with 30.
        - wli: nested pairs [pos,len] (required for model="wli"; ignored for "char").
        - direction: "fwd"/"rev" (accepts "forward"/"reverse" too).
        - se: "wise"/"nose" (case-insensitive); NOSE must have a single sentence and no 29/30.
        - n: 1..4
        - model: "wli" or "char"
        """
        dtag = _norm_dir(direction)
        setag = _norm_se(se)
        mtag = _norm_model(model)

        self._validate(pt, wli, setag, mtag)
        mdl = self._ensure(dtag, setag, mtag, int(n))

        out: List[SentScores] = []
        for s_idx, pt_sent in enumerate(pt):
            p_arr = np.asarray(pt_sent, dtype=np.uint8)[None, :]  # (1,L)
            if mtag == "wli":
                pairs = np.asarray(wli[s_idx], dtype=np.uint8)
                if pairs.ndim != 2 or pairs.shape[1] != 2:
                    raise ValueError("wli sentence must be (L,2)")
                w_arr = pairs[None, :, :]  # (1,L,2)
                lp   = float(mdl.batch_logp(p_arr,  w_arr, int(n), 0)[0])
                ct   = int(  mdl.batch_count(p_arr, w_arr, int(n), 0)[0])
                zsum = float(mdl.batch_zsum(p_arr,  w_arr, int(n), 0)[0])
                msum = float(mdl.batch_madsum(p_arr, w_arr, int(n), 0)[0])
            else:
                lp   = float(mdl.batch_logp_char(p_arr, int(n))[0])
                ct   = int(  mdl.batch_count_char(p_arr, int(n))[0])
                zsum = float(mdl.batch_zsum_char(p_arr, int(n))[0])
                msum = float(mdl.batch_madsum_char(p_arr, int(n))[0])
            out.append(SentScores(ct, lp, zsum, msum))
        return out

    def score_random(self,
                     pt: List[List[int]],
                     wli: Optional[List[List[List[int]]]],
                     direction: DIR, se: SE, n: int, model: MODEL,
                     trials: int = 1, seed: int = 1234) -> Dict[str, Any]:
        """
        Randomized baseline with N trials (uniform 0..28 letters).
        - WISE: keep 29 at start and 30 at end; randomize interior only.
        Returns dict with 'means' and 'sds' per sentence (tuples on counts/logprob/z/madsum)
        and 'seconds' timing.
        """
        dtag = _norm_dir(direction)
        setag = _norm_se(se)
        mtag = _norm_model(model)
        self._validate(pt, wli, setag, mtag)
        rng = random.Random(seed)

        per_trial: List[List[SentScores]] = []
        t0 = time.perf_counter()
        for t in range(trials):
            pt_r: List[List[int]] = []
            for sent in pt:
                L = len(sent)
                if setag == "wise" and L >= 2:
                    row = [29] + [rng.randrange(0,29) for _ in range(L-2)] + [30]
                else:
                    row = [rng.randrange(0,29) for _ in range(L)]
                pt_r.append(row)
            per_trial.append(self.score(pt_r, wli, dtag, setag, n, mtag))
        elapsed = time.perf_counter() - t0

        # Aggregate per sentence
        S = len(pt)
        means: List[Tuple[float,float,float,float]] = []
        sds:   List[Tuple[float,float,float,float]] = []
        for s in range(S):
            cs = [per_trial[t][s].counts_sum  for t in range(trials)]
            ls = [per_trial[t][s].logprob_sum for t in range(trials)]
            zs = [per_trial[t][s].z_sum       for t in range(trials)]
            ms = [per_trial[t][s].madsum      for t in range(trials)]
            def msd(a):
                m = sum(a)/len(a)
                v = sum((x-m)*(x-m) for x in a)/max(1, len(a)-1)
                return m, math.sqrt(v)
            mc, sc = msd(cs); ml, sl = msd(ls); mz, sz = msd(zs); mm, sm = msd(ms)
            means.append((mc, ml, mz, mm))
            sds.append((sc, sl, sz, sm))
        return {"means": means, "sds": sds, "seconds": elapsed}

    # ---------------- Internals ----------------

    def _ensure(self, direction: str, se: str, model: str, n: int) -> _fastlm.FastTransitionModel:
        key = (direction, se, model, n)
        mdl = self._cache.get(key)
        if mdl is not None:
            return mdl
        path = self._fname(direction, se, model, n)
        keys, logp, cnts, mask = _load_bin(path)
        mdl = _fastlm.FastTransitionModel(keys, logp, cnts, int(mask),
                                          self._smooth_mode, self._alpha, self._oov_mode, False)
        self._cache[key] = mdl
        return mdl

    def _fname(self, direction: str, se: str, model: str, n: int) -> Path:
        tag = "wli29_joint" if model == "wli" else "char29_joint"
        return self.bins_dir / f"{tag}_{direction}_{n}_{se}.bin.zst"

    @staticmethod
    def _validate(pt: List[List[int]],
                  wli: Optional[List[List[List[int]]]],
                  se: str, model: str) -> None:
        if model == "wli" and wli is None:
            raise ValueError("WLI model requires wli input")
        if model == "wli":
            if len(pt) != len(wli):
                raise ValueError("pt and wli must have same number of sentences")
            for s,(p,wl) in enumerate(zip(pt, wli)):
                if len(p) != len(wl):
                    raise ValueError(f"sentence {s}: pt and wli length mismatch")
                for t, pr in enumerate(p):
                    if not (0 <= pr <= 30):
                        raise ValueError(f"pt[{s}][{t}] outside [0..30]")
                for t,(pos,L) in enumerate(wl):
                    if L == 0:
                        if pos != 0:
                            raise ValueError(f"wli[{s}][{t}] tag must be [0,0]")
                        if se == "wise":
                            if p[t] not in (29,30):
                                raise ValueError(f"wli tag at {s},{t} must align to 29/30 in pt")
                    else:
                        if not (0 <= pos < L <= 63):
                            raise ValueError(f"wli[{s}][{t}] pos/len out of range")
            if se == "wise":
                for s,p in enumerate(pt):
                    if p and (p[0] != 29 or p[-1] != 30):
                        raise ValueError(f"WISE sentence {s} must start with 29 and end with 30")
            else:  # NOSE
                for s, p in enumerate(pt):
                    for tok in p:
                        if tok in (29, 30):
                            raise ValueError(
                                f"NOSE sentence {s} must not contain 29/30")
        else:  # char
            if se == "wise":
                for s,p in enumerate(pt):
                    if p and (p[0] != 29 or p[-1] != 30):
                        raise ValueError(f"WISE sentence {s} must start with 29 and end with 30")
            else:
                for s, p in enumerate(pt):
                    for tok in p:
                        if tok in (29, 30):
                            raise ValueError(
                                f"NOSE sentence {s} must not contain 29/30")

# ---------------- Helpers ----------------

def _norm_dir(direction: DIR) -> str:
    if direction in ("fwd","forward"): return "fwd"
    if direction in ("rev","reverse"): return "rev"
    raise ValueError("direction must be 'fwd'/'forward' or 'rev'/'reverse'")

def _norm_se(se: SE) -> str:
    s = str(se).lower()
    if s in ("wise","nose"): return s
    raise ValueError("se must be 'wise' or 'nose'")

def _norm_model(model: MODEL) -> str:
    m = str(model).lower()
    if m in ("wli","char"): return m
    raise ValueError("model must be 'wli' or 'char'")

def _load_bin(path: Path):
    """
    Read combo .bin.zst:
      header "<4sBHIff" (magic='WLI0'), then keys:uint64[M], logp:float32[M], cnts:uint64[M]
    Returns C-contiguous numpy arrays and mask (uint32).
    """
    if not path.exists():
        raise FileNotFoundError(f"LM file not found: {path}")
    comp = path.read_bytes()
    dec  = zstd.ZstdDecompressor().decompress(comp)
    buf  = memoryview(dec)
    off  = 0
    magic, version, lg_size, _zero, _mu_stub, _sigma_stub = struct.unpack_from("<4sBHIff", buf, off)
    off += struct.calcsize("<4sBHIff")
    if magic != b"WLI0":
        raise ValueError(f"Bad magic in {path}")
    table_size = 1 << lg_size
    mask = np.uint32((1 << lg_size) - 1)

    keys = np.frombuffer(buf[off: off + 8*table_size], dtype="<u8"); off += 8*table_size
    logp = np.frombuffer(buf[off: off + 4*table_size], dtype="<f4"); off += 4*table_size
    cnts = np.frombuffer(buf[off: off + 8*table_size], dtype="<u8"); off += 8*table_size

    # Copy to C-contiguous arrays that are writable (C++ may write smoothed logp)
    return np.array(keys, copy=True), np.array(logp, copy=True), np.array(cnts, copy=True), mask

# ---------------- Example test harness ----------------
if __name__ == "__main__":
    from test_data import (PT_REV_NOSE,    WLI_REV_NOSE,    PT_REV_WISE,    WLI_REV_WISE,    PT_FWD_NOSE,    WLI_FWD_NOSE,    PT_FWD_WISE,    WLI_FWD_WISE)

    # Instantiate scorer (point to your combo bins)
    lm = LanguageModelPrime(
        bins_dir="./bin_spares_2",     # <-- set to your folder with char29_joint_* and/or wli29_joint_*
        smoothing="auto_gt",    # "none"|"lidstone"|"jeffreys"|"auto_gt"
        alpha=0.5,              # used only if smoothing="lidstone"
        oov_policy="floor_min_seen",
        include_char=True
    )

    # Example: CHAR 3-gram, FWD/WISE
    print("=== CHAR 3-gram FWD WISE (real) ===")
    res = lm.score(PT_FWD_WISE, None, "fwd", "wise", 3, "char")
    for i, s in enumerate(res):
        print(f"sent{i}: count={s.counts_sum}  logp={s.logprob_sum:.4f}  zsum={s.z_sum:.4f}  madsum={s.madsum:.4f}")

    print("=== CHAR 3-gram FWD WISE (random x5) ===")
    rb = lm.score_random(PT_FWD_WISE, None, "fwd", "wise", 3, "char", trials=5, seed=42)
    for i, (m, sd) in enumerate(zip(rb["means"], rb["sds"])):
        mc, ml, mz, mm = m
        sc, sl, sz, sm = sd
        print(f"sent{i}: mean(count)={mc:.1f}±{sc:.1f}  "
              f"mean(logp)={ml:.3f}±{sl:.3f}  mean(zsum)={mz:.3f}±{sz:.3f}  mean(madsum)={mm:.3f}±{sm:.3f}")
    print(f"time: {rb['seconds']:.3f}s")





