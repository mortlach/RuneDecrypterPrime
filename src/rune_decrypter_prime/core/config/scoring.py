# ============================================================
# rune_decrypter_prime/core/config.py
# Unified dataclasses for cipher/scorer/solver/run configs.
# ============================================================

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Literal
import math

from rune_decrypter_prime.core.types import (
    ScorerImpl,
    Direction,
    SeMode,
    ObjectiveFamily,
    Stat,
    ObjectiveSpec,
    ensure_direction,
    ensure_scorer_impl,
    ensure_se_mode,
    ensure_objective_family,
    ensure_stat,
)


def _objective_from_string(spec: str) -> ObjectiveSpec:
    """
    Accept legacy strings like "pct.logp.win10" and convert them to ObjectiveSpec.
    """
    if spec is None:
        raise ValueError("objective string cannot be None")
    text = str(spec).strip().lower()
    if not text:
        raise ValueError("objective string cannot be empty")
    parts = [token for token in text.replace("/", ".").split(".") if token]
    family = ensure_objective_family(parts[0])
    stat = None
    win = None
    for token in parts[1:]:
        if token.startswith("win"):
            try:
                win = int(token[3:])
            except ValueError as exc:
                raise ValueError(f"Invalid window token '{token}' in objective string '{spec}'") from exc
            continue
        stat = ensure_stat(token)
    return ObjectiveSpec(family=family, stat=stat, win=win)

# ---------------- ScoringConfig ----------------------------------------------
@dataclass
class ScoringConfig:
    """Configuration for the Language Model scorer (LMPrime)."""
    model_root: Path = None
    smoothing: str = "auto_gt"
    alpha: float = 0.5
    oov_policy: str = "floor_min_seen"
    include_char: bool = True
    use_word_breaks: bool = True
    n_char: int = 2
    n_wli: int  = 2
    win: int = 10
    se_mode: SeMode = SeMode.NOSE
    weights: Tuple[float, float] = (0.25, 0.75)   # (w_char, w_wli)
    maximize: bool = True
    encoding_dir: Direction = Direction.LTR
    char_weights: Dict[int, float] = field(default_factory=lambda: {2: 0.5})
    wli_weights: Dict[int, float] = field(default_factory=lambda: {2: 0.5})
    impl: Optional[ScorerImpl] = ScorerImpl.AUTO
    dtype: Literal["float32", "float64"] = "float32"
    objective: ObjectiveSpec = ObjectiveSpec(family=ObjectiveFamily.PCT,stat=Stat.LOGP,win=10)

    def __post_init__(self) -> None:
        if self.encoding_dir is not None:
            self.encoding_dir = ensure_direction(self.encoding_dir)
        if self.impl is not None:
            self.impl = ensure_scorer_impl(self.impl)
        if self.se_mode is not None:
            self.se_mode = ensure_se_mode(self.se_mode)

        obj = getattr(self, "objective", None)
        if isinstance(obj, dict):
            fam = ensure_objective_family(obj.get("family", ObjectiveFamily.PCT))
            stat_val = obj.get("stat")
            stat = ensure_stat(stat_val) if stat_val is not None else None
            win = obj.get("win")
            self.objective = ObjectiveSpec(family=fam, stat=stat, win=win)
        elif isinstance(obj, str):
            self.objective = _objective_from_string(obj)
        elif isinstance(obj, ObjectiveSpec):
            fam = ensure_objective_family(obj.family)
            stat = ensure_stat(obj.stat) if obj.stat is not None else None
            self.objective = ObjectiveSpec(family=fam, stat=stat, win=obj.win)

        self.char_weights = self._normalise_channel_weights(self.char_weights, 'char_weights')
        self.wli_weights = self._normalise_channel_weights(self.wli_weights, 'wli_weights')

    def asdict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["model_root"] = self.model_root
        out["smoothing"] = self.smoothing
        out["alpha"] = self.alpha
        out["oov_policy"] = self.oov_policy
        out["include_char"] = self.include_char
        out["use_word_breaks"] = self.use_word_breaks
        out["n_char"] = self.n_char
        out["n_wli"] = self.n_wli
        out["win"] = self.win
        out["se_mode"] = self.se_mode
        out["objective"] = self.objective
        #     {
        #     "family": self.objective.family.value if isinstance(self.objective.family, ObjectiveFamily) else self.objective.family,
        #     "stat": (self.objective.stat.value if isinstance(self.objective.stat, Stat) else self.objective.stat),
        #     "win": self.objective.win,
        # }
        # out["weights"] = self.weights
        out["maximize"] = self.maximize
        out["encoding_dir"] = self.encoding_dir
        out["char_weights"] = self.char_weights
        out["wli_weights"] = self.wli_weights
        out["impl"] = self.impl.value if isinstance(self.impl, ScorerImpl) else self.impl
        out["dtype"] = self.dtype
        return out



    @staticmethod
    def _normalise_channel_weights(weights: Any, field_name: str) -> Dict[int, float]:
        if weights in (None, {}):
            return {}
        if isinstance(weights, dict):
            iterable = weights.items()
        elif isinstance(weights, (list, tuple)):
            iterable = weights
        else:
            raise TypeError(f"{field_name} must be a dict or list of (n, weight) pairs as documented")

        normalised: Dict[int, float] = {}
        for item in iterable:
            if isinstance(item, dict):
                if len(item) != 1:
                    raise ValueError(f"{field_name} dict entries must contain a single (n, weight) mapping")
                ((key, value),) = item.items()
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                key, value = item
            else:
                raise TypeError(f"{field_name} entries must be (n, weight) pairs")

            try:
                n_val = int(key)
            except Exception as exc:
                raise TypeError(f"{field_name} keys must be integers (n-gram length)") from exc
            if n_val <= 0:
                raise ValueError(f"{field_name} keys must be positive integers per scoring docs")

            try:
                weight_val = float(value)
            except Exception as exc:
                raise TypeError(f"{field_name} values must be numeric weights") from exc
            if not math.isfinite(weight_val):
                raise ValueError(f"{field_name} weights must be finite numbers")

            normalised[n_val] = weight_val

        return normalised
