# ============================================================
# rune_decrypter_prime/scoring/base_scorer.py   (Abstract scorer API)
# Minimal, stable contract for all scoring backends.
# ============================================================
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence, Dict, Tuple, Optional
import re
from rune_decrypter_prime.utils.telemetry import stash as _tstash

# --- Shared constants used by concrete scorers ---
STAT_KEYS: Tuple[str, ...] = ("logp", "zsum", "madsum")

# Accepts: "family.stat" or "family.stat.win<k>"
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
        return f"pct.logp.win{int(default_win)}"
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
    """

    @abstractmethod
    def score(self, plaintext: Iterable[int], wli_windows: Any | None = None) -> float:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def batch_score(self, pts: Sequence[Iterable[int]], wlis: Any | None = None):  # -> np.ndarray[float32]
        raise NotImplementedError

    def __call__(self, plaintexts: Any, wli_windows: Any | None = None):
        return self.score(plaintexts, wli_windows)

    def last_stats(self):
        """Return per-call stats recorded by the last score()/batch_score() call, if any."""
        return getattr(self, "_last_stats", {}) or {}

    def telemetry(self):
        """Structured info for run logger / dashboards. Implementation may extend."""
        return getattr(self, "_telemetry", {}) or {}

    # --- tiny shared helper for telemetry (no-throw, in-place) ---
    def _stash_stats(self, dtype: str | None = None, **stats):
        """
        Best-effort: merge stats into self._telemetry without raising.
        Keeps existing contract: in-place mutation, accepts None.
        """
        try:
            tele = self.__dict__.setdefault("_telemetry", {})
            if dtype is not None:
                tele["dtype"] = str(dtype)
            if stats:
                _tstash(tele, **stats)
        except Exception:
            # Telemetry must never interfere with core logic.
            pass
