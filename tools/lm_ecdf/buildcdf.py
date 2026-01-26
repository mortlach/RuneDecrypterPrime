#!/usr/bin/env python3
"""
ECDF builder for LanguageModelPrime window scores.

Reads:   ./lmprime_out/scores/<book>_<dir>_<se>_<model>_n{n}_win{W}.npz
Writes:  ./lmprime_out/ecdf/<dir>_<se>_<model>_n{n}_win{W}_{stat}.npz
         ./lmprime_out/ecdf/index.json

Design goals
------------
• Combine data from multiple books without loss.
• Build per-bucket ECDFs (dir × se × model × n × win × stat).
• Canonical normalization = divide by total_eval (WISE=W+2, NOSE=W).
  If source files used legacy “/interior”, rescale at build-time using
  scale = interior / total (NOSE scale==1).
• Compact artifacts (grid,q float32) for C++/GPU use.
• Low‑risk refinements to reduce tiny KS deviations in WISE/WLI:
    – Quantile grids built in float64, downcast at save time.
    – Tail‑dense mesh (logistic warping of q) for WISE/WLI buckets.
    – Strictly‑increasing grid enforced by minimal nudges.

Stats columns in `scores`:
    scores[:,0] = logp_avg
    scores[:,1] = zsum_avg
    scores[:,2] = madsum_avg

Coverage columns in `coverage`:
    coverage[:,0] = denom_interior
    coverage[:,1] = total_eval
"""

from __future__ import annotations
import json, time, os
from pathlib import Path
from typing import Dict, Tuple, List, Iterable, Optional
import numpy as np

# =========================
# ====== CONFIG (edit) ====
# =========================

# Where the scorer wrote per-window results:
SCORES_DIR = Path("./lmprime_out/scores")

# Where we will write ECDF tables + index:
ECDF_OUT_DIR = Path("./lmprime_out/ecdf")

# Which statistics to build ECDFs for (subset of: logp, zsum, madsum)
STATS = ("zsum", "madsum", "logp")

# Number of ECDF knots (quantile grid size). Acts like “bins” the user can choose.
NUM_KNOTS = 4096

# If True, run extra assertions (NOSE scale==1; WISE total==interior+2 for fixed W)
STRICT_CHECKS = False

# Filter windows with very low corpus counts (diagnostic). 0 → keep all.
MIN_COUNTS = 0

# How to interpret averages stored in the NPZ “scores”:
#   "auto"      : read file meta["wise_norm"] if present; default to "interior"
#   "interior"  : assume averages were divided by denom_interior (legacy)
#   "total"     : assume averages were divided by total_eval (canonical)
WISE_NORM_IN_FILES = "auto"   # "auto" | "interior" | "total"

# ===== ECDF refinements (low‑risk) =====
ECDF_BUILD_DTYPE      = np.float64   # build quantiles in float64
ECDF_SAVE_DTYPE       = np.float32   # store as float32
ECDF_TAIL_MESH_DEFAULT= "linear"     # default mesh for most buckets
ECDF_TAIL_MESH_WISE_WLI = "logistic" # mesh used for (se=wise, model=wli)
ECDF_LOGISTIC_A       = 6.0          # tail density parameter (4..8 typical)
ECDF_ENFORCE_STRICT   = True         # nudge ties to strictly increasing
ECDF_STRICT_METHOD    = "nextafter"  # "nextafter" | "epsilon"

# =========================
# ====== UTILITIES ========
# =========================

STATS_IDX = {"logp": 0, "zsum": 1, "madsum": 2}

def now_ts() -> float:
    return time.time()

def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def parse_score_filename(fp: Path) -> Optional[Dict]:
    """
    Expect pattern: <book>_<dir>_<se>_<model>_n{n}_win{W}.npz
    Book name can contain underscores; parse from the tail.
    """
    name = fp.name
    if not name.endswith(".npz"):
        return None
    base = name[:-4]
    parts = base.split("_")
    if len(parts) < 6:
        return None
    try:
        win_tok = parts[-1]         # e.g., win10
        n_tok   = parts[-2]         # e.g., n4
        model   = parts[-3]         # e.g., wli|char
        se      = parts[-4]         # wise|nose
        d       = parts[-5]         # fwd|rev
        book    = "_".join(parts[:-5])

        if not win_tok.startswith("win") or not n_tok.startswith("n"):
            return None

        W = int(win_tok[3:])
        n = int(n_tok[1:])
        if d not in ("fwd", "rev"): return None
        if se not in ("wise", "nose"): return None
        if model not in ("wli", "char"): return None
        return {"book": book, "dir": d, "se": se, "model": model, "n": n, "win": W}
    except Exception:
        return None

# =========================
# ====== ECDF helpers =====
# =========================

def make_mesh(num_knots: int,
              mesh: str = "linear",
              logistic_a: float = 6.0,
              dtype = np.float64) -> np.ndarray:
    """
    Returns q in (0,1) of length num_knots with optional tail densification.
    """
    if mesh == "linear":
        q = np.linspace(0.0, 1.0, num_knots, dtype=dtype)
        eps = np.finfo(dtype).eps
        q[0]  = max(q[0],  eps)
        q[-1] = min(q[-1], 1.0 - eps)
        return q

    if mesh == "logistic":
        t = np.linspace(-logistic_a, logistic_a, num_knots, dtype=dtype)
        y = 1.0 / (1.0 + np.exp(-t))              # (0,1)
        y0, y1 = y[0], y[-1]
        q = (y - y0) / (y1 - y0)                  # re-normalize to (0,1)
        eps = np.finfo(dtype).eps
        q[0]  = max(q[0],  eps)
        q[-1] = min(q[-1], 1.0 - eps)
        return q

    raise ValueError(f"Unknown mesh '{mesh}'")

def enforce_strictly_increasing(grid: np.ndarray,
                                method: str = "nextafter") -> np.ndarray:
    """
    Ensure grid is strictly increasing by minimal nudges in float64.
    Operates in-place and returns the same array.
    """
    np.maximum.accumulate(grid, out=grid)
    if method == "nextafter":
        for i in range(1, grid.shape[0]):
            if grid[i] <= grid[i-1]:
                grid[i] = np.nextafter(grid[i-1], np.inf)
    elif method == "epsilon":
        tiny = np.finfo(grid.dtype).eps
        for i in range(1, grid.shape[0]):
            if grid[i] <= grid[i-1]:
                step = max(abs(grid[i-1]), 1.0) * tiny
                grid[i] = grid[i-1] + step
    else:
        raise ValueError(f"Unknown strict method '{method}'")
    return grid

def build_ecdf_table(values: np.ndarray,
                     num_knots: int,
                     mesh: str = "linear",
                     logistic_a: float = 6.0,
                     enforce_strict: bool = True,
                     strict_method: str = "nextafter",
                     build_dtype = np.float64,
                     save_dtype  = np.float32) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build a monotone piecewise-linear ECDF table:
      returns (grid_save_dtype, q_save_dtype)
    """
    if values.size == 0:
        q = make_mesh(num_knots, mesh="linear", dtype=build_dtype)
        grid = np.linspace(0.0, 1.0, num_knots, dtype=build_dtype)
        if enforce_strict:
            enforce_strictly_increasing(grid, method=strict_method)
        return grid.astype(save_dtype), q.astype(save_dtype)

    q = make_mesh(num_knots, mesh=mesh, logistic_a=logistic_a, dtype=build_dtype)

    grid = np.quantile(values.astype(build_dtype, copy=False),
                       q, method="linear").astype(build_dtype, copy=False)

    if enforce_strict:
        enforce_strictly_increasing(grid, method=strict_method)

    return grid.astype(save_dtype), q.astype(save_dtype)

# =========================
# ====== CORE BUILDER =====
# =========================

class LmprimeECDFBuilder:
    """
    Discovers buckets from SCORES_DIR and writes ECDF tables into ECDF_OUT_DIR.

    Output per bucket/stat:
      <dir>_<se>_<model>_n{n}_win{W}_{stat}.npz
        - grid: float32 [NUM_KNOTS]
        - q   : float32 [NUM_KNOTS]
        - meta: JSON string (np.array(dtype=object)) with provenance
    Also writes `index.json` with a manifest of all artifacts.
    """

    def __init__(self,
                 scores_dir: Path = SCORES_DIR,
                 ecdf_out_dir: Path = ECDF_OUT_DIR,
                 stats: Iterable[str] = STATS,
                 num_knots: int = NUM_KNOTS,
                 wise_norm_in_files: str = WISE_NORM_IN_FILES,
                 min_counts: int = MIN_COUNTS,
                 strict_checks: bool = STRICT_CHECKS):
        self.scores_dir = Path(scores_dir)
        self.ecdf_out_dir = Path(ecdf_out_dir)
        self.stats = tuple(stats)
        self.num_knots = int(num_knots)
        self.wise_norm_in_files = wise_norm_in_files
        self.min_counts = int(min_counts)
        self.strict_checks = bool(strict_checks)
        safe_mkdir(self.ecdf_out_dir)

        for s in self.stats:
            if s not in STATS_IDX:
                raise ValueError(f"Unknown stat '{s}'. Valid: {list(STATS_IDX)}")

        if self.wise_norm_in_files not in ("auto","interior","total"):
            raise ValueError("wise_norm_in_files must be 'auto'|'interior'|'total'")

    # ───────── Discovery ─────────
    def discover_buckets(self) -> Dict[Tuple[str,str,str,int,int], List[Path]]:
        """
        Group files by (dir, se, model, n, win). Return mapping → list of files.
        """
        buckets: Dict[Tuple[str,str,str,int,int], List[Path]] = {}
        if not self.scores_dir.exists():
            raise FileNotFoundError(f"SCORES_DIR not found: {self.scores_dir}")

        for fp in self.scores_dir.glob("*.npz"):
            meta = parse_score_filename(fp)
            if not meta:
                continue
            key = (meta["dir"], meta["se"], meta["model"], meta["n"], meta["win"])
            buckets.setdefault(key, []).append(fp)

        for k in buckets:
            buckets[k].sort()
        return buckets

    # ───────── Loading/normalization ─────────
    def _read_file_meta_norm(self, arr: np.lib.npyio.NpzFile, se: str) -> str:
        """
        Decide how values in `scores` were averaged in the file.
        Returns "interior" or "total".
        """
        if se == "nose":
            return "total"

        policy = self.wise_norm_in_files
        if policy in ("interior", "total"):
            return policy

        # auto: attempt to read meta["wise_norm"]; default to "interior"
        try:
            meta_obj = arr["meta"]
            meta_json = json.loads(str(np.array(meta_obj).item()))
            norm = meta_json.get("wise_norm", "interior")
            if norm not in ("interior","total"):
                norm = "interior"
            return norm
        except Exception:
            return "interior"

    def _load_values_from_file(self, fp: Path, stat_idx: int,
                               expected: Dict) -> np.ndarray:
        """
        Load one file and return a 1D float32 array of normalized values for given stat.
        Applies:
          • post-hoc rescale for WISE if file stored /interior,
          • optional min_counts filtering,
          • strict sanity checks (optional).
        """
        arr = np.load(fp, allow_pickle=True)  # allow_pickle True for 'meta'
        scores   = arr["scores"]    # [W,3]
        coverage = arr["coverage"]  # [W,2]
        counts   = arr["counts"]    # [W]

        if scores.ndim != 2 or scores.shape[1] != 3:
            raise ValueError(f"{fp.name}: scores has unexpected shape {scores.shape}")
        if coverage.ndim != 2 or coverage.shape[1] != 2:
            raise ValueError(f"{fp.name}: coverage has unexpected shape {coverage.shape}")
        if counts.shape[0] != scores.shape[0]:
            raise ValueError(f"{fp.name}: counts length {counts.shape[0]} ≠ scores {scores.shape[0]}")

        vals = scores[:, stat_idx].astype(np.float32, copy=True)
        interior = coverage[:, 0].astype(np.float32, copy=False)
        total    = coverage[:, 1].astype(np.float32, copy=False)

        if self.strict_checks:
            if expected["se"] == "nose":
                if not (np.all(interior == total) and np.all(interior == expected["win"])):
                    raise AssertionError(f"{fp.name}: NOSE coverage mismatch")
            else:
                bad = np.where(~(total == (interior + 2)))[0]
                if bad.size:
                    raise AssertionError(f"{fp.name}: WISE coverage mismatch on {bad.size} windows")

        norm_src = self._read_file_meta_norm(arr, expected["se"])
        if norm_src == "interior":
            with np.errstate(divide="ignore", invalid="ignore"):
                scale = np.where(total > 0, interior / total, 1.0).astype(np.float32)
            vals *= scale
        # else already per total_eval

        if self.min_counts > 0:
            mask = counts >= self.min_counts
            if mask.any():
                vals = vals[mask]
            else:
                vals = np.empty((0,), dtype=np.float32)

        return vals

    # ───────── Saving ─────────
    def _save_bucket_stat(self, key: Tuple[str,str,str,int,int], stat: str,
                          grid: np.ndarray, q: np.ndarray, meta: Dict):
        d, se, model, n, win = key
        safe_mkdir(self.ecdf_out_dir)
        out = self.ecdf_out_dir / f"{d}_{se}_{model}_n{n}_win{win}_{stat}.npz"
        payload_meta = json.dumps(meta)
        np.savez_compressed(out,
                            grid=grid.astype(ECDF_SAVE_DTYPE, copy=False),
                            q=q.astype(ECDF_SAVE_DTYPE, copy=False),
                            meta=np.array(payload_meta, dtype=object))
        print(f"  → {out.name}  ({grid.size} knots)")

    # ───────── Build one bucket ─────────
    def build_bucket(self, key: Tuple[str,str,str,int,int], files: List[Path]) -> List[Path]:
        d, se, model, n, win = key
        print(f"\n[{d}/{se}/{model}/n={n}/W={win}]  files={len(files)}")
        t0 = now_ts()

        per_stat_vals: Dict[str, List[np.ndarray]] = {s: [] for s in self.stats}
        total_windows = 0
        contributing = []

        expected = {"dir": d, "se": se, "model": model, "n": n, "win": win}

        for fp in files:
            try:
                for stat in self.stats:
                    idx = STATS_IDX[stat]
                    vals = self._load_values_from_file(fp, idx, expected)
                    if vals.size:
                        per_stat_vals[stat].append(vals)
                with np.load(fp, allow_pickle=True) as arr:
                    total_windows += int(arr["scores"].shape[0])
                contributing.append(fp.name)
            except Exception as e:
                print(f"    ! Skipping {fp.name}: {e}")

        built = 0
        for stat in self.stats:
            if per_stat_vals[stat]:
                values = np.concatenate(per_stat_vals[stat], axis=0)
            else:
                values = np.empty((0,), dtype=np.float32)

            # Choose mesh: densify tails for WISE/WLI only (low-risk tweak)
            mesh = ECDF_TAIL_MESH_DEFAULT
            if se == "wise" and model == "wli":
                mesh = ECDF_TAIL_MESH_WISE_WLI

            grid, q = build_ecdf_table(
                values,
                num_knots      = self.num_knots,
                mesh           = mesh,
                logistic_a     = ECDF_LOGISTIC_A,
                enforce_strict = ECDF_ENFORCE_STRICT,
                strict_method  = ECDF_STRICT_METHOD,
                build_dtype    = ECDF_BUILD_DTYPE,
                save_dtype     = ECDF_SAVE_DTYPE,
            )

            meta = {
                "builder": "LmprimeECDFBuilder",
                "builder_version": "1.1",
                "created_ts": now_ts(),
                "dir": d, "se": se, "model": model, "n": n, "win": win,
                "stat": stat,
                "num_knots": self.num_knots,
                "min_counts": self.min_counts,
                "wise_norm_in_files": self.wise_norm_in_files,
                "canonical_norm": "total",  # values normalized per total_eval at build time
                "files": contributing,
                "source_windows_total": total_windows,
                "used_values": int(values.size),
                "quantile_mesh": mesh,
                "logistic_a": float(ECDF_LOGISTIC_A),
                "build_dtype": str(np.dtype(ECDF_BUILD_DTYPE)),
                "save_dtype": str(np.dtype(ECDF_SAVE_DTYPE)),
                "enforce_strict": bool(ECDF_ENFORCE_STRICT),
                "strict_method": ECDF_STRICT_METHOD,
                "notes": "grid[k] is the score where ECDF==q[k]; use linear interpolation."
            }
            self._save_bucket_stat(key, stat, grid, q, meta)
            built += 1

        print(f"  ✓ built {built} stats in {now_ts()-t0:.2f}s; used_values per stat shown above.")
        return []



    # ───────── Build all ─────────
    def build_all(self) -> Dict:
        buckets = self.discover_buckets()
        if not buckets:
            print("No score files found; nothing to do.")
            return {}

        index = {
            "created_ts": now_ts(),
            "scores_dir": str(self.scores_dir.resolve()),
            "ecdf_out_dir": str(self.ecdf_out_dir.resolve()),
            "num_knots": self.num_knots,
            "min_counts": self.min_counts,
            "wise_norm_in_files": self.wise_norm_in_files,
            "strict_checks": self.strict_checks,
            "build_dtype": str(np.dtype(ECDF_BUILD_DTYPE)),
            "save_dtype": str(np.dtype(ECDF_SAVE_DTYPE)),
            "tail_mesh_default": ECDF_TAIL_MESH_DEFAULT,
            "tail_mesh_wise_wli": ECDF_TAIL_MESH_WISE_WLI,
            "logistic_a": float(ECDF_LOGISTIC_A),
            "enforce_strict": bool(ECDF_ENFORCE_STRICT),
            "strict_method": ECDF_STRICT_METHOD,
            "buckets": []
        }

        for key, files in sorted(buckets.items()):
            d, se, model, n, win = key
            self.build_bucket(key, files)
            index["buckets"].append({
                "dir": d, "se": se, "model": model, "n": n, "win": win,
                "stats": list(self.stats),
                "artifact_prefix": f"{d}_{se}_{model}_n{n}_win{win}_<stat>.npz",
                "files": [f.name for f in files]
            })

        manifest = self.ecdf_out_dir / "index.json"
        with manifest.open("w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=2)
        print(f"\n✔ index written → {manifest}")
        return index

# =========================
# ===== RUNTIME UTIL ======
# =========================

class ECDFNormalizer:
    """
    Small helper to apply saved ECDF tables.
    Usage:
        norm = ECDFNormalizer(ECDF_OUT_DIR)
        pct = norm.percentile(x, d='fwd', se='wise', model='wli', n=4, win=10, stat='zsum')
        energy = norm.energy(pct)  # -log(1-p)
    """
    def __init__(self, ecdf_out_dir: Path = ECDF_OUT_DIR):
        self.root = Path(ecdf_out_dir)
        if not self.root.exists():
            raise FileNotFoundError(self.root)

    def _path(self, d: str, se: str, model: str, n: int, win: int, stat: str) -> Path:
        return self.root / f"{d}_{se}_{model}_n{n}_win{win}_{stat}.npz"

    def load_table(self, d: str, se: str, model: str, n: int, win: int, stat: str):
        fp = self._path(d,se,model,n,win,stat)
        arr = np.load(fp, allow_pickle=True)
        grid = arr["grid"].astype(np.float32, copy=False)
        q    = arr["q"].astype(np.float32, copy=False)
        return grid, q

    @staticmethod
    def percentile_of(grid: np.ndarray, q: np.ndarray, x: np.ndarray | float) -> np.ndarray:
        """
        Map raw scores → percentile using piecewise-linear interpolation.
        """
        return np.interp(x, grid, q, left=0.0, right=1.0).astype(np.float32)

    def percentile(self, x: np.ndarray | float, *, d: str, se: str, model: str, n: int, win: int, stat: str) -> np.ndarray:
        grid, q = self.load_table(d, se, model, n, win, stat)
        return self.percentile_of(grid, q, x)

    @staticmethod
    def energy(pct: np.ndarray | float, eps: float = 1e-9) -> np.ndarray:
        """
        Convert percentile to bounded, convex “energy” for optimizers:
            E = -log(1 - pct + eps)
        """
        p = np.clip(pct, 0.0, 1.0, dtype=np.float32)
        return -np.log(1.0 - p + eps).astype(np.float32)

    @staticmethod
    def probit(pct: np.ndarray | float, eps: float = 1e-9) -> np.ndarray:
        """
        Optional: probit (Φ^-1) mapping to z-like scores.
        """
        try:
            from scipy.stats import norm
        except Exception as e:
            raise RuntimeError("scipy is required for probit()") from e
        p = np.clip(pct, eps, 1.0 - eps).astype(np.float32)
        return norm.ppf(p).astype(np.float32)



# =========================
# ======== MAIN ===========
# =========================

if __name__ == "__main__":
    print(f"▶ Building ECDFs from: {SCORES_DIR.resolve()}")
    print(f"  → Output to: {ECDF_OUT_DIR.resolve()}")
    print(f"  stats={STATS}, knots={NUM_KNOTS}, min_counts={MIN_COUNTS}, wise_norm_in_files='{WISE_NORM_IN_FILES}'")
    print(f"  build_dtype={np.dtype(ECDF_BUILD_DTYPE)}, save_dtype={np.dtype(ECDF_SAVE_DTYPE)}, "
          f"strict={ECDF_ENFORCE_STRICT}/{ECDF_STRICT_METHOD}, "
          f"mesh_default={ECDF_TAIL_MESH_DEFAULT}, mesh_wise_wli={ECDF_TAIL_MESH_WISE_WLI}, "
          f"logistic_a={ECDF_LOGISTIC_A}")
    t0 = time.time()
    builder = LmprimeECDFBuilder(
        scores_dir=SCORES_DIR,
        ecdf_out_dir=ECDF_OUT_DIR,
        stats=STATS,
        num_knots=NUM_KNOTS,
        wise_norm_in_files=WISE_NORM_IN_FILES,
        min_counts=MIN_COUNTS,
        strict_checks=STRICT_CHECKS
    )
    index = builder.build_all()
    print(f"✔ Done in {time.time()-t0:.2f}s")
