from __future__ import annotations

from typing import Any, Mapping

import numpy as np


def build_shadow_stop_v1_state(
    *,
    phase_name: str,
    plateau_work_units: int,
    high_score_floor: float,
    high_score_stable_work_units: int,
    score_improve_eps: float,
    initial_score: float = float("nan"),
    initial_match: float = float("nan"),
) -> dict[str, Any]:
    best_score = float(initial_score) if np.isfinite(float(initial_score)) else float("nan")
    best_match = float(initial_match) if np.isfinite(float(initial_match)) else float("nan")
    return dict(
        phase_name=str(phase_name),
        plateau_work_units_cfg=int(max(1, int(plateau_work_units))),
        high_score_floor_cfg=float(high_score_floor),
        high_score_stable_work_units_cfg=int(
            max(1, int(high_score_stable_work_units))
        ),
        score_improve_eps_cfg=float(max(0.0, float(score_improve_eps))),
        best_score=float(best_score),
        best_match=float(best_match),
        last_progress_work_unit=0,
        last_progress_evals=0,
        plateau_work_units_since_progress=0,
        high_score_streak_work_units=(
            1
            if np.isfinite(float(best_score))
            and float(best_score) >= float(high_score_floor)
            else 0
        ),
        progress_counter_seen=0,
        novelty_counter_seen=0,
        plateau_would_stop=0,
        plateau_first_work_unit=None,
        plateau_first_evals=None,
        plateau_first_best_score=None,
        plateau_first_best_match=None,
        high_score_would_stop=0,
        high_score_first_work_unit=None,
        high_score_first_evals=None,
        high_score_first_score=None,
        high_score_first_match=None,
    )


def update_shadow_stop_v1_state(
    state: Mapping[str, Any],
    *,
    work_unit: int,
    evals_done: int,
    best_score: float,
    best_match: float,
    progress_counter: int,
    novelty_counter: int,
) -> dict[str, Any]:
    out = dict(state)
    work_unit_i = int(work_unit)
    evals_i = int(evals_done)
    score_f = float(best_score) if np.isfinite(float(best_score)) else float("nan")
    match_f = float(best_match) if np.isfinite(float(best_match)) else float("nan")
    progress_i = int(progress_counter)
    novelty_i = int(novelty_counter)

    prev_best_score = float(out.get("best_score", float("nan")))
    improved_score = bool(
        np.isfinite(score_f)
        and (
            (not np.isfinite(prev_best_score))
            or float(score_f)
            > float(prev_best_score) + float(out.get("score_improve_eps_cfg", 0.0))
        )
    )
    improved_progress = bool(
        int(progress_i) > int(out.get("progress_counter_seen", 0) or 0)
    )
    improved_novelty = bool(
        int(novelty_i) > int(out.get("novelty_counter_seen", 0) or 0)
    )
    if improved_score:
        out["best_score"] = float(score_f)
        out["best_match"] = float(match_f)
    if improved_score or improved_progress or improved_novelty:
        out["last_progress_work_unit"] = int(work_unit_i)
        out["last_progress_evals"] = int(evals_i)
        out["plateau_work_units_since_progress"] = 0
        out["progress_counter_seen"] = int(max(int(out.get("progress_counter_seen", 0) or 0), progress_i))
        out["novelty_counter_seen"] = int(max(int(out.get("novelty_counter_seen", 0) or 0), novelty_i))
    else:
        out["plateau_work_units_since_progress"] = int(
            int(out.get("plateau_work_units_since_progress", 0) or 0) + 1
        )

    if (
        int(out.get("plateau_would_stop", 0) or 0) == 0
        and int(out.get("plateau_work_units_since_progress", 0) or 0)
        >= int(out.get("plateau_work_units_cfg", 1) or 1)
    ):
        out["plateau_would_stop"] = 1
        out["plateau_first_work_unit"] = int(work_unit_i)
        out["plateau_first_evals"] = int(evals_i)
        out["plateau_first_best_score"] = (
            float(out.get("best_score", float("nan")))
            if np.isfinite(float(out.get("best_score", float("nan"))))
            else None
        )
        out["plateau_first_best_match"] = (
            float(out.get("best_match", float("nan")))
            if np.isfinite(float(out.get("best_match", float("nan"))))
            else None
        )

    if np.isfinite(score_f) and float(score_f) >= float(
        out.get("high_score_floor_cfg", float("inf"))
    ):
        out["high_score_streak_work_units"] = int(
            int(out.get("high_score_streak_work_units", 0) or 0) + 1
        )
    else:
        out["high_score_streak_work_units"] = 0

    if (
        int(out.get("high_score_would_stop", 0) or 0) == 0
        and int(out.get("high_score_streak_work_units", 0) or 0)
        >= int(out.get("high_score_stable_work_units_cfg", 1) or 1)
    ):
        out["high_score_would_stop"] = 1
        out["high_score_first_work_unit"] = int(work_unit_i)
        out["high_score_first_evals"] = int(evals_i)
        out["high_score_first_score"] = float(score_f)
        out["high_score_first_match"] = float(match_f) if np.isfinite(match_f) else None

    return out
