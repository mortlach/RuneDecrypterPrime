from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, MutableMapping


def build_setup_logging_payload(
    *,
    state: MutableMapping[str, Any],
    run_config: Mapping[str, Any],
    scoring_experiment_meta: Mapping[str, Any],
    mode_canonical: str,
    mode_raw: str,
    mode_intent: str,
    stage3_can_skip: bool,
    direction_value: str,
    oracle_mode: str,
    oracle_assist_selection_effective: bool,
    autoskip_effective: bool,
    proven_known: int,
    hist_rel_path: str,
    non_scoring_lock_hash: str,
    scoring_lock_hash: str,
    run_config_hash: str,
    reports_rel_path: str,
    audit_csv_rel_path: str,
    audit_jsonl_rel_path: str,
    scorer_objective_summary_fn: Callable[[Dict[str, Any]], str],
    weights_text_fn: Callable[[Dict[int, float]], str],
    stage3_search_cfg_preview: Dict[str, Any],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    return dict(
        profile=str(state["PROFILE"]),
        mode_canonical=str(mode_canonical),
        mode_raw=str(mode_raw),
        mode_intent=str(mode_intent),
        stage3_can_skip=bool(stage3_can_skip),
        direction_value=str(direction_value),
        order=str(state["ORDER"]),
        alphabet_size=int(state["ALPHABET_SIZE"]),
        oracle_mode=str(oracle_mode),
        oracle_assist_selection_requested=bool(state["ORACLE_ASSIST_SELECTION"]),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        autoskip_effective=bool(autoskip_effective),
        autoskip_requested=bool(state["AUTOSKIP_PROVEN"]),
        force_rerun_proven=bool(state["FORCE_RERUN_PROVEN"]),
        autoskip_min_match=float(state["AUTOSKIP_PROVEN_MIN_MATCH"]),
        proven_known=int(proven_known),
        hist_rel_path=str(hist_rel_path),
        profile_id=str(state["NO_WLI_PIPELINE_PROFILE_ID"]),
        profile_previous_default=str(state["NO_WLI_PIPELINE_PROFILE_ID_PREVIOUS_DEFAULT"]),
        scorer_impl_stage12=str(getattr(state["SCORER_IMPL"], "value", state["SCORER_IMPL"])),
        scorer_impl_stage3=str(state["SCORER_FULL"].get("impl", state["SCORER_IMPL"])),
        scorer_stage1_label=str(state["SCORER_STAGE1_LABEL"]),
        scorer_stage2_label=str(state["SCORER_STAGE2_LABEL"]),
        scorer_stage3_label=str(state["SCORER_STAGE3_LABEL"]),
        scorer_stage1_summary=str(scorer_objective_summary_fn(state["SCORER_STAGE1"])),
        scorer_stage2_summary=str(scorer_objective_summary_fn(state["SCORER_STAGE2"])),
        scorer_stage3_summary=str(scorer_objective_summary_fn(state["SCORER_FULL"])),
        require_no_ecdf_for_avg_fulltext=bool(state["REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT"]),
        stage3_search_summary=str(scorer_objective_summary_fn(stage3_search_cfg_preview)),
        stage3_judge_summary=str(scorer_objective_summary_fn(state["SCORER_FULL"])),
        stage3_basin_judge_k=int(state["STAGE3_SPAN_BASIN_JUDGE_K"]),
        scoring_experiment_profile=str(scoring_experiment_meta.get("profile", "off")),
        scoring_experiment_enabled=bool(scoring_experiment_meta.get("enabled", False)),
        scoring_experiment_desc=str(scoring_experiment_meta.get("description", "")),
        phase_experiments_enabled=bool(
            run_config.get("stage3_phase_experiments", {}).get("enabled", False)
        ),
        phase_experiments_phaseA=str(
            run_config.get("stage3_phase_experiments", {}).get("phaseA", "off")
        ),
        phase_experiments_phaseB=str(
            run_config.get("stage3_phase_experiments", {}).get("phaseB", "off")
        ),
        phase_experiments_phaseB_char_gate_policy=str(
            run_config.get("stage3_phase_experiments", {}).get(
                "phaseB_char_pct_min_policy", "static_config"
            )
        ),
        non_scoring_lock_hash=str(non_scoring_lock_hash),
        scoring_lock_hash=str(scoring_lock_hash),
        run_config_hash=str(run_config_hash),
        stage1_seed_restarts=int(state["STAGE1_SEED_RESTARTS"]),
        stage1_seed_n_blocks=int(state["STAGE1_SEED_N_BLOCKS"]),
        stage1_seed_total=int(state["STAGE1_SEED_TOTAL"]),
        stage1_seed_swaps=int(state["STAGE1_SEED_SWAPS"]),
        stage12_scout_runs=int(state["STAGE12_SCOUT_RUNS"]),
        stage12_archive_keep=int(state["STAGE12_ARCHIVE_KEEP"]),
        stage12_promote_top=int(state["STAGE12_PROMOTE_TOP"]),
        stage1_scout_step_scale=float(state["STAGE1_SCOUT_STEP_SCALE"]),
        stage1_scout_restart_scale=float(state["STAGE1_SCOUT_RESTART_SCALE"]),
        stage1_scout_min_steps=int(state["STAGE1_SCOUT_MIN_STEPS"]),
        stage1_scout_min_restarts=int(state["STAGE1_SCOUT_MIN_RESTARTS"]),
        stage1_scout_no_improve_delta=float(state["STAGE1_SCOUT_NO_IMPROVE_DELTA"]),
        stage1_scout_no_improve_patience=int(state["STAGE1_SCOUT_NO_IMPROVE_PATIENCE"]),
        stage1_scout_min_new_archive=int(state["STAGE1_SCOUT_MIN_NEW_ARCHIVE"]),
        stage1_scout_early_stop_min_scouts=int(state["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"]),
        stage1_sub_candidates=int(state["STAGE1_SUB_CANDIDATES"]),
        stage1_sub_candidates_by_columns=dict(state["STAGE1_SUB_CANDIDATES_BY_COLUMNS"]),
        stage3_initial_keys=int(state["STAGE3_INITIAL_KEYS"]),
        stage3_initial_keys_by_columns=dict(state["STAGE3_INITIAL_KEYS_BY_COLUMNS"]),
        stage3_period_init_mult_by_period=dict(state["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"]),
        stage3_period_step_mult_by_period=dict(state["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"]),
        stage3_period_restart_bonus_by_period=dict(
            state["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"]
        ),
        stage3_init_keys_cap=int(state["STAGE3_INIT_KEYS_CAP"]),
        stage2_exact_max_columns=int(state["STAGE2_EXACT_MAX_COLUMNS"]),
        stage2_exact_sub_candidates=int(state["STAGE2_EXACT_SUB_CANDIDATES"]),
        stage2_exact_sub_candidates_by_columns=dict(
            state["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"]
        ),
        stage2_pass1_primary_text=str(
            weights_text_fn(state["STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS"])
        ),
        stage2_pass1_fallback_text=str(
            weights_text_fn(state["STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS"])
        ),
        stage2_hybrid_sub_candidates=int(state["STAGE2_HYBRID_SUB_CANDIDATES"]),
        stage2_hybrid_sub_candidates_by_columns=dict(
            state["STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS"]
        ),
        stage3_two_phase_enabled=bool(state["STAGE3_TWO_PHASE_ENABLED"]),
        stage3_phasea_cfg=dict(state["STAGE3_PHASEA_CFG"]),
        stage3_phaseb_cfg=dict(state["STAGE3_PHASEB_CFG"]),
        stage3_phaseb_top_n=int(state["STAGE3_PHASEB_TOP_N"]),
        stage3_continue_after_solve=bool(state["STAGE3_CONTINUE_AFTER_SOLVE"]),
        stage3_phaseb_gate_delta_floor=float(state["STAGE3_PHASEB_GATE_DELTA_FLOOR"]),
        stage3_phaseb_gate_end_gain_floor=float(
            state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"]
        ),
        stage3_c1_focus_enabled=bool(state["STAGE3_C1_FOCUS_ENABLED"]),
        stage3_c1_init_keys=int(state["STAGE3_C1_INIT_KEYS"]),
        stage3_c1_phasea_steps=int(state["STAGE3_C1_PHASEA_STEPS"]),
        stage3_c1_phaseb_steps=int(state["STAGE3_C1_PHASEB_STEPS"]),
        stage3_c1_phaseb_top_n=int(state["STAGE3_C1_PHASEB_TOP_N"]),
        stage3_c1_phaseb_gate_delta_floor=float(
            state["STAGE3_C1_PHASEB_GATE_DELTA_FLOOR"]
        ),
        stage3_c1_phaseb_gate_end_gain_floor=float(
            state["STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR"]
        ),
        scan_tier_time_cap_seconds=float(state["SCAN_TIER_TIME_CAP_SECONDS"]),
        scan_stage2_continue_to_gate=bool(state["SCAN_STAGE2_CONTINUE_TO_GATE"]),
        scan_stage2_continue_cap_seconds=float(state["SCAN_STAGE2_CONTINUE_CAP_SECONDS"]),
        scan_stage3_gate_low_match=float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
        scan_stage3_gate_high_match=float(
            max(
                float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
                float(state["SCAN_STAGE3_GATE_HIGH_MATCH"]),
            )
        ),
        tiers_count=int(len(state["TIERS"])),
        text_offsets=list(map(int, state["TEXT_OFFSETS"])),
        key_seeds=list(map(int, state["KEY_SEEDS"])),
        reports_rel_path=str(reports_rel_path),
        audit_csv_rel_path=str(audit_csv_rel_path),
        audit_jsonl_rel_path=str(audit_jsonl_rel_path),
        log_prefix=str(log_prefix),
    )
