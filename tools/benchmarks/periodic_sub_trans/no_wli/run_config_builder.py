from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping, MutableMapping


def build_run_config(
    *,
    state: MutableMapping[str, Any],
    mode_canonical: str,
    mode_raw: str,
    mode_intent: str,
    stage3_can_skip: bool,
    scoring_experiment_meta: Mapping[str, Any],
    root: Path,
    direction: Any,
    autoskip_effective: bool,
    proven_known: int,
    oracle_mode: str,
    oracle_decision_paths_enabled: bool,
    oracle_assist_selection_effective: bool,
    is_adaptive_focus_mode_fn: Callable[[str | None], bool],
    scorer_cfg_for_output_fn: Callable[..., Dict[str, Any]],
    stage3_search_cfg_fn: Callable[..., Dict[str, Any]],
    scoring_meta_for_output_fn: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    return dict(
        profile=state["PROFILE"],
        mode=str(mode_canonical),
        mode_raw=str(mode_raw),
        mode_intent=str(mode_intent),
        stage3_can_skip=bool(stage3_can_skip),
        stage3_phase_experiments=dict(
            enabled=bool(is_adaptive_focus_mode_fn(mode_canonical)),
            phaseA=(
                "a_baseline"
                if is_adaptive_focus_mode_fn(mode_canonical)
                else str(scoring_experiment_meta.get("profile", "off"))
            ),
            phaseB=(
                "c_min_late"
                if is_adaptive_focus_mode_fn(mode_canonical)
                else str(scoring_experiment_meta.get("profile", "off"))
            ),
            phaseB_char_pct_min_policy=(
                "oracle_minus_0.10_clamp_0.30_0.45_not_applied_explicit_basin_judge"
                if is_adaptive_focus_mode_fn(mode_canonical)
                else "static_config"
            ),
        ),
        scoring_experiment=scoring_meta_for_output_fn(dict(scoring_experiment_meta), root=root),
        direction=direction.value,
        order=state["ORDER"],
        alphabet_size=int(state["ALPHABET_SIZE"]),
        threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
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
            stage3_min_stage2_match=float(state["SCAN_STAGE3_MIN_STAGE2_MATCH"]),
        ),
        autoskip_proven=bool(autoskip_effective),
        autoskip_proven_requested=bool(state["AUTOSKIP_PROVEN"]),
        force_rerun_proven=bool(state["FORCE_RERUN_PROVEN"]),
        autoskip_proven_min_match=float(state["AUTOSKIP_PROVEN_MIN_MATCH"]),
        autoskip_proven_known=int(proven_known),
        oracle_mode=str(oracle_mode),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_assist_selection_requested=bool(state["ORACLE_ASSIST_SELECTION"]),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        # Run config is startup-time intent/config, not post-run behavior.
        oracle_consulted_in_decisions=False,
        text_offsets=list(map(int, state["TEXT_OFFSETS"])),
        key_seeds=list(map(int, state["KEY_SEEDS"])),
        tiers=[
            dict(
                name=str(t.name),
                period=int(t.period),
                columns=int(t.columns),
                length=int(t.length),
            )
            for t in state["TIERS"]
        ],
        artifacts=dict(
            final_best=True,
            stage2_topk=int(state["SAVE_STAGE2_TOPK"]),
            stage3_topk_enabled=bool(state["SAVE_STAGE3_TOPK"]),
            stage3_topk=int(state["SAVE_STAGE3_TOPK_LIMIT"]),
        ),
        scorer_schedule=dict(
            stage1=str(state["SCORER_STAGE1_LABEL"]),
            stage2=str(state["SCORER_STAGE2_LABEL"]),
            stage3=str(state["SCORER_STAGE3_LABEL"]),
        ),
        stage1=dict(
            scorer=scorer_cfg_for_output_fn(dict(state["SCORER_STAGE1"]), root=root),
            solver=dict(state["SOLVER_STAGE1"]),
            seed_restarts=int(state["STAGE1_SEED_RESTARTS"]),
            seed_plan=dict(
                blocks=int(state["STAGE1_SEED_N_BLOCKS"]),
                total=int(state["STAGE1_SEED_TOTAL"]),
                swaps=int(state["STAGE1_SEED_SWAPS"]),
            ),
            scout=dict(
                runs=int(state["STAGE12_SCOUT_RUNS"]),
                archive_keep=int(state["STAGE12_ARCHIVE_KEEP"]),
                promote_top=int(state["STAGE12_PROMOTE_TOP"]),
                step_scale=float(state["STAGE1_SCOUT_STEP_SCALE"]),
                restart_scale=float(state["STAGE1_SCOUT_RESTART_SCALE"]),
                min_steps=int(state["STAGE1_SCOUT_MIN_STEPS"]),
                min_restarts=int(state["STAGE1_SCOUT_MIN_RESTARTS"]),
                no_improve_delta=float(state["STAGE1_SCOUT_NO_IMPROVE_DELTA"]),
                no_improve_patience=int(state["STAGE1_SCOUT_NO_IMPROVE_PATIENCE"]),
                min_new_archive=int(state["STAGE1_SCOUT_MIN_NEW_ARCHIVE"]),
                early_stop_min_scouts=int(state["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"]),
            ),
            sub_candidates=int(state["STAGE1_SUB_CANDIDATES"]),
            sub_candidates_by_columns={
                str(k): int(v) for k, v in state["STAGE1_SUB_CANDIDATES_BY_COLUMNS"].items()
            },
        ),
        stage2=dict(
            scorer=scorer_cfg_for_output_fn(dict(state["SCORER_STAGE2"]), root=root),
            pass1_primary_char_weights={
                str(k): float(v) for k, v in state["STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS"].items()
            },
            pass1_fallback_char_weights={
                str(k): float(v) for k, v in state["STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS"].items()
            },
            pass1_diversity_rule=dict(
                min_hamming_factor=float(state["STAGE2_PASS1_DIVERSITY_MIN_HAMMING_FACTOR"]),
                min_first_symbols=int(state["STAGE2_PASS1_DIVERSITY_MIN_FIRST_SYMBOLS"]),
            ),
            exact_max_columns=int(state["STAGE2_EXACT_MAX_COLUMNS"]),
            exact_sub_candidates=int(state["STAGE2_EXACT_SUB_CANDIDATES"]),
            exact_sub_by_columns={
                str(k): int(v)
                for k, v in state["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"].items()
            },
            exact_two_pass=bool(state["STAGE2_EXACT_TWO_PASS"]),
            pass1_top_tails=int(state["STAGE2_EXACT_PASS1_TOP_TAILS"]),
            pass1_top_by_columns={
                str(k): int(v)
                for k, v in state["STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS"].items()
            },
            early_solve_break=bool(state["STAGE2_EXACT_EARLY_SOLVE_BREAK"]),
            hybrid_solver=dict(state["SOLVER_STAGE2"]),
            hybrid_sub_candidates=int(state["STAGE2_HYBRID_SUB_CANDIDATES"]),
            hybrid_sub_by_columns={
                str(k): int(v)
                for k, v in state["STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS"].items()
            },
            judge_pool=dict(
                mode=(
                    "stage3_judge_enabled"
                    if bool(
                        state["STAGE2_PROMOTE_BY_STAGE3_JUDGE"]
                        or state["STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE"]
                    )
                    else "telemetry_only_topk"
                ),
                policy=str(state["STAGE2_JUDGE_POLICY"]),
                topk_default=int(state["SAVE_STAGE2_TOPK"]),
                promote_by_stage3_judge=bool(state["STAGE2_PROMOTE_BY_STAGE3_JUDGE"]),
                entry_band_by_stage3_judge=bool(state["STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE"]),
            ),
        ),
        stage3=dict(
            scorer=scorer_cfg_for_output_fn(dict(state["SCORER_FULL"]), root=root),
            search_scorer=dict(
                scorer_cfg_for_output_fn(
                    stage3_search_cfg_fn(direction=direction),
                    root=root,
                ),
                encoding_dir=str(direction.value),
            ),
            judge_scorer=scorer_cfg_for_output_fn(dict(state["SCORER_FULL"]), root=root),
            contract=(
                "Stage-3 Kaeding search optimizes avg/full_text char4 only (ECDF-free); "
                "span-hamming is used only in explicit basin-judge ranking of Phase-A endpoints "
                "before selecting Phase-B seeds."
            ),
            solver=dict(state["SOLVER_STAGE3"]),
            init_keys=int(state["STAGE3_INITIAL_KEYS"]),
            init_by_columns={
                str(k): int(v) for k, v in state["STAGE3_INITIAL_KEYS_BY_COLUMNS"].items()
            },
            span_basin_judge=dict(
                enabled=bool(True),
                k=int(state["STAGE3_SPAN_BASIN_JUDGE_K"]),
                require_span_active=bool(state["STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE"]),
                dedupe_by_end_hash=bool(state["STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH"]),
                tie_eps=float(state["STAGE3_SPAN_BASIN_JUDGE_TIE_EPS"]),
                tie_max_seeds=int(state["STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS"]),
                disable_char_pct_gate=bool(True),
                gate_fail_policy="score_floor",
            ),
            period_scaling=dict(
                init_mult_by_period={
                    str(k): float(v)
                    for k, v in state["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"].items()
                },
                step_mult_by_period={
                    str(k): float(v)
                    for k, v in state["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"].items()
                },
                restart_bonus_by_period={
                    str(k): int(v)
                    for k, v in state["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"].items()
                },
                init_keys_cap=int(state["STAGE3_INIT_KEYS_CAP"]),
            ),
            dynamic_bands=[dict(b) for b in state["STAGE3_DYNAMIC_BANDS"]],
            two_phase=dict(
                enabled=bool(state["STAGE3_TWO_PHASE_ENABLED"]),
                continue_after_solve=bool(state["STAGE3_CONTINUE_AFTER_SOLVE"]),
                phase_a=dict(state["STAGE3_PHASEA_CFG"]),
                phase_b=dict(state["STAGE3_PHASEB_CFG"]),
                phase_b_top_n=int(state["STAGE3_PHASEB_TOP_N"]),
                gate_delta_floor=float(state["STAGE3_PHASEB_GATE_DELTA_FLOOR"]),
                gate_end_gain_floor=float(state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"]),
            ),
            c1_focus=dict(
                enabled=bool(state["STAGE3_C1_FOCUS_ENABLED"]),
                init_keys=int(state["STAGE3_C1_INIT_KEYS"]),
                phase_a_steps=int(state["STAGE3_C1_PHASEA_STEPS"]),
                phase_b_steps=int(state["STAGE3_C1_PHASEB_STEPS"]),
                phase_b_top_n=int(state["STAGE3_C1_PHASEB_TOP_N"]),
                gate_delta_floor=float(state["STAGE3_C1_PHASEB_GATE_DELTA_FLOOR"]),
                gate_end_gain_floor=float(state["STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR"]),
            ),
        ),
    )
