from __future__ import annotations

from typing import Any, Mapping

from rdp.core.types import (
    ObjectiveFamily,
    ObjectiveSpec,
    Stat,
    ensure_objective_family,
    ensure_stat,
)
from rune_decrypter_prime.scoring.base_scorer import parse_objective


def normalize_objective_input(value: Any, *, default_win: int) -> ObjectiveSpec:
    """
    Normalize objective input accepted by scorer runtime config.

    Accepted forms:
    - ObjectiveSpec
    - mapping with {"family","stat","win"}
    - objective string like "pct.logp.win10"
    - None (defaults to pct.logp.win<default_win>)
    """
    from rdp.core.config.scoring import ScoringObjective
    from rdp.core.types import ScoringObjectiveKind, ScoreStatistic

    if isinstance(value, ScoringObjective):
        if value.kind is ScoringObjectiveKind.PERCENTILE:
            fam = ObjectiveFamily.PCT
            stat = {
                ScoreStatistic.LOG_PROBABILITY: Stat.LOGP,
                ScoreStatistic.Z_SCORE_SUM: Stat.ZSUM,
                ScoreStatistic.MEDIAN_ABSOLUTE_DEVIATION_SUM: Stat.MADSUM,
            }[value.statistic]
            win = value.window_size
        elif value.kind is ScoringObjectiveKind.AVERAGE:
            fam, stat, win = ObjectiveFamily.AVG, Stat.LOGP, default_win
        else:
            fam, stat, win = ObjectiveFamily.NEGLOGP, None, None
    elif isinstance(value, ObjectiveSpec):
        fam = ensure_objective_family(value.family)
        stat = ensure_stat(value.stat) if value.stat is not None else None
        win = int(value.win) if value.win is not None else None
    elif isinstance(value, Mapping):
        fam = ensure_objective_family(value.get("family", ObjectiveFamily.PCT))
        stat_raw = value.get("stat")
        stat = ensure_stat(stat_raw) if stat_raw is not None else None
        win_raw = value.get("win")
        win = int(win_raw) if win_raw is not None else None
    elif isinstance(value, str):
        fam_raw, stat_raw, win_raw = parse_objective(value)
        fam = ensure_objective_family(fam_raw)
        stat = ensure_stat(stat_raw) if stat_raw is not None else None
        win = int(win_raw) if win_raw is not None else None
    elif value is None:
        fam = ObjectiveFamily.PCT
        stat = Stat.LOGP
        win = int(default_win)
    else:
        raise TypeError("objective must be ObjectiveSpec | dict | str | None")

    if fam in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY, ObjectiveFamily.AVG):
        if stat is None:
            stat = Stat.LOGP
        if win is None:
            win = int(default_win)
    return ObjectiveSpec(family=fam, stat=stat, win=win)
