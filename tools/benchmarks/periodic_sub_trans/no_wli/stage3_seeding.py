from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Sequence

import numpy as np


def prepare_stage3_refine_inputs(
    *,
    tier_period: int,
    tier_columns: int,
    key_len: int,
    key_seed: int,
    best2_key: Sequence[int],
    best2_match: float,
    stage2_promoted: Sequence[Dict[str, Any]],
    stage2_entry_score: float,
    stage2_entry_score_judge: float,
    scorer_stage2: Dict[str, Any],
    scorer_full: Dict[str, Any],
    stage3_dynamic_bands: Sequence[Mapping[str, Any]],
    oracle_s3: float,
    oracle_decision_paths_enabled: bool,
    stage2_entry_band_by_stage3_judge: bool,
    stage3_c1_focus_enabled_cfg: bool,
    stage3_c1_init_keys: int,
    stage3_initial_keys: int,
    stage3_initial_keys_by_columns: Mapping[int, int],
    stage3_period_init_mult_by_period: Mapping[int, float],
    stage3_period_step_mult_by_period: Mapping[int, float],
    stage3_period_restart_bonus_by_period: Mapping[int, int],
    stage3_init_keys_cap: int,
    stage3_phasea_cfg: Mapping[str, Any],
    stage3_phaseb_cfg: Mapping[str, Any],
    stage3_phaseb_top_n: int,
    stage3_phaseb_gate_delta_floor: float,
    stage3_phaseb_gate_end_gain_floor: float,
    stage3_c1_phasea_steps: int,
    stage3_c1_phaseb_steps: int,
    stage3_c1_phaseb_top_n: int,
    stage3_c1_phaseb_gate_delta_floor: float,
    stage3_c1_phaseb_gate_end_gain_floor: float,
    solver_stage3_cfg: Mapping[str, Any],
    build_stage3_promoted_keys_fn: Callable[..., List[List[int]]],
    mutate_full_key_fn: Callable[..., List[List[int]]],
    objective_space_key_fn: Callable[[Dict[str, Any]], str],
    resolve_stage3_gap_and_band_fn: Callable[..., tuple[float, Dict[str, Any], bool]],
) -> Dict[str, Any]:
    c1_focus_enabled = bool(stage3_c1_focus_enabled_cfg and int(tier_columns) <= 1)
    init3_n_base = int(stage3_initial_keys_by_columns.get(int(tier_columns), int(stage3_initial_keys)))
    init3_n = int(max(init3_n_base, int(stage3_c1_init_keys))) if c1_focus_enabled else int(init3_n_base)
    stage3_period_init_mult = float(
        max(0.10, float(stage3_period_init_mult_by_period.get(int(tier_period), 1.0)))
    )
    stage3_period_step_mult = float(
        max(0.10, float(stage3_period_step_mult_by_period.get(int(tier_period), 1.0)))
    )
    stage3_period_restart_bonus = int(
        max(0, int(stage3_period_restart_bonus_by_period.get(int(tier_period), 0)))
    )
    init3_n = int(max(1, int(np.ceil(float(init3_n) * float(stage3_period_init_mult))))
    )
    if int(stage3_init_keys_cap) > 0:
        init3_n = int(min(int(init3_n), int(stage3_init_keys_cap)))

    promoted_keys = build_stage3_promoted_keys_fn(
        promoted_entries=stage2_promoted,
        best_key=best2_key,
        key_len=int(key_len),
    )
    if not promoted_keys:
        promoted_keys = [list(map(int, best2_key))]

    per_seed = max(1, int(np.ceil(float(init3_n) / float(len(promoted_keys)))))
    init3_all: List[List[int]] = []
    for j, seed_key in enumerate(promoted_keys):
        init3_all.append(list(map(int, seed_key)))
        init3_all.extend(
            mutate_full_key_fn(
                seed_key,
                period=int(tier_period),
                columns=int(tier_columns),
                seed=7000 + int(key_seed) + 97 * int(j),
                n=per_seed,
            )
        )
    init3: List[List[int]] = []
    seen_init: set[tuple[int, ...]] = set()
    for k in init3_all:
        kt = tuple(int(x) for x in k)
        if kt in seen_init:
            continue
        seen_init.add(kt)
        init3.append(list(map(int, k)))
        if len(init3) >= int(init3_n):
            break

    stage2_stage3_space_match = (
        objective_space_key_fn(dict(scorer_stage2))
        == objective_space_key_fn(dict(scorer_full))
    )
    stage2_gate_source = "mid"
    if bool(stage2_entry_band_by_stage3_judge) and np.isfinite(float(stage2_entry_score_judge)):
        stage2_gate_score = float(stage2_entry_score_judge)
        stage2_gate_source = "judge"
    elif (not stage2_stage3_space_match) and np.isfinite(float(stage2_entry_score_judge)):
        stage2_gate_score = float(stage2_entry_score_judge)
        stage2_gate_source = "judge_auto_mismatch"
    else:
        stage2_gate_score = float(stage2_entry_score)
        stage2_gate_source = "mid"

    promoted_best_match = float("nan")
    if stage2_promoted:
        promoted_match_vals = [float(ent.get("match", float("nan"))) for ent in stage2_promoted]
        finite_promoted = [v for v in promoted_match_vals if np.isfinite(v)]
        if finite_promoted:
            promoted_best_match = float(max(finite_promoted))
    if np.isfinite(float(best2_match)):
        promoted_best_match = (
            float(best2_match)
            if (not np.isfinite(promoted_best_match))
            else float(max(float(promoted_best_match), float(best2_match)))
        )

    stage2_gap_to_oracle, band, oracle_used_for_stage3_band = resolve_stage3_gap_and_band_fn(
        dynamic_bands=list(stage3_dynamic_bands),
        stage2_gate_score=float(stage2_gate_score),
        oracle_stage3_score=float(oracle_s3),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
    )
    stage3_band_name = str(band.get("name", ""))

    stage3_phaseA_cfg = dict(stage3_phasea_cfg)
    stage3_phaseB_cfg = dict(stage3_phaseb_cfg)
    stage3_phaseB_top_n = int(stage3_phaseb_top_n)
    stage3_phaseB_gate_delta = float(stage3_phaseb_gate_delta_floor)
    stage3_phaseB_gate_end_gain = float(stage3_phaseb_gate_end_gain_floor)
    if c1_focus_enabled:
        stage3_phaseA_cfg["steps"] = int(max(int(stage3_phaseA_cfg.get("steps", 0)), int(stage3_c1_phasea_steps)))
        stage3_phaseB_cfg["steps"] = int(max(int(stage3_phaseB_cfg.get("steps", 0)), int(stage3_c1_phaseb_steps)))
        stage3_phaseB_cfg["col_every"] = 0
        stage3_phaseB_cfg["col_batch"] = 0
        stage3_phaseB_top_n = int(max(int(stage3_phaseB_top_n), int(stage3_c1_phaseb_top_n)))
        stage3_phaseB_gate_delta = float(
            max(float(stage3_phaseB_gate_delta), float(stage3_c1_phaseb_gate_delta_floor))
        )
        stage3_phaseB_gate_end_gain = float(
            max(float(stage3_phaseB_gate_end_gain), float(stage3_c1_phaseb_gate_end_gain_floor))
        )

    stage3_phaseA_cfg["steps"] = int(
        max(1, int(np.ceil(float(stage3_phaseA_cfg.get("steps", 0)) * float(stage3_period_step_mult))))
    )
    stage3_phaseB_cfg["steps"] = int(
        max(1, int(np.ceil(float(stage3_phaseB_cfg.get("steps", 0)) * float(stage3_period_step_mult))))
    )
    stage3_phaseB_top_n = int(max(1, int(stage3_phaseB_top_n) + int(stage3_period_restart_bonus)))

    solver_stage3_cfg_out = dict(solver_stage3_cfg)
    band_steps = int(band.get("steps", solver_stage3_cfg_out.get("steps", 0)))
    band_restarts = int(band.get("restarts", solver_stage3_cfg_out.get("restarts", 0)))
    band_plateau_rounds = int(band.get("plateau_rounds", solver_stage3_cfg_out.get("plateau_rounds", 0)))
    solver_stage3_cfg_out.update(
        steps=int(max(1, int(np.ceil(float(band_steps) * float(stage3_period_step_mult))))),
        restarts=int(max(1, int(band_restarts) + int(stage3_period_restart_bonus))),
        plateau_rounds=int(max(1, int(np.ceil(float(band_plateau_rounds) * float(stage3_period_step_mult))))),
        col_batch=int(band.get("col_batch", solver_stage3_cfg_out.get("col_batch", 0))),
        inner_batch=int(band.get("inner_batch", solver_stage3_cfg_out.get("inner_batch", 0))),
    )

    return dict(
        c1_focus_enabled=bool(c1_focus_enabled),
        init3_n=int(init3_n),
        init3=init3,
        promoted_keys=[list(map(int, k)) for k in promoted_keys],
        stage3_promoted_keys_count=int(len(promoted_keys)),
        stage3_period_init_mult=float(stage3_period_init_mult),
        stage3_period_step_mult=float(stage3_period_step_mult),
        stage3_period_restart_bonus=int(stage3_period_restart_bonus),
        stage2_stage3_space_match=bool(stage2_stage3_space_match),
        stage2_gate_score=float(stage2_gate_score),
        stage2_gate_source=str(stage2_gate_source),
        promoted_best_match=float(promoted_best_match),
        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
        stage3_band_name=str(stage3_band_name),
        band=dict(band),
        oracle_used_for_stage3_band=bool(oracle_used_for_stage3_band),
        stage3_phaseA_cfg=stage3_phaseA_cfg,
        stage3_phaseB_cfg=stage3_phaseB_cfg,
        stage3_phaseB_top_n=int(stage3_phaseB_top_n),
        stage3_phaseB_gate_delta=float(stage3_phaseB_gate_delta),
        stage3_phaseB_gate_end_gain=float(stage3_phaseB_gate_end_gain),
        solver_stage3_cfg=solver_stage3_cfg_out,
    )
