# ============================================================
# rune_decrypter_prime/scoring/base_scorer.py   (Abstract scorer API)
# Minimal, stable contract for all scoring backends.
# Now imports the strict Enums used by concrete scorers.
# ============================================================
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence, Dict, Tuple, Optional
import re

from rune_decrypter_prime.utils.telemetry import stash as _tstash
from rune_decrypter_prime.core.types import (
    Direction, Device,  # existing
    # new enum family used by the scorers
    SeMode, Channel, ObjectiveFamily, Stat, ObjectiveSpec,
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

    # Require and resolve ObjectiveSpec(PCT, LOGP, win=K). Sets self.win and returns K.
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
        if fam_val != "pct" or stat_val != "logp":
            raise ValueError(f"unsupported objective: {obj!r} (expected pct.logp.winK)")

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

# # ============================================================
# # rune_decrypter_prime/scoring/enum_scorer_base.py
# #
# # Functional scorer base with strict Enums, shared window/ECDF glue,
# # and legacy objective routing. Concrete backends (NumPy/Torch) only
# # implement per-model percentile computation and (optionally) legacy
# # scalar objectives. Windows are assumed to be WIN=10, stride=1.
# # ============================================================
# from __future__ import annotations
#
# from abc import ABC, abstractmethod
# from dataclasses import dataclass
# from typing import Iterable, Sequence, Tuple, Dict, List, Optional, Any, Union, TYPE_CHECKING
# import math
# import warnings
#
# # Keep telemetry behaviour identical to existing scorers (no-throw best-effort)
# from rune_decrypter_prime.utils.telemetry import stash as _tstash
#
# # --------------------------------------------------------------------------------------
# # Enum types (imported; defined in core/types.py). We only *reference* them here.
# # NOTE: Add these Enums to core/types.py if not already present, matching these names.
# # --------------------------------------------------------------------------------------
# if TYPE_CHECKING:  # type-checking only; avoids circulars at runtime
#     from rune_decrypter_prime.core.types import (
#         Direction,        # LTR | RTL
#         Device,           # CPU | CUDA (Torch backend only)
#         # New enums agreed for scorers
#         SeMode,           # NOSE | WISE
#         Channel,          # CHAR | WLI
#         ObjectiveFamily,  # PCT | AVG | ENERGY | NEGLOGP
#         Stat,             # LOGP | ZSUM | MADSUM
#         ObjectiveSpec,    # (family, stat?, win?)
#     )
# else:
#     # When editors run static analysis without project wiring, provide minimal shims.
#     class _ShimEnum(str):
#         def __getattr__(self, k):
#             raise AttributeError("Enum shims are for type hints only.")
#     Direction = Device = SeMode = Channel = ObjectiveFamily = Stat = _ShimEnum  # type: ignore
#     ObjectiveSpec = Any  # type: ignore
#
#
# # ============================================================
# # Constants & small helpers
# # ============================================================
# WIN: int = 10           # Project-wide assumption: all pct.* objectives use win=10
# STRIDE: int = 1         # Overlapping windows with unit stride
#
# # Clamp defaults match existing behaviour
# DEFAULT_ECDF_FLOOR: float = 1e-6
# DEFAULT_ECDF_CEILING: float = 1.0
#
#
# @dataclass(frozen=True)
# class ActiveModel:
#     """A single active model component in the convex mix.
#
#     Attributes
#     ----------
#     channel : Channel
#         Which family of n-grams this component uses (CHAR or WLI).
#     n : int
#         N-gram order (e.g., 2..4 for CHAR; 1..4 for WLI depending on data).
#     w : float
#         Non-negative weight. The base normalises the list to L1=1.0.
#     """
#     channel: Channel  # type: ignore[valid-type]
#     n: int
#     w: float
#
#
# # ============================================================
# # Base
# # ============================================================
# class EnumScorerBase(ABC):
#     """Shared scorer glue with Enum-only API and deterministic behaviour.
#
#     This base provides:
#       - Strict, Enum-typed configuration (no stringy inputs at this boundary).
#       - Fixed-window (WIN=10, STRIDE=1) normalised objective routing for PCT/ENERGY.
#       - Legacy routing for AVG/NEGLOGP with a clear deprecation warning.
#       - Input/output type contracts and small, no-throw telemetry.
#
#     Concrete backends implement:
#       1) ``_u_per_window`` — return *percentiles* per overlapping window for a
#          single (channel, n) model component. The base mixes components and
#          computes final mean/std.
#       2) ``_score_legacy_scalar`` — optional; NumPy backend keeps AVG/NEGLOGP,
#          Torch backend can raise NotImplementedError for legacy objectives.
#
#     Input contracts (assumed met; minimal asserts kept for early failure):
#       - ``plaintext`` / items in ``plaintexts`` are iterables of ints (0..28), length L >= 1.
#       - If provided, ``wli_windows`` is an iterable of L pairs (int, int) or an Lx2 array.
#       - For ``batch_score``, either pass a single Lx2 WLI shared by all items, or a list
#         of length N with each item an Lx2 WLI matching its plaintext.
#
#     Output contracts:
#       - ``score`` returns a float in [0,1] for PCT/ENERGY, or an unconstrained float
#         for legacy AVG/NEGLOGP.
#       - ``batch_score`` returns a list[float] with one score per input.
#
#     Telemetry:
#       - We record ``score_mean``/``score_std`` for the normalised path and the number of
#         windows used (n_windows = L - WIN + 1). For batch, we log arrays for means/stds.
#       - When legacy objectives are used, we mark ``legacy_objective=True``.
#
#     Performance:
#       - WIN=10 is baked in here to allow backends to pre-optimise packing, ECDF lookup,
#         table selection, or Torch striding for the fixed K.
#     """
#
#     # ------------------------------ init ------------------------------
#     def __init__(
#         self,
#         *,
#         direction: Direction,                  # type: ignore[valid-type]
#         objective: ObjectiveSpec,              # type: ignore[valid-type]
#         se_mode: SeMode,                       # type: ignore[valid-type]
#         include_char: bool,
#         use_word_breaks: bool,
#         # model selection (choose *either* dict maps or legacy single-order+pair weights)
#         char_weights: Optional[Dict[int, float]] = None,
#         wli_weights: Optional[Dict[int, float]] = None,
#         n_char: Optional[int] = None,
#         n_wli: Optional[int] = None,
#         weights_pair: Optional[Tuple[float, float]] = None,  # (w_char, w_wli)
#         # ECDF clamps
#         ecdf_floor: float = DEFAULT_ECDF_FLOOR,
#         ecdf_ceiling: float = DEFAULT_ECDF_CEILING,
#         # dtype label for telemetry only
#         dtype_str: str = "float32",
#     ) -> None:
#         # Store simple fields
#         self.direction = direction
#         self.objective = objective
#         self.se_mode = se_mode
#         self.include_char = bool(include_char)
#         self.use_word_breaks = bool(use_word_breaks)
#         self._dtype_str = str(dtype_str)
#
#         # ECDF clamp bounds (kept as floats)
#         self._ecdf_floor = float(ecdf_floor)
#         self._ecdf_ceiling = float(ecdf_ceiling)
#         if not (0.0 <= self._ecdf_floor <= 1.0 and 0.0 <= self._ecdf_ceiling <= 1.0):
#             raise ValueError("ecdf_floor/ceiling must be in [0,1].")
#         if self._ecdf_floor > self._ecdf_ceiling:
#             raise ValueError("ecdf_floor cannot exceed ecdf_ceiling.")
#
#         # Validate / freeze model selection
#         self._models: List[ActiveModel] = self._select_models(
#             include_char=self.include_char,
#             use_wli=self.use_word_breaks,
#             char_weights=char_weights,
#             wli_weights=wli_weights,
#             n_char=n_char,
#             n_wli=n_wli,
#             weights_pair=weights_pair,
#         )
#
#         # Derived / fixed window parameters
#         self._win = int(WIN)
#         self._stride = int(STRIDE)
#
#         # scratch telemetry
#         self._telemetry: Dict[str, Any] = {}
#
#     # ---------------------------- public API ----------------------------
#     def score(
#         self,
#         plaintext: Iterable[int],
#         wli_windows: Optional[Iterable[Tuple[int, int]]] = None,
#     ) -> float:
#         """Score a single plaintext.
#
#         Parameters
#         ----------
#         plaintext : Iterable[int]
#             Tokenised plaintext as rune IDs in [0, 28]. Length L >= 1.
#         wli_windows : Optional[Iterable[Tuple[int, int]]]
#             Optional Lx2 word-link indicators aligned to ``plaintext``.
#
#         Returns
#         -------
#         float
#             Normalised score in [0,1] for PCT/ENERGY objectives; unconstrained for legacy.
#         """
#         fam = getattr(self.objective, "family", None)
#         stat = getattr(self.objective, "stat", None)
#
#         if fam is None:
#             raise ValueError("ObjectiveSpec.family is required.")
#
#         if str(fam).endswith("NEGLOGP") or str(fam).lower().endswith("neglogp"):
#             warnings.warn("Using legacy NEGLOGP objective; consider migrating to PCT.*.",
#                           DeprecationWarning, stacklevel=2)
#             out = float(self._score_legacy_scalar(plaintext, wli_windows))
#             self._stash(dtype=self._dtype_str, legacy_objective=True, score_mean=out, score_std=0.0, n_windows=1)
#             return out
#
#         if str(fam).endswith("AVG") or str(fam).lower().endswith("avg"):
#             warnings.warn("Using legacy AVG.* objective; consider migrating to PCT.*.",
#                           DeprecationWarning, stacklevel=2)
#             out = float(self._score_legacy_scalar(plaintext, wli_windows))
#             self._stash(dtype=self._dtype_str, legacy_objective=True, score_mean=out, score_std=0.0, n_windows=1)
#             return out
#
#         # ENERGY alias → PCT (keeps behaviour compatible with pre-refactor)
#         pct_like = (
#             str(fam).endswith("PCT") or str(fam).lower().endswith("pct") or
#             str(fam).endswith("ENERGY") or str(fam).lower().endswith("energy")
#         )
#         if not pct_like:
#             raise ValueError(f"Unsupported objective family: {fam!r}")
#         if stat is None:
#             raise ValueError("ObjectiveSpec.stat is required for PCT/ENERGY objectives.")
#
#         # Overlapping windows count (L - WIN + 1). For L < WIN, return floor immediately.
#         L = _len_plain(plaintext)
#         nwin = max(0, L - self._win + 1)
#         if nwin == 0:
#             self._stash(dtype=self._dtype_str, scorer={"impl": self.impl_name(), "device": self.device_name()},
#                         score_mean=float(self._ecdf_floor), score_std=0.0, n_windows=int(nwin))
#             return float(self._ecdf_floor)
#
#         # Mix per-model percentiles (already clamped by subclass if applicable)
#         perwin = [0.0] * nwin
#         for m in self._models:
#             u = self._u_per_window(
#                 channel=m.channel, n=m.n,
#                 plaintext=plaintext, wli_windows=wli_windows,
#                 win=self._win, stride=self._stride,
#                 se_mode=self.se_mode, direction=self.direction,
#             )
#             if len(u) != nwin:
#                 raise ValueError(f"_u_per_window returned {len(u)} values, expected {nwin}.")
#             w = float(m.w)
#             for i in range(nwin):
#                 perwin[i] += w * float(u[i])
#
#         # Final mean/std
#         # (Keep deterministic float32 if backends use float32; result as Python float)
#         mean = float(sum(perwin) / nwin)
#         # population std for parity with existing NumPy path
#         var = float(sum((x - mean) * (x - mean) for x in perwin) / nwin)
#         std = float(math.sqrt(max(var, 0.0)))
#
#         self._stash(
#             dtype=self._dtype_str,
#             scorer={"impl": self.impl_name(), "device": self.device_name()},
#             score_mean=mean, score_std=std, n_windows=int(nwin),
#         )
#         return mean
#
#     def batch_score(
#         self,
#         plaintexts: Sequence[Iterable[int]],
#         wlis: Optional[Union[Iterable[Tuple[int, int]], Sequence[Iterable[Tuple[int, int]]]]] = None,
#     ) -> List[float]:
#         """Score a batch of plaintexts.
#
#         Batch behaviour mirrors the single-item path, aggregating per-item telemetry
#         (means/stds). All plaintexts must share the same length L; this matches the
#         current solver expectations and enables fixed-window buffering in backends.
#         """
#         if not plaintexts:
#             return []
#         L0 = _len_plain(plaintexts[0])
#         for i, p in enumerate(plaintexts):
#             if _len_plain(p) != L0:
#                 raise ValueError(f"all plaintexts must have same length; item {i} has {_len_plain(p)} vs {L0}")
#
#         shared_wli = None
#         per_item_wli: Optional[Sequence[Iterable[Tuple[int, int]]]] = None
#         if wlis is not None:
#             # If it quacks like a single Lx2 array/list, treat it as shared
#             if _len_plain(wlis) == L0:  # type: ignore[arg-type]
#                 shared_wli = wlis  # type: ignore[assignment]
#             else:
#                 per_item_wli = wlis  # type: ignore[assignment]
#                 if len(per_item_wli) != len(plaintexts):
#                     raise ValueError("wlis length must match plaintexts length when providing per-item WLI.")
#
#         out: List[float] = []
#         means: List[float] = []
#         stds: List[float] = []
#         for i, pt in enumerate(plaintexts):
#             wli_i = shared_wli if per_item_wli is None else per_item_wli[i]
#             m = float(self.score(pt, wli_i))
#             out.append(m)
#             # pull last stored mean/std (score() already stashed them)
#             tele = self.telemetry()
#             means.append(float(tele.get("score_mean", m)))
#             stds.append(float(tele.get("score_std", 0.0)))
#
#         # Record batch arrays
#         self._stash(
#             dtype=self._dtype_str,
#             scorer={"impl": self.impl_name(), "device": self.device_name()},
#             score_mean_batch=means, score_std_batch=stds,
#             n_windows=max(0, L0 - self._win + 1),
#         )
#         return out
#
#     # ---------------------------- abstract hooks ----------------------------
#     @abstractmethod
#     def _u_per_window(
#         self,
#         *,
#         channel: Channel,             # type: ignore[valid-type]
#         n: int,
#         plaintext: Iterable[int],
#         wli_windows: Optional[Iterable[Tuple[int, int]]],
#         win: int,
#         stride: int,
#         se_mode: SeMode,              # type: ignore[valid-type]
#         direction: Direction,         # type: ignore[valid-type]
#     ) -> Sequence[float]:
#         """Percentiles per overlapping window for a single model component.
#
#         Return a 1-D sequence of length ``L - win + 1`` with values in [0,1].
#         Subclasses may clamp to ``[self._ecdf_floor, self._ecdf_ceiling]``.
#         """
#         raise NotImplementedError
#
#     def _score_legacy_scalar(
#         self,
#         plaintext: Iterable[int],
#         wli_windows: Optional[Iterable[Tuple[int, int]]],
#     ) -> float:
#         """Legacy scalar objectives (AVG.*, NEGLOGP).
#
#         NumPy backend implements this by calling the LM runtime's full-length
#         windows. Torch backend may raise NotImplementedError (mirroring current
#         behaviour). The base routes here only when ObjectiveFamily is AVG/NEGLOGP.
#         """
#         raise NotImplementedError
#
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
#
#     # ---------------------------- private helpers ----------------------------
#     def _select_models(
#         self,
#         *,
#         include_char: bool,
#         use_wli: bool,
#         char_weights: Optional[Dict[int, float]],
#         wli_weights: Optional[Dict[int, float]],
#         n_char: Optional[int],
#         n_wli: Optional[int],
#         weights_pair: Optional[Tuple[float, float]],
#     ) -> List[ActiveModel]:
#         """Build and L1-normalise the active model list.
#
#         Two modes are supported (mutually exclusive):
#           (A) dict-based weights per order, e.g. ``char_weights={2:0.6,3:0.4}``; or
#           (B) legacy single-order + pair weights (``n_char``, ``n_wli``, ``weights_pair``).
#
#         Returns a stable list ordered by channel (CHAR, then WLI) and increasing n.
#         """
#         have_dicts = (char_weights is not None) or (wli_weights is not None)
#         have_legacy = (n_char is not None) or (n_wli is not None) or (weights_pair is not None)
#         if have_dicts and have_legacy:
#             raise ValueError("Provide either per-order dict weights OR legacy n_* + weights_pair, not both.")
#
#         models: List[ActiveModel] = []
#
#         if have_dicts:
#             if include_char and char_weights:
#                 for n, w in sorted(char_weights.items()):
#                     if w > 0.0:
#                         models.append(ActiveModel(channel=cast_channel("CHAR"), n=int(n), w=float(w)))
#             if use_wli and wli_weights:
#                 for n, w in sorted(wli_weights.items()):
#                     if w > 0.0:
#                         models.append(ActiveModel(channel=cast_channel("WLI"), n=int(n), w=float(w)))
#         else:
#             # Legacy single-order path
#             w_char, w_wli = (weights_pair or (0.5, 0.5))
#             if not include_char:
#                 w_char = 0.0
#             if not use_wli:
#                 w_wli = 0.0
#             if include_char and n_char is None:
#                 raise ValueError("n_char must be set when include_char=True and using legacy path.")
#             if use_wli and n_wli is None:
#                 raise ValueError("n_wli must be set when use_word_breaks=True and using legacy path.")
#             if include_char:
#                 models.append(ActiveModel(channel=cast_channel("CHAR"), n=int(n_char or 2), w=float(w_char)))
#             if use_wli:
#                 models.append(ActiveModel(channel=cast_channel("WLI"), n=int(n_wli or 2), w=float(w_wli)))
#
#         # L1 normalise (avoid div-by-zero by defaulting to equal weights if empty)
#         total = sum(max(0.0, m.w) for m in models)
#         if total <= 0.0:
#             raise ValueError("No active models; check include_char/use_word_breaks and provided weights.")
#         inv = 1.0 / total
#         models = [ActiveModel(m.channel, m.n, m.w * inv) for m in models]
#         return models
#
#     def _stash(self, dtype: Optional[str] = None, **stats: Any) -> None:
#         """No-throw telemetry merge."""
#         try:
#             tele = self._telemetry
#             if dtype is not None:
#                 tele["dtype"] = str(dtype)
#             if stats:
#                 _tstash(tele, **stats)
#         except Exception:
#             pass
#
#
# # ============================= minor utilities =============================
# def _len_plain(x: Any) -> int:
#     try:
#         return len(x)
#     except Exception:
#         # iterable without __len__ (rare in our pipeline, but keep friendly)
#         c = 0
#         for _ in x:  # type: ignore[assignment]
#             c += 1
#         return c
#
#
# def cast_channel(name: str) -> Channel:  # type: ignore[valid-type]
#     """Helper to construct a Channel enum from a constant string.
#
#     Backends and tests can replace this with the real Channel Enum import.
#     We keep it here to avoid importing core/types.py at import time.
#     """
#     # During TYPE_CHECKING this function is ignored by type-checkers.
#     return name  # type: ignore[return-value]
#
#
# # # ============================================================
# # # rune_decrypter_prime/scoring/base_scorer.py   (Abstract scorer API)
# # # Minimal, stable contract for all scoring backends.
# # # ============================================================
# # from __future__ import annotations
# # from abc import ABC, abstractmethod
# # from typing import Any, Iterable, Sequence, Dict, Tuple, Optional
# # import re
# # from rune_decrypter_prime.utils.telemetry import stash as _tstash
# #
# # # --- Shared constants used by concrete scorers ---
# # STAT_KEYS: Tuple[str, ...] = ("logp", "zsum", "madsum")
# #
# # # Accepts: "family.stat" or "family.stat.win<k>"
# # _OBJ_RE = re.compile(r'^(?P<family>[A-Za-z_]+)\.(?P<stat>[A-Za-z_]+)(?:\.win(?P<win>\d+))?$')
# #
# # def parse_objective(obj: str) -> Tuple[str, Optional[str], Optional[int]]:
# #     """
# #     Return (family, stat, win_hint).
# #
# #     Examples:
# #       "pct.logp"         -> ("pct", "logp", None)
# #       "pct.logp.win10"   -> ("pct", "logp", 10)
# #       "energy.logp"      -> ("energy", "logp", None)
# #     """
# #     s = (obj or "").strip().lower()
# #     m = _OBJ_RE.match(s)
# #     if not m:
# #         parts = s.split(".", 1)
# #         fam = parts[0] if parts else s
# #         stat = parts[1] if len(parts) > 1 else None
# #         return fam, stat, None
# #     fam = m.group("family")
# #     stat = m.group("stat")
# #     win_str = m.group("win")
# #     return fam, stat, (int(win_str) if win_str is not None else None)
# #
# # def normalize_objective(obj: str, default_win: int) -> str:
# #     """
# #     Canonicalise objective spellings to: 'pct.logp.win{default_win}' for pct/logp-ish inputs.
# #
# #     Rules:
# #       - '' or None           -> pct.logp.win{default_win}
# #       - 'pct.logp'           -> pct.logp.win{default_win}
# #       - 'pct.logp.winK'      -> as-is
# #       - 'energy.logp' alias  -> pct.logp.win{default_win}
# #       - otherwise            -> lowercased original (non-standard; handled by scorers)
# #     """
# #     if not obj:
# #         return f"pct.logp.win{int(default_win)}"
# #     o = str(obj).strip().lower()
# #     if o in {"energy.logp", "energy", "logp.energy"}:
# #         return f"pct.logp.win{int(default_win)}"
# #     if o.startswith("pct.logp.win"):
# #         return o
# #     if o == "pct.logp":
# #         return f"pct.logp.win{int(default_win)}"
# #     fam, stat, win_hint = parse_objective(o)
# #     if fam == "pct" and stat == "logp":
# #         return f"pct.logp.win{int(win_hint if win_hint is not None else default_win)}"
# #     return o  # non-standard: leave to concrete scorer
# #
# # class BaseScorer(ABC):
# #     """
# #     Minimal scoring contract used by the solver. All concrete scorers must:
# #       - implement score() for a single plaintext
# #       - implement batch_score() for a batch (same L across items)
# #       - expose telemetry() with impl/device/dtype for logging & tests
# #     """
# #
# #     @abstractmethod
# #     def score(self, plaintext: Iterable[int], wli_windows: Any | None = None) -> float:  # pragma: no cover
# #         raise NotImplementedError
# #
# #     @abstractmethod
# #     def batch_score(self, pts: Sequence[Iterable[int]], wlis: Any | None = None):  # -> np.ndarray[float32]
# #         raise NotImplementedError
# #
# #     def __call__(self, plaintexts: Any, wli_windows: Any | None = None):
# #         return self.score(plaintexts, wli_windows)
# #
# #     def last_stats(self):
# #         """Return per-call stats recorded by the last score()/batch_score() call, if any."""
# #         return getattr(self, "_last_stats", {}) or {}
# #
# #     def telemetry(self):
# #         """Structured info for run logger / dashboards. Implementation may extend."""
# #         return getattr(self, "_telemetry", {}) or {}
# #
# #     # --- tiny shared helper for telemetry (no-throw, in-place) ---
# #     def _stash_stats(self, dtype: str | None = None, **stats):
# #         """
# #         Best-effort: merge stats into self._telemetry without raising.
# #         Keeps existing contract: in-place mutation, accepts None.
# #         """
# #         try:
# #             tele = self.__dict__.setdefault("_telemetry", {})
# #             if dtype is not None:
# #                 tele["dtype"] = str(dtype)
# #             if stats:
# #                 _tstash(tele, **stats)
# #         except Exception:
# #             # Telemetry must never interfere with core logic.
# #             pass
