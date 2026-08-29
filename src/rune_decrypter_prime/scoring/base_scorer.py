# ============================================================
# rune_decrypter_prime/scoring/base_scorer.py   (Abstract scorer API)
# Minimal, stable contract for all scoring backends.
# Now imports the strict Enums used by concrete scorers.
# ============================================================
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence, Dict, Tuple, Optional
import re

from rune_decrypter_prime.core.types import (
    Direction,
    SeMode,
)

# --- Shared constants used by concrete scorers ---
STAT_KEYS: Tuple[str, ...] = ("logp", "zsum", "madsum")
WIN_FIXED: int = 10  # v1 assumption: all pct.* scorers use win=10

# Accepts: "family.stat" or "family.stat.win<k>" (legacy helpers kept for callers that still use strings)
_OBJ_RE = re.compile(r'^(?P<family>[A-Za-z_]+)\.(?P<stat>[A-Za-z_]+)(?:\.win(?P<win>\d+))?$')

def parse_objective(obj: str) -> Tuple[str, Optional[str], Optional[int]]:
    """
    Return (family, stat, win_hint).

    Examples:
      "pct.logp"         -> ("pct", "logp", None)
      "pct.logp.win10"   -> ("pct", "logp", 10)
      "energy.logp"      -> ("energy", "logp", None)
    """
    s = (obj or "").strip().lower()
    m = _OBJ_RE.match(s)
    if not m:
        parts = s.split(".", 1)
        fam = parts[0] if parts else s
        stat = parts[1] if len(parts) > 1 else None
        return fam, stat, None
    fam = m.group("family")
    stat = m.group("stat")
    win_str = m.group("win")
    return fam, stat, (int(win_str) if win_str is not None else None)


def normalize_objective(obj: str, default_win: int) -> str:
    """
    Canonicalise objective spellings to: 'pct.logp.win{default_win}' for pct/logp-ish inputs.

    Rules:
      - '' or None           -> pct.logp.win{default_win}
      - 'pct.logp'           -> pct.logp.win{default_win}
      - 'pct.logp.winK'      -> as-is
      - 'energy.logp' alias  -> pct.logp.win{default_win}
      - otherwise            -> lowercased original (non-standard; handled by scorers)
    """
    if not obj:
        return f"pct.logp.win{int(default_win)}"
    o = str(obj).strip().lower()
    if o in {"energy.logp", "energy", "logp.energy"}:
        return f"energy.logp.win{int(default_win)}"
    if o.startswith("pct.logp.win"):
        return o
    if o == "pct.logp":
        return f"pct.logp.win{int(default_win)}"
    fam, stat, win_hint = parse_objective(o)
    if fam == "pct" and stat == "logp":
        return f"pct.logp.win{int(win_hint if win_hint is not None else default_win)}"
    return o  # non-standard: leave to concrete scorer


class BaseScorer(ABC):
    """
    Minimal scoring contract used by the solver. All concrete scorers must:
      - implement score() for a single plaintext
      - implement batch_score() for a batch (same L across items)
      - expose telemetry() with impl/device/dtype for logging & tests

    This base intentionally stays light; concrete scorers own the math.
    """

    @abstractmethod
    def score(self, plaintext: Iterable[int], wli_windows: Any | None = None) -> float:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def batch_score(self, pts: Sequence[Iterable[int]], wlis: Any | None = None):  # -> np.ndarray[float32]
        raise NotImplementedError

    def __call__(self, plaintexts: Any, wli_windows: Any | None = None):
        return self.score(plaintexts, wli_windows)

    def supports_raw(self) -> bool:
        """Return True if this scorer provides real raw scores."""
        return False

    def score_with_raw(self, plaintext: Iterable[int], wli_windows: Any | None = None) -> Tuple[float, float]:
        """
        Optional: return (primary_score, raw_score). Defaults to primary for both.
        Concrete scorers can override for raw logp support.
        """
        pct = float(self.score(plaintext, wli_windows))
        return pct, pct

    def batch_score_with_raw(self, pts: Sequence[Iterable[int]], wlis: Any | None = None) -> Tuple[Any, Any]:
        """
        Optional: return (primary_scores, raw_scores). Defaults to primary for both.
        Concrete scorers can override for raw logp support.
        """
        pct = self.batch_score(pts, wlis)
        try:
            raw = pct.copy()
        except Exception:
            raw = pct
        return pct, raw

    def last_stats(self):
        """Return per-call stats recorded by the last score()/batch_score() call, if any."""
        return getattr(self, "_last_stats", {}) or {}

    def telemetry(self):
        """Structured info for run logger / dashboards. Implementation may extend."""
        return getattr(self, "_telemetry", {}) or {}

    # --- tiny shared helper for telemetry (no-throw, in-place) ---
    # --- tiny shared helper for telemetry (no-throw, in-place) ---
    def _stash_stats(self, dtype: str | None = None, **stats):
        """
        Best-effort: merge stats into self._telemetry and update a per-call snapshot
        at self._last_stats. This keeps the public contract used by tests:

          • scorer.last_stats() -> {'score_mean', 'score_std', 'n_windows', ...}
          • scorer.telemetry()  -> {..., same stats merged in ...}

        Telemetry must never interfere with core logic: no exceptions propagate.
        """
        try:
            # ensure holders exist
            tele = self.__dict__.setdefault("_telemetry", {})
            if dtype is not None:
                tele["dtype"] = str(dtype)

            if stats:
                # 1) update telemetry (merge)
                from rune_decrypter_prime.utils.telemetry import stash as _tstash
                _tstash(tele, **stats)

                # 2) publish a fresh per-call snapshot for tests / callers
                #    (replace, don't accumulate across different calls)
                self.__dict__["_last_stats"] = dict(stats)
        except Exception:
            # Never let telemetry affect scoring
            pass

    # Require and resolve ObjectiveSpec(PCT|ENERGY, LOGP, win=K). Sets self.win and returns K.
    def _require_objective_pct_logp_win(self) -> int:
        """
        Enforce the v1 objective contract:
          - objective is an ObjectiveSpec with family='pct' and stat='logp'
          - win (K) is taken from the spec; if missing, fall back to self.win (default 10)
        Returns the resolved window K as int and updates self.win to K.
        Raises:
          TypeError / ValueError if the contract is violated.
        """
        obj = getattr(self, "objective", None)
        # Must be an ObjectiveSpec-like object
        try:
            fam = getattr(obj, "family")
            stat = getattr(obj, "stat")
            win = getattr(obj, "win", None)
        except Exception as exc:
            raise TypeError("objective must be an ObjectiveSpec on the scorer") from exc

        # Compare via .value if present (Enum), else str()
        fam_val = getattr(fam, "value", str(fam)).lower()
        stat_val = getattr(stat, "value", str(stat)).lower()
        if fam_val not in ("pct", "energy") or stat_val != "logp":
            raise ValueError(f"unsupported objective: {obj!r} (expected pct.logp.winK or energy.logp.winK)")

        k = int(win) if (win is not None) else int(getattr(self, "win", 10))
        # Keep base/state coherent
        try:
            self.win = k
        except Exception:
            pass
        return k

    # --- adapters used by concrete scorers to talk to runtime (strings) ---
    @staticmethod
    def _dir_name(direction: Direction) -> str:
        return direction.value

    @staticmethod
    def _se_name(se_mode: SeMode) -> str:
        return se_mode.value

    # ---------------------------- misc helpers ----------------------------
    def impl_name(self) -> str:
        """Backend impl string for telemetry (e.g., 'numpy' or 'torch')."""
        name = self.__class__.__name__.replace("RuneScorer", "").strip().lower()
        if not name:
            return "numpy"
        if name in {"scorer", "base"}:
            return "numpy"
        return name

    def dtype_name(self) -> str:
        """Return the configured dtype string."""
        return str(getattr(self, "_dtype", "float32"))

    def device_name(self) -> str:
        """Backend device string for telemetry ('cpu'/'cuda' or 'n/a')."""
        return getattr(self, "_device_str", "n/a")

    def telemetry(self) -> Dict[str, Any]:
        """Return current telemetry dict."""
        return dict(self._telemetry) if hasattr(self, "_telemetry") else {}
