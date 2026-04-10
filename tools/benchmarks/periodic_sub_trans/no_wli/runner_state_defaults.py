from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, MutableMapping


def initialize_runtime_state(
    *,
    state: MutableMapping[str, Any],
    default_scorer_stage1: Mapping[str, Any],
    default_scorer_stage2: Mapping[str, Any],
    default_scorer_full: Mapping[str, Any],
    default_solver_stage1: Mapping[str, Any],
    default_solver_stage2: Mapping[str, Any],
    default_solver_stage3: Mapping[str, Any],
    default_stage3_entry_allocation_policy: str,
    default_stage3_entry_mutations_per_promoted: int,
    default_stage3_phaseb_family_preservation_policy: str,
    default_stage3_phaseb_family_view_id: str,
    default_stage3_phaseb_family_reserved_slots: int,
    default_stage3_phasec_start_policy: str,
    default_stage35_baseline_selector: str,
    default_stage3_dynamic_bands: list[dict[str, Any]],
    default_stage3_phasea_cfg: Mapping[str, Any],
    default_stage3_phaseb_cfg: Mapping[str, Any],
    default_tiers: list[tuple[str, int, int, int]],
    tier_cls: type,
) -> None:
    state["SOLVE_MATCH_THRESHOLD"] = 0.90
    state["STALL_DELTA"] = 0.002
    state["STALL_STAGE_LIMIT"] = 1
    state["HEARTBEAT_SECONDS"] = 900
    state["TIER_HEARTBEAT_SECONDS"] = 60
    state["STAGE3_HEARTBEAT_SECONDS"] = 30
    state["STAGE3_HEARTBEAT_MIN_STEP"] = 50
    state["STAGE3_HEARTBEAT_MIN_ELAPSED_SECONDS"] = 5.0
    # Use a longer preview so near-solve artifacts are easier to inspect mid-run.
    state["PREVIEW_CHARS"] = 480
    state["AUTOSKIP_PROVEN"] = True
    state["AUTOSKIP_PROVEN_MIN_MATCH"] = float(state["SOLVE_MATCH_THRESHOLD"])
    state["FORCE_RERUN_PROVEN"] = True

    state["TEXT_OFFSETS"] = [0]
    state["KEY_SEEDS"] = [111]
    state["INSTANCE_INPUT_MODE"] = "generated"
    state["INSTANCE_FIXTURE_IDS"] = []
    state["SEARCH_SEEDS"] = []

    state["STAGE1_SUB_CANDIDATES"] = 24
    state["STAGE3_INITIAL_KEYS"] = 18

    state["STAGE1_SUB_CANDIDATES_BY_COLUMNS"] = {1: 8, 3: 32, 5: 24, 7: 24, 10: 20, 13: 20}
    state["STAGE3_INITIAL_KEYS_BY_COLUMNS"] = {1: 8, 3: 36, 5: 30, 7: 40, 10: 40, 13: 48}

    state["STAGE2_EXACT_MAX_COLUMNS"] = 7
    state["STAGE2_EXACT_SUB_CANDIDATES"] = 4
    state["STAGE2_EXACT_TWO_PASS"] = True
    state["STAGE2_EXACT_PASS1_TOP_TAILS"] = 160
    state["STAGE2_EXACT_EARLY_SOLVE_BREAK"] = True
    state["STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS"] = {3: 0.2, 4: 0.8}
    state["STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS"] = {2: 1.0}
    state["STAGE2_PASS1_DIVERSITY_MIN_HAMMING_FACTOR"] = 0.40
    state["STAGE2_PASS1_DIVERSITY_MIN_FIRST_SYMBOLS"] = 3
    state["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"] = {3: 24, 5: 12, 7: 12}
    state["STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS"] = {3: 6, 5: 120, 7: 768}
    state["STAGE2_HYBRID_SUB_CANDIDATES"] = 10
    state["STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS"] = {10: 10, 13: 8}

    state["SAVE_STAGE2_TOPK"] = 12
    state["SAVE_STAGE3_TOPK"] = True
    state["SAVE_STAGE3_TOPK_LIMIT"] = 5
    state["SAVE_RESUME_HANDOFFS"] = True
    state["KAEDING_PROGRESS_EVERY_PCT"] = 1
    state["KAEDING_CONSOLE_PROGRESS"] = False

    state["STAGE1_SEED_RESTARTS"] = 96
    state["STAGE1_SEED_N_BLOCKS"] = 18
    state["STAGE1_SEED_TOTAL"] = 256
    state["STAGE1_SEED_SWAPS"] = 3
    state["STAGE12_SCOUT_RUNS"] = 6
    state["STAGE12_ARCHIVE_KEEP"] = 48
    state["STAGE12_PROMOTE_TOP"] = 24
    state["STAGE1_SCOUT_STEP_SCALE"] = 0.28
    state["STAGE1_SCOUT_RESTART_SCALE"] = 0.25
    state["STAGE1_SCOUT_MIN_STEPS"] = 900
    state["STAGE1_SCOUT_MIN_RESTARTS"] = 1
    state["STAGE1_SCOUT_NO_IMPROVE_DELTA"] = 1e-6
    state["STAGE1_SCOUT_NO_IMPROVE_PATIENCE"] = 1
    state["STAGE1_SCOUT_MIN_NEW_ARCHIVE"] = 4
    state["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"] = 2

    state["STAGE3_DYNAMIC_BANDS"] = [dict(b) for b in default_stage3_dynamic_bands]
    state["STAGE3_TWO_PHASE_ENABLED"] = False
    state["STAGE3_PHASEA_CFG"] = deepcopy(default_stage3_phasea_cfg)
    state["STAGE3_PHASEB_CFG"] = deepcopy(default_stage3_phaseb_cfg)
    state["STAGE3_PHASEB_TOP_N"] = 8
    state["STAGE3_PHASEB_GATE_DELTA_FLOOR"] = 0.008
    state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"] = 0.004
    state["STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY"] = str(
        default_stage3_phaseb_family_preservation_policy
    )
    state["STAGE3_PHASEB_FAMILY_VIEW_ID"] = str(default_stage3_phaseb_family_view_id)
    state["STAGE3_PHASEB_FAMILY_RESERVED_SLOTS"] = int(
        max(0, int(default_stage3_phaseb_family_reserved_slots))
    )
    state["STAGE3_PHASEC_ENABLED"] = True
    state["STAGE3_PHASEC_CFG"] = {
        "steps": 32,
        "proposals_per_step": 24,
        "three_cycle_prob": 0.15,
    }
    state["STAGE3_PHASEC_START_KEYS"] = 12
    state["STAGE3_PHASEC_SEED_OFFSET"] = 1200003
    state["STAGE3_PHASEC_WORD_NGRAM_TIEBREAK"] = True
    state["STAGE3_PHASEC_START_POLICY"] = str(default_stage3_phasec_start_policy)
    state["STAGE35_ENABLED"] = False
    state["STAGE35_BASELINE_SELECTOR"] = str(default_stage35_baseline_selector)
    state["STAGE35_CFG"] = {
        "seed_keep": 4,
        "beam_width": 4,
        "archive_keep": 16,
        "rounds": 3,
        "mini_search_steps": 2,
        "mini_search_beam_width": 3,
        "mini_search_top_symbols": 10,
        "mini_search_final_keep": 2,
        "mini_search_keep_all_rows": 0,
        "accept_score_min_gain": 0,
        "accept_search_score_max_drop": 0,
    }
    state["STAGE3_SPAN_BASIN_JUDGE_K"] = 32
    state["STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE"] = True
    state["STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH"] = True
    state["STAGE3_SPAN_BASIN_JUDGE_TIE_EPS"] = 0.001
    state["STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS"] = 48
    state["RUN_STAGE3_SPAN_BASIN_K_SWEEP"] = True
    state["STAGE3_SPAN_BASIN_K_SWEEP_VALUES"] = [96]

    state["STAGE3_C1_FOCUS_ENABLED"] = True
    state["STAGE3_C1_INIT_KEYS"] = 96
    state["STAGE3_C1_PHASEA_STEPS"] = 1200
    state["STAGE3_C1_PHASEB_STEPS"] = 6000
    state["STAGE3_C1_PHASEB_TOP_N"] = 24
    state["STAGE3_C1_PHASEB_GATE_DELTA_FLOOR"] = 0.010
    state["STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR"] = 0.006
    state["STAGE3_CONTINUE_AFTER_SOLVE"] = False
    state["STAGE3_ENTRY_ALLOCATION_POLICY"] = str(
        default_stage3_entry_allocation_policy
    )
    state["STAGE3_ENTRY_MUTATIONS_PER_PROMOTED"] = int(
        max(1, int(default_stage3_entry_mutations_per_promoted))
    )

    state["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"] = {}
    state["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"] = {}
    state["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"] = {}
    state["STAGE3_INIT_KEYS_CAP"] = 192

    state["_STAGE3_TWO_PHASE_ENABLED_DEFAULT"] = bool(state["STAGE3_TWO_PHASE_ENABLED"])
    state["_STAGE3_PHASEA_CFG_DEFAULT"] = dict(state["STAGE3_PHASEA_CFG"])
    state["_STAGE3_PHASEB_CFG_DEFAULT"] = dict(state["STAGE3_PHASEB_CFG"])
    state["_STAGE3_PHASEB_TOP_N_DEFAULT"] = int(state["STAGE3_PHASEB_TOP_N"])
    state["_STAGE3_PHASEB_GATE_DELTA_FLOOR_DEFAULT"] = float(state["STAGE3_PHASEB_GATE_DELTA_FLOOR"])
    state["_STAGE3_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT"] = float(state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"])
    state["_STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY_DEFAULT"] = str(
        state["STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY"]
    )
    state["_STAGE3_PHASEB_FAMILY_VIEW_ID_DEFAULT"] = str(
        state["STAGE3_PHASEB_FAMILY_VIEW_ID"]
    )
    state["_STAGE3_PHASEB_FAMILY_RESERVED_SLOTS_DEFAULT"] = int(
        state["STAGE3_PHASEB_FAMILY_RESERVED_SLOTS"]
    )
    state["_STAGE3_PHASEC_ENABLED_DEFAULT"] = bool(state["STAGE3_PHASEC_ENABLED"])
    state["_STAGE3_PHASEC_CFG_DEFAULT"] = dict(state["STAGE3_PHASEC_CFG"])
    state["_STAGE3_PHASEC_START_KEYS_DEFAULT"] = int(state["STAGE3_PHASEC_START_KEYS"])
    state["_STAGE3_PHASEC_SEED_OFFSET_DEFAULT"] = int(state["STAGE3_PHASEC_SEED_OFFSET"])
    state["_STAGE3_PHASEC_WORD_NGRAM_TIEBREAK_DEFAULT"] = bool(
        state["STAGE3_PHASEC_WORD_NGRAM_TIEBREAK"]
    )
    state["_STAGE3_PHASEC_START_POLICY_DEFAULT"] = str(
        state["STAGE3_PHASEC_START_POLICY"]
    )
    state["_STAGE35_ENABLED_DEFAULT"] = bool(state["STAGE35_ENABLED"])
    state["_STAGE35_BASELINE_SELECTOR_DEFAULT"] = str(
        state["STAGE35_BASELINE_SELECTOR"]
    )
    state["_STAGE35_CFG_DEFAULT"] = dict(state["STAGE35_CFG"])
    state["_STAGE3_SPAN_BASIN_JUDGE_TIE_EPS_DEFAULT"] = float(
        state["STAGE3_SPAN_BASIN_JUDGE_TIE_EPS"]
    )
    state["_STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS_DEFAULT"] = int(
        state["STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS"]
    )
    state["_STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS_DEFAULT"] = int(state["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"])
    state["_STAGE3_C1_FOCUS_ENABLED_DEFAULT"] = bool(state["STAGE3_C1_FOCUS_ENABLED"])
    state["_STAGE3_C1_INIT_KEYS_DEFAULT"] = int(state["STAGE3_C1_INIT_KEYS"])
    state["_STAGE3_C1_PHASEA_STEPS_DEFAULT"] = int(state["STAGE3_C1_PHASEA_STEPS"])
    state["_STAGE3_C1_PHASEB_STEPS_DEFAULT"] = int(state["STAGE3_C1_PHASEB_STEPS"])
    state["_STAGE3_C1_PHASEB_TOP_N_DEFAULT"] = int(state["STAGE3_C1_PHASEB_TOP_N"])
    state["_STAGE3_C1_PHASEB_GATE_DELTA_FLOOR_DEFAULT"] = float(state["STAGE3_C1_PHASEB_GATE_DELTA_FLOOR"])
    state["_STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR_DEFAULT"] = float(state["STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR"])
    state["_STAGE3_CONTINUE_AFTER_SOLVE_DEFAULT"] = bool(state["STAGE3_CONTINUE_AFTER_SOLVE"])
    state["_STAGE3_ENTRY_ALLOCATION_POLICY_DEFAULT"] = str(
        state["STAGE3_ENTRY_ALLOCATION_POLICY"]
    )
    state["_STAGE3_ENTRY_MUTATIONS_PER_PROMOTED_DEFAULT"] = int(
        state["STAGE3_ENTRY_MUTATIONS_PER_PROMOTED"]
    )
    state["_STAGE3_PERIOD_INIT_MULT_BY_PERIOD_DEFAULT"] = dict(state["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"])
    state["_STAGE3_PERIOD_STEP_MULT_BY_PERIOD_DEFAULT"] = dict(state["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"])
    state["_STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD_DEFAULT"] = dict(state["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"])
    state["_STAGE3_INIT_KEYS_CAP_DEFAULT"] = int(state["STAGE3_INIT_KEYS_CAP"])
    state["_ORACLE_ASSIST_SELECTION_DEFAULT"] = bool(state["ORACLE_ASSIST_SELECTION"])
    state["_INSTANCE_INPUT_MODE_DEFAULT"] = str(state["INSTANCE_INPUT_MODE"])
    state["_INSTANCE_FIXTURE_IDS_DEFAULT"] = [str(x) for x in state["INSTANCE_FIXTURE_IDS"]]
    state["_SEARCH_SEEDS_DEFAULT"] = [int(x) for x in state["SEARCH_SEEDS"]]

    state["SCORER_STAGE1"] = deepcopy(default_scorer_stage1)
    state["SCORER_STAGE2"] = deepcopy(default_scorer_stage2)
    state["SCORER_FULL"] = deepcopy(default_scorer_full)
    state["SCORER_STAGE1"]["impl"] = state["SCORER_IMPL"]
    state["SCORER_STAGE2"]["impl"] = state["SCORER_IMPL"]
    state["SCORER_FULL"]["impl"] = state["SCORER_IMPL"]

    state["SOLVER_STAGE1"] = deepcopy(default_solver_stage1)
    state["SOLVER_STAGE2"] = deepcopy(default_solver_stage2)
    state["SOLVER_STAGE3"] = deepcopy(default_solver_stage3)

    state["TIERS"] = [
        tier_cls(str(name), int(period), int(columns), int(length))
        for name, period, columns, length in default_tiers
    ]
