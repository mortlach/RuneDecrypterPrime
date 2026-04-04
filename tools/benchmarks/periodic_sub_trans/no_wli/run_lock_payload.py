from __future__ import annotations

from typing import Any, Callable, Dict, Mapping


def build_non_scoring_lock_payload(
    *,
    state: Mapping[str, Any],
    build_run_mode_info_fn: Callable[[str | None], Any],
) -> Dict[str, Any]:
    mode_info = build_run_mode_info_fn(state["PIPELINE_RUN_MODE"])
    tiers = list(state["TIERS"])
    return dict(
        mode=str(mode_info.mode_canonical),
        mode_raw=str(mode_info.mode_raw),
        mode_intent=str(mode_info.intent),
        stage3_can_skip=bool(mode_info.stage3_can_skip),
        direction=str(state["ENCODING_DIR"]),
        order=str(state["ORDER"]),
        alphabet_size=int(state["ALPHABET_SIZE"]),
        solve_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
        stall_delta=float(state["STALL_DELTA"]),
        stall_stage_limit=int(state["STALL_STAGE_LIMIT"]),
        scan_controls=dict(
            tier_time_cap_seconds=float(state["SCAN_TIER_TIME_CAP_SECONDS"]),
            stage2_continue_to_gate=bool(state["SCAN_STAGE2_CONTINUE_TO_GATE"]),
            stage2_continue_cap_seconds=float(state["SCAN_STAGE2_CONTINUE_CAP_SECONDS"]),
            stage3_gate_low_match=float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
            stage3_gate_high_match=float(
                max(
                    float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
                    float(state["SCAN_STAGE3_GATE_HIGH_MATCH"]),
                )
            ),
        ),
        text_offsets=[int(x) for x in state["TEXT_OFFSETS"]],
        key_seeds=[int(x) for x in state["KEY_SEEDS"]],
        tiers=[
            dict(
                name=str(t.name),
                period=int(t.period),
                columns=int(t.columns),
                length=int(t.length),
            )
            for t in tiers
        ],
        stage1_search=dict(
            seed_restarts=int(state["STAGE1_SEED_RESTARTS"]),
            seed_n_blocks=int(state["STAGE1_SEED_N_BLOCKS"]),
            seed_total=int(state["STAGE1_SEED_TOTAL"]),
            seed_swaps=int(state["STAGE1_SEED_SWAPS"]),
            scout_runs=int(state["STAGE12_SCOUT_RUNS"]),
            archive_keep=int(state["STAGE12_ARCHIVE_KEEP"]),
            promote_top=int(state["STAGE12_PROMOTE_TOP"]),
            scout_step_scale=float(state["STAGE1_SCOUT_STEP_SCALE"]),
            scout_restart_scale=float(state["STAGE1_SCOUT_RESTART_SCALE"]),
            scout_min_steps=int(state["STAGE1_SCOUT_MIN_STEPS"]),
            scout_min_restarts=int(state["STAGE1_SCOUT_MIN_RESTARTS"]),
            scout_no_improve_delta=float(state["STAGE1_SCOUT_NO_IMPROVE_DELTA"]),
            scout_no_improve_patience=int(state["STAGE1_SCOUT_NO_IMPROVE_PATIENCE"]),
            scout_min_new_archive=int(state["STAGE1_SCOUT_MIN_NEW_ARCHIVE"]),
            scout_early_stop_min_scouts=int(state["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"]),
            sub_candidates=int(state["STAGE1_SUB_CANDIDATES"]),
            sub_candidates_by_columns={
                str(k): int(v)
                for k, v in state["STAGE1_SUB_CANDIDATES_BY_COLUMNS"].items()
            },
        ),
        stage2_search=dict(
            exact_max_columns=int(state["STAGE2_EXACT_MAX_COLUMNS"]),
            exact_sub_candidates=int(state["STAGE2_EXACT_SUB_CANDIDATES"]),
            exact_sub_by_columns={
                str(k): int(v)
                for k, v in state["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"].items()
            },
            exact_two_pass=bool(state["STAGE2_EXACT_TWO_PASS"]),
            exact_pass1_top_tails=int(state["STAGE2_EXACT_PASS1_TOP_TAILS"]),
            exact_pass1_top_by_columns={
                str(k): int(v)
                for k, v in state["STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS"].items()
            },
            exact_early_solve_break=bool(state["STAGE2_EXACT_EARLY_SOLVE_BREAK"]),
            hybrid_sub_candidates=int(state["STAGE2_HYBRID_SUB_CANDIDATES"]),
            hybrid_sub_by_columns={
                str(k): int(v)
                for k, v in state["STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS"].items()
            },
            judge_policy=str(state["STAGE2_JUDGE_POLICY"]),
            promote_by_stage3_judge=bool(state["STAGE2_PROMOTE_BY_STAGE3_JUDGE"]),
            entry_band_by_stage3_judge=bool(state["STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE"]),
        ),
        stage3_search=dict(
            solver=dict(state["SOLVER_STAGE3"]),
            entry=dict(
                allocation_policy=str(state["STAGE3_ENTRY_ALLOCATION_POLICY"]),
                mutations_per_promoted=int(
                    state["STAGE3_ENTRY_MUTATIONS_PER_PROMOTED"]
                ),
            ),
            init_keys=int(state["STAGE3_INITIAL_KEYS"]),
            init_by_columns={
                str(k): int(v) for k, v in state["STAGE3_INITIAL_KEYS_BY_COLUMNS"].items()
            },
            span_basin_judge_k=int(state["STAGE3_SPAN_BASIN_JUDGE_K"]),
            span_basin_judge_require_span_active=bool(
                state["STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE"]
            ),
            span_basin_judge_dedupe_by_end_hash=bool(
                state["STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH"]
            ),
            span_basin_judge_tie_eps=float(state["STAGE3_SPAN_BASIN_JUDGE_TIE_EPS"]),
            span_basin_judge_tie_max_seeds=int(
                state["STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS"]
            ),
            span_basin_judge_k_sweep=dict(
                enabled=bool(state["RUN_STAGE3_SPAN_BASIN_K_SWEEP"]),
                values=[int(v) for v in state["STAGE3_SPAN_BASIN_K_SWEEP_VALUES"]],
            ),
            dynamic_bands=[dict(b) for b in state["STAGE3_DYNAMIC_BANDS"]],
            two_phase_enabled=bool(state["STAGE3_TWO_PHASE_ENABLED"]),
            phase_a=dict(state["STAGE3_PHASEA_CFG"]),
            phase_b=dict(state["STAGE3_PHASEB_CFG"]),
            phase_b_top_n=int(state["STAGE3_PHASEB_TOP_N"]),
            phase_b_gate_delta=float(state["STAGE3_PHASEB_GATE_DELTA_FLOOR"]),
            phase_b_gate_end_gain=float(state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"]),
            phase_b_family_preservation=dict(
                policy=str(state["STAGE3_PHASEB_FAMILY_PRESERVATION_POLICY"]),
                family_view_id=str(state["STAGE3_PHASEB_FAMILY_VIEW_ID"]),
                reserved_slots=int(state["STAGE3_PHASEB_FAMILY_RESERVED_SLOTS"]),
            ),
            phase_c=dict(
                enabled=bool(state["STAGE3_PHASEC_ENABLED"]),
                cfg=dict(state["STAGE3_PHASEC_CFG"]),
                start_keys=int(state["STAGE3_PHASEC_START_KEYS"]),
                seed_offset=int(state["STAGE3_PHASEC_SEED_OFFSET"]),
                word_ngram_tiebreak=bool(
                    state["STAGE3_PHASEC_WORD_NGRAM_TIEBREAK"]
                ),
                start_policy=str(state["STAGE3_PHASEC_START_POLICY"]),
            ),
            stage35=dict(
                enabled=bool(state["STAGE35_ENABLED"]),
                baseline_selector=str(state["STAGE35_BASELINE_SELECTOR"]),
                cfg=dict(state["STAGE35_CFG"]),
            ),
            continue_after_solve=bool(state["STAGE3_CONTINUE_AFTER_SOLVE"]),
            c1_focus_enabled=bool(state["STAGE3_C1_FOCUS_ENABLED"]),
            c1_init_keys=int(state["STAGE3_C1_INIT_KEYS"]),
            c1_phase_a_steps=int(state["STAGE3_C1_PHASEA_STEPS"]),
            c1_phase_b_steps=int(state["STAGE3_C1_PHASEB_STEPS"]),
            c1_phase_b_top_n=int(state["STAGE3_C1_PHASEB_TOP_N"]),
            c1_gate_delta=float(state["STAGE3_C1_PHASEB_GATE_DELTA_FLOOR"]),
            c1_gate_end_gain=float(state["STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR"]),
            period_init_mult={
                str(k): float(v) for k, v in state["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"].items()
            },
            period_step_mult={
                str(k): float(v) for k, v in state["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"].items()
            },
            period_restart_bonus={
                str(k): int(v) for k, v in state["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"].items()
            },
            init_keys_cap=int(state["STAGE3_INIT_KEYS_CAP"]),
        ),
        logging_controls=dict(
            kaeding_progress_every_pct=int(state["KAEDING_PROGRESS_EVERY_PCT"]),
            kaeding_console_progress=int(1 if bool(state["KAEDING_CONSOLE_PROGRESS"]) else 0),
            tier_heartbeat_seconds=float(state["TIER_HEARTBEAT_SECONDS"]),
            stage3_heartbeat_seconds=float(state["STAGE3_HEARTBEAT_SECONDS"]),
            stage3_heartbeat_min_step=int(state["STAGE3_HEARTBEAT_MIN_STEP"]),
            stage3_heartbeat_min_elapsed_seconds=float(
                state["STAGE3_HEARTBEAT_MIN_ELAPSED_SECONDS"]
            ),
        ),
    )


def build_scoring_lock_payload(*, state: Mapping[str, Any]) -> Dict[str, Any]:
    scorer_impl = state["SCORER_IMPL"]
    scorer_stage2 = dict(state["SCORER_STAGE2"])
    return dict(
        scorer_impl=str(getattr(scorer_impl, "value", scorer_impl)),
        stage1_label=str(state["SCORER_STAGE1_LABEL"]),
        stage2_label=str(state["SCORER_STAGE2_LABEL"]),
        stage3_label=str(state["SCORER_STAGE3_LABEL"]),
        stage1=dict(state["SCORER_STAGE1"]),
        stage2=scorer_stage2,
        stage3=dict(state["SCORER_FULL"]),
        stage2_pass1_primary={
            str(k): float(v) for k, v in state["STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS"].items()
        },
        stage2_pass1_fallback={
            str(k): float(v) for k, v in state["STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS"].items()
        },
        oracle_assist_selection=bool(state["ORACLE_ASSIST_SELECTION"]),
        require_no_ecdf_for_avg_fulltext=bool(state["REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT"]),
        stage3_search_contract=dict(
            objective=(
                str(scorer_stage2.get("objective", "avg.logp.win20"))
                if str(scorer_stage2.get("objective", "avg.logp.win20")).startswith("avg.")
                else "avg.logp.win20"
            ),
            avg_window_policy="full_text",
            char_weights={"4": 1.0},
            span_hamming_enabled=False,
            span_basin_judge_k=int(state["STAGE3_SPAN_BASIN_JUDGE_K"]),
            span_basin_judge_require_span_active=bool(
                state["STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE"]
            ),
            span_basin_judge_dedupe_by_end_hash=bool(
                state["STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH"]
            ),
            span_basin_judge_tie_eps=float(state["STAGE3_SPAN_BASIN_JUDGE_TIE_EPS"]),
            span_basin_judge_tie_max_seeds=int(
                state["STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS"]
            ),
            span_basin_judge_k_sweep=dict(
                enabled=bool(state["RUN_STAGE3_SPAN_BASIN_K_SWEEP"]),
                values=[int(v) for v in state["STAGE3_SPAN_BASIN_K_SWEEP_VALUES"]],
            ),
        ),
        stage3_span_char_pct_min_override=(
            None
            if state["STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE"] is None
            else float(state["STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE"])
        ),
    )
