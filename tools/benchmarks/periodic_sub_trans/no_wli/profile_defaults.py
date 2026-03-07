from __future__ import annotations

from typing import Any, Callable, Dict, MutableMapping


def apply_profile_defaults_from_profile(
    *,
    state: MutableMapping[str, Any],
    profile: Any,
    effective_stage3_impl_fn: Callable[[Dict[str, Any]], str],
) -> None:
    state["PROFILE"] = str(profile.profile_id)
    state["SCORER_STAGE1_LABEL"] = str(profile.scorer_schedule.stage1_label)
    state["SCORER_STAGE2_LABEL"] = str(profile.scorer_schedule.stage2_label)
    state["SCORER_STAGE3_LABEL"] = str(profile.scorer_schedule.stage3_label)
    state["SCORER_STAGE1"] = profile.scorer_schedule.stage1_a.to_params()
    state["SCORER_STAGE2"] = profile.scorer_schedule.stage2_m.to_params()
    state["SCORER_FULL"] = profile.scorer_schedule.stage3_b.to_params()
    state["SCORER_STAGE1"]["impl"] = state["SCORER_IMPL"]
    state["SCORER_STAGE2"]["impl"] = state["SCORER_IMPL"]
    state["SCORER_FULL"]["impl"] = effective_stage3_impl_fn(state["SCORER_FULL"])

    state["STAGE1_SUB_CANDIDATES"] = int(profile.stage1_sub_candidates)
    state["STAGE3_INITIAL_KEYS"] = int(profile.stage3_initial_keys)
    state["STAGE1_SUB_CANDIDATES_BY_COLUMNS"] = {
        int(k): int(v) for k, v in profile.stage1_sub_candidates_by_columns.items()
    }
    state["STAGE3_INITIAL_KEYS_BY_COLUMNS"] = {
        int(k): int(v) for k, v in profile.stage3_initial_keys_by_columns.items()
    }

    state["STAGE2_EXACT_MAX_COLUMNS"] = int(profile.stage2_exact_max_columns)
    state["STAGE2_EXACT_SUB_CANDIDATES"] = int(profile.stage2_exact_sub_candidates)
    state["STAGE2_EXACT_TWO_PASS"] = bool(profile.stage2_exact_two_pass)
    state["STAGE2_EXACT_PASS1_TOP_TAILS"] = int(profile.stage2_exact_pass1_top_tails)
    state["STAGE2_EXACT_EARLY_SOLVE_BREAK"] = bool(profile.stage2_exact_early_solve_break)
    state["STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS"] = {
        int(k): float(v) for k, v in profile.scorer_schedule.stage2_pass1_primary.items()
    }
    state["STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS"] = {
        int(k): float(v)
        for k, v in profile.scorer_schedule.stage2_pass1_fallback.items()
    }
    state["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"] = {
        int(k): int(v)
        for k, v in profile.stage2_exact_sub_candidates_by_columns.items()
    }
    state["STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS"] = {
        int(k): int(v)
        for k, v in profile.stage2_exact_pass1_top_tails_by_columns.items()
    }
    state["STAGE2_HYBRID_SUB_CANDIDATES"] = int(profile.stage2_hybrid_sub_candidates)
    state["STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS"] = {
        int(k): int(v)
        for k, v in profile.stage2_hybrid_sub_candidates_by_columns.items()
    }

    state["STAGE1_SEED_RESTARTS"] = int(profile.stage1_seed_restarts)
    state["STAGE1_SEED_N_BLOCKS"] = int(profile.stage1_seed_n_blocks)
    state["STAGE1_SEED_TOTAL"] = int(profile.stage1_seed_total)
    state["STAGE1_SEED_SWAPS"] = int(profile.stage1_seed_swaps)
    state["STAGE12_SCOUT_RUNS"] = int(profile.stage12_scout_runs)
    state["STAGE12_ARCHIVE_KEEP"] = int(profile.stage12_archive_keep)
    state["STAGE12_PROMOTE_TOP"] = int(profile.stage12_promote_top)
    state["STAGE1_SCOUT_STEP_SCALE"] = float(profile.stage1_scout_step_scale)
    state["STAGE1_SCOUT_RESTART_SCALE"] = float(profile.stage1_scout_restart_scale)
    state["STAGE1_SCOUT_MIN_STEPS"] = int(profile.stage1_scout_min_steps)
    state["STAGE1_SCOUT_MIN_RESTARTS"] = int(profile.stage1_scout_min_restarts)
    state["STAGE1_SCOUT_NO_IMPROVE_DELTA"] = float(profile.stage1_scout_no_improve_delta)
    state["STAGE1_SCOUT_NO_IMPROVE_PATIENCE"] = int(profile.stage1_scout_no_improve_patience)
    state["STAGE1_SCOUT_MIN_NEW_ARCHIVE"] = int(profile.stage1_scout_min_new_archive)
    state["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"] = int(
        state["_STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS_DEFAULT"]
    )

    state["STAGE3_DYNAMIC_BANDS"] = [dict(x) for x in profile.stage3_dynamic_bands]
    state["SOLVER_STAGE1"] = dict(profile.solver_stage1)
    state["SOLVER_STAGE2"] = dict(profile.solver_stage2)
    state["SOLVER_STAGE3"] = dict(profile.solver_stage3)
    state["STAGE3_TWO_PHASE_ENABLED"] = bool(state["_STAGE3_TWO_PHASE_ENABLED_DEFAULT"])
    state["STAGE3_PHASEA_CFG"] = dict(state["_STAGE3_PHASEA_CFG_DEFAULT"])
    state["STAGE3_PHASEB_CFG"] = dict(state["_STAGE3_PHASEB_CFG_DEFAULT"])
    state["STAGE3_PHASEB_TOP_N"] = int(state["_STAGE3_PHASEB_TOP_N_DEFAULT"])
    state["STAGE3_PHASEB_GATE_DELTA_FLOOR"] = float(
        state["_STAGE3_PHASEB_GATE_DELTA_FLOOR_DEFAULT"]
    )
    state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"] = float(
        state["_STAGE3_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT"]
    )
    state["STAGE3_C1_FOCUS_ENABLED"] = bool(state["_STAGE3_C1_FOCUS_ENABLED_DEFAULT"])
    state["STAGE3_C1_INIT_KEYS"] = int(state["_STAGE3_C1_INIT_KEYS_DEFAULT"])
    state["STAGE3_C1_PHASEA_STEPS"] = int(state["_STAGE3_C1_PHASEA_STEPS_DEFAULT"])
    state["STAGE3_C1_PHASEB_STEPS"] = int(state["_STAGE3_C1_PHASEB_STEPS_DEFAULT"])
    state["STAGE3_C1_PHASEB_TOP_N"] = int(state["_STAGE3_C1_PHASEB_TOP_N_DEFAULT"])
    state["STAGE3_C1_PHASEB_GATE_DELTA_FLOOR"] = float(
        state["_STAGE3_C1_PHASEB_GATE_DELTA_FLOOR_DEFAULT"]
    )
    state["STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR"] = float(
        state["_STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT"]
    )
    state["STAGE3_CONTINUE_AFTER_SOLVE"] = bool(state["_STAGE3_CONTINUE_AFTER_SOLVE_DEFAULT"])
    state["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"] = dict(
        state["_STAGE3_PERIOD_INIT_MULT_BY_PERIOD_DEFAULT"]
    )
    state["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"] = dict(
        state["_STAGE3_PERIOD_STEP_MULT_BY_PERIOD_DEFAULT"]
    )
    state["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"] = dict(
        state["_STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD_DEFAULT"]
    )
    state["STAGE3_INIT_KEYS_CAP"] = int(state["_STAGE3_INIT_KEYS_CAP_DEFAULT"])
    state["ORACLE_ASSIST_SELECTION"] = bool(state["_ORACLE_ASSIST_SELECTION_DEFAULT"])
    state["SCAN_TIER_TIME_CAP_SECONDS"] = float(state["_SCAN_TIER_TIME_CAP_SECONDS_DEFAULT"])
    state["SCAN_STAGE3_GATE_LOW_MATCH"] = float(state["_SCAN_STAGE3_GATE_LOW_MATCH_DEFAULT"])
    state["SCAN_STAGE3_GATE_HIGH_MATCH"] = float(
        max(
            float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
            float(state["_SCAN_STAGE3_GATE_HIGH_MATCH_DEFAULT"]),
        )
    )
    state["SCAN_STAGE3_MIN_STAGE2_MATCH"] = float(state["SCAN_STAGE3_GATE_LOW_MATCH"])
    state["SCAN_STAGE2_CONTINUE_TO_GATE"] = bool(state["_SCAN_STAGE2_CONTINUE_TO_GATE_DEFAULT"])
    state["SCAN_STAGE2_CONTINUE_CAP_SECONDS"] = float(
        state["_SCAN_STAGE2_CONTINUE_CAP_SECONDS_DEFAULT"]
    )

    if str(profile.profile_id) == str(state["NO_WLI_LONGRUN3X_PROFILE_ID"]):
        state["STAGE3_TWO_PHASE_ENABLED"] = True
        state["STAGE3_PHASEA_CFG"] = {
            "steps": 900,
            "restarts": 1,
            "inner_batch": 96,
            "col_every": 0,
            "col_batch": 0,
            "slip_every": 0,
            "slip_swaps": 0,
            "stall_slip_limit": 0,
        }
        state["STAGE3_PHASEB_CFG"] = {
            "steps": 4200,
            "inner_batch": 128,
            "col_every": 1,
            "col_batch": 128,
            "slip_every": 70,
            "stall_rounds": 240,
            "stall_slip_limit": 8,
            "slip_swaps": 28,
        }
        state["STAGE3_PHASEB_TOP_N"] = 16
        state["STAGE3_PHASEB_GATE_DELTA_FLOOR"] = 0.008
        state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"] = 0.004
        state["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"] = int(
            max(1, int(state["STAGE12_SCOUT_RUNS"]))
        )


def apply_kaeding_progress_settings(*, state: MutableMapping[str, Any]) -> None:
    pct = int(max(1, int(state["KAEDING_PROGRESS_EVERY_PCT"])))
    print_progress = bool(state["KAEDING_CONSOLE_PROGRESS"])
    state["SOLVER_STAGE1"]["progress_pct"] = int(pct)
    state["SOLVER_STAGE1"]["print_progress"] = bool(print_progress)
    state["SOLVER_STAGE3"]["progress_pct"] = int(pct)
    state["SOLVER_STAGE3"]["print_progress"] = bool(print_progress)
    state["STAGE3_PHASEA_CFG"]["progress_pct"] = int(pct)
    state["STAGE3_PHASEA_CFG"]["print_progress"] = bool(print_progress)
    state["STAGE3_PHASEB_CFG"]["progress_pct"] = int(pct)
    state["STAGE3_PHASEB_CFG"]["print_progress"] = bool(print_progress)
