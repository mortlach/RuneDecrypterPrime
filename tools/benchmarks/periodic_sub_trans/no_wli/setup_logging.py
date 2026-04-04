from __future__ import annotations

import json
from typing import Sequence


def emit_setup_logging(
    *,
    profile: str,
    mode_canonical: str,
    mode_raw: str,
    mode_intent: str,
    stage3_can_skip: bool,
    direction_value: str,
    order: str,
    alphabet_size: int,
    oracle_mode: str,
    oracle_assist_selection_requested: bool,
    oracle_assist_selection_effective: bool,
    autoskip_effective: bool,
    autoskip_requested: bool,
    force_rerun_proven: bool,
    autoskip_min_match: float,
    proven_known: int,
    hist_rel_path: str,
    profile_id: str,
    profile_previous_default: str,
    scorer_impl_stage12: str,
    scorer_impl_stage3: str,
    scorer_stage1_label: str,
    scorer_stage2_label: str,
    scorer_stage3_label: str,
    scorer_stage1_summary: str,
    scorer_stage2_summary: str,
    scorer_stage3_summary: str,
    require_no_ecdf_for_avg_fulltext: bool,
    stage3_search_summary: str,
    stage3_judge_summary: str,
    stage3_basin_judge_k: int,
    scoring_experiment_profile: str,
    scoring_experiment_enabled: bool,
    scoring_experiment_desc: str,
    phase_experiments_enabled: bool,
    phase_experiments_phaseA: str,
    phase_experiments_phaseB: str,
    phase_experiments_phaseB_char_gate_policy: str,
    non_scoring_lock_hash: str,
    scoring_lock_hash: str,
    run_config_hash: str,
    stage1_seed_restarts: int,
    stage1_seed_n_blocks: int,
    stage1_seed_total: int,
    stage1_seed_swaps: int,
    stage12_scout_runs: int,
    stage12_archive_keep: int,
    stage12_promote_top: int,
    stage1_scout_step_scale: float,
    stage1_scout_restart_scale: float,
    stage1_scout_min_steps: int,
    stage1_scout_min_restarts: int,
    stage1_scout_no_improve_delta: float,
    stage1_scout_no_improve_patience: int,
    stage1_scout_min_new_archive: int,
    stage1_scout_early_stop_min_scouts: int,
    stage1_sub_candidates: int,
    stage1_sub_candidates_by_columns: dict[int, int],
    stage3_initial_keys: int,
    stage3_initial_keys_by_columns: dict[int, int],
    stage3_period_init_mult_by_period: dict[int, float],
    stage3_period_step_mult_by_period: dict[int, float],
    stage3_period_restart_bonus_by_period: dict[int, int],
    stage3_init_keys_cap: int,
    stage2_exact_max_columns: int,
    stage2_exact_sub_candidates: int,
    stage2_exact_sub_candidates_by_columns: dict[int, int],
    stage2_pass1_primary_text: str,
    stage2_pass1_fallback_text: str,
    stage2_hybrid_sub_candidates: int,
    stage2_hybrid_sub_candidates_by_columns: dict[int, int],
    stage3_two_phase_enabled: bool,
    stage3_phasea_cfg: dict[str, object],
    stage3_phaseb_cfg: dict[str, object],
    stage3_phaseb_top_n: int,
    stage3_continue_after_solve: bool,
    stage3_phaseb_gate_delta_floor: float,
    stage3_phaseb_gate_end_gain_floor: float,
    stage3_phasec_enabled: bool = False,
    stage3_phasec_cfg: dict[str, object] | None = None,
    stage3_phasec_start_keys: int = 0,
    stage3_phasec_seed_offset: int = 0,
    stage3_phasec_word_ngram_tiebreak: bool = False,
    stage35_enabled: bool = False,
    stage35_baseline_selector: str = "legacy",
    stage35_cfg: dict[str, object] | None = None,
    stage3_c1_focus_enabled: bool,
    stage3_c1_init_keys: int,
    stage3_c1_phasea_steps: int,
    stage3_c1_phaseb_steps: int,
    stage3_c1_phaseb_top_n: int,
    stage3_c1_phaseb_gate_delta_floor: float,
    stage3_c1_phaseb_gate_end_gain_floor: float,
    scan_tier_time_cap_seconds: float,
    scan_stage2_continue_to_gate: bool,
    scan_stage2_continue_cap_seconds: float,
    scan_stage3_gate_low_match: float,
    scan_stage3_gate_high_match: float,
    tiers_count: int,
    text_offsets: Sequence[int],
    key_seeds: Sequence[int],
    reports_rel_path: str,
    audit_csv_rel_path: str,
    audit_jsonl_rel_path: str,
    log_prefix: str = "[pipeline_no_wli]",
) -> None:
    print(
        f"{log_prefix} setup: profile={profile} mode={mode_canonical} raw_mode={mode_raw} "
        f"mode_intent={mode_intent} stage3_can_skip={1 if bool(stage3_can_skip) else 0} "
        f"direction={direction_value} order={order} A={alphabet_size} "
        f"oracle_mode={oracle_mode} "
        f"oracle_assist_selection={1 if bool(oracle_assist_selection_requested) else 0} "
        f"oracle_assist_effective={1 if bool(oracle_assist_selection_effective) else 0}",
        flush=True,
    )
    print(
        f"{log_prefix} setup: autoskip_proven="
        f"{'on' if autoskip_effective else 'off'} "
        f"(requested={'on' if autoskip_requested else 'off'}, force_rerun={'on' if force_rerun_proven else 'off'}) "
        f"min_match={float(autoskip_min_match):.3f} "
        f"known={int(proven_known)} source={hist_rel_path}",
        flush=True,
    )
    print(
        f"{log_prefix} PROFILE_BANNER "
        f"NO_WLI_PIPELINE_PROFILE_ID={profile_id} "
        f"previous_default={profile_previous_default} "
        f"stage3={scorer_stage3_summary}",
        flush=True,
    )
    print(
        f"{log_prefix} setup: objective "
        f"impl(stage1/2)={scorer_impl_stage12} "
        f"impl(stage3)={scorer_impl_stage3} "
        f"stage1=({scorer_stage1_label},{scorer_stage1_summary},wli_off) "
        f"stage2=({scorer_stage2_label},{scorer_stage2_summary},wli_off) "
        f"stage3=({scorer_stage3_label},{scorer_stage3_summary},wli_off)",
        flush=True,
    )
    print(
        f"{log_prefix} setup: ecdf_guard="
        f"{'on' if bool(require_no_ecdf_for_avg_fulltext) else 'off'} "
        f"(enforce_no_ecdf_for_avg_fulltext={bool(require_no_ecdf_for_avg_fulltext)})",
        flush=True,
    )
    print(
        f"{log_prefix} setup: stage3-contract "
        f"search=({stage3_search_summary},ecdf_free=1,span=off) "
        f"judge=({stage3_judge_summary},span=calibrated) "
        f"basin_judge_k={int(stage3_basin_judge_k)}",
        flush=True,
    )
    print(
        f"{log_prefix} setup: scoring_experiment="
        f"{scoring_experiment_profile} "
        f"enabled={1 if bool(scoring_experiment_enabled) else 0} "
        f"desc=\"{scoring_experiment_desc}\"",
        flush=True,
    )
    print(
        f"{log_prefix} setup: stage3_phase_experiments "
        f"enabled={1 if bool(phase_experiments_enabled) else 0} "
        f"phaseA={phase_experiments_phaseA} "
        f"phaseB={phase_experiments_phaseB} "
        f"phaseB_char_gate_policy={phase_experiments_phaseB_char_gate_policy}",
        flush=True,
    )
    print(
        f"{log_prefix} setup: lock_hashes non_scoring={non_scoring_lock_hash} "
        f"scoring={scoring_lock_hash} run_config={run_config_hash}",
        flush=True,
    )
    print(
        f"{log_prefix} setup: search knobs "
        f"stage1_seed_restarts={int(stage1_seed_restarts)} "
        f"stage1_seed_plan=(blocks={int(stage1_seed_n_blocks)},total={int(stage1_seed_total)},swaps={int(stage1_seed_swaps)}) "
        f"stage12_scout_runs={int(stage12_scout_runs)} stage12_archive_keep={int(stage12_archive_keep)} "
        f"stage12_promote_top={int(stage12_promote_top)} "
        f"stage1_scout_scale=(steps={float(stage1_scout_step_scale):.2f},restarts={float(stage1_scout_restart_scale):.2f}) "
        f"stage1_scout_mins=(steps={int(stage1_scout_min_steps)},restarts={int(stage1_scout_min_restarts)}) "
        f"stage1_scout_plateau=(delta={float(stage1_scout_no_improve_delta):.1e},"
        f"patience={int(stage1_scout_no_improve_patience)},"
        f"min_new_archive={int(stage1_scout_min_new_archive)},"
        f"early_stop_min_scouts={int(stage1_scout_early_stop_min_scouts)}) "
        f"stage1_sub_candidates={int(stage1_sub_candidates)} "
        f"stage1_sub_by_c={json.dumps({str(k): int(v) for k, v in stage1_sub_candidates_by_columns.items()}, separators=(',', ':'))} "
        f"stage3_init_keys={int(stage3_initial_keys)} "
        f"stage3_init_by_c={json.dumps({str(k): int(v) for k, v in stage3_initial_keys_by_columns.items()}, separators=(',', ':'))} "
        f"stage3_init_mult_by_p={json.dumps({str(k): float(v) for k, v in stage3_period_init_mult_by_period.items()}, separators=(',', ':'))} "
        f"stage3_step_mult_by_p={json.dumps({str(k): float(v) for k, v in stage3_period_step_mult_by_period.items()}, separators=(',', ':'))} "
        f"stage3_restart_bonus_by_p={json.dumps({str(k): int(v) for k, v in stage3_period_restart_bonus_by_period.items()}, separators=(',', ':'))} "
        f"stage3_init_cap={int(stage3_init_keys_cap)} "
        f"stage2_exact_max_columns={int(stage2_exact_max_columns)} "
        f"stage2_exact_sub_candidates={int(stage2_exact_sub_candidates)} "
        f"stage2_exact_sub_by_c={json.dumps({str(k): int(v) for k, v in stage2_exact_sub_candidates_by_columns.items()}, separators=(',', ':'))} "
        f"stage2_pass1_primary={stage2_pass1_primary_text} "
        f"stage2_pass1_fallback={stage2_pass1_fallback_text} "
        f"stage2_hybrid_sub_candidates={int(stage2_hybrid_sub_candidates)} "
        f"stage2_hybrid_sub_by_c={json.dumps({str(k): int(v) for k, v in stage2_hybrid_sub_candidates_by_columns.items()}, separators=(',', ':'))}",
        flush=True,
    )
    print(
        f"{log_prefix} setup: stage3_two_phase="
        f"{'on' if bool(stage3_two_phase_enabled) else 'off'} "
        f"phaseA={json.dumps(dict(stage3_phasea_cfg), separators=(',', ':'))} "
        f"phaseB={json.dumps(dict(stage3_phaseb_cfg), separators=(',', ':'))} "
        f"phaseB_top_n={int(stage3_phaseb_top_n)} "
        f"continue_after_solve={1 if bool(stage3_continue_after_solve) else 0} "
        f"phaseB_gate=(delta={float(stage3_phaseb_gate_delta_floor):.4f},"
        f"end_gain={float(stage3_phaseb_gate_end_gain_floor):.4f}) "
        f"phaseC=(enabled={1 if bool(stage3_phasec_enabled) else 0},"
        f"start_keys={int(stage3_phasec_start_keys)},"
        f"seed_offset={int(stage3_phasec_seed_offset)},"
        f"word_ngram_tiebreak={1 if bool(stage3_phasec_word_ngram_tiebreak) else 0},"
        f"cfg={json.dumps(dict(stage3_phasec_cfg or {}), separators=(',', ':'))}) "
        f"stage35=(enabled={1 if bool(stage35_enabled) else 0},"
        f"baseline_selector={stage35_baseline_selector},"
        f"cfg={json.dumps(dict(stage35_cfg or {}), separators=(',', ':'))}) "
        f"c1_focus=(enabled={1 if bool(stage3_c1_focus_enabled) else 0},"
        f"init_keys={int(stage3_c1_init_keys)},"
        f"phaseA_steps={int(stage3_c1_phasea_steps)},"
        f"phaseB_steps={int(stage3_c1_phaseb_steps)},"
        f"phaseB_top_n={int(stage3_c1_phaseb_top_n)},"
        f"gate_delta={float(stage3_c1_phaseb_gate_delta_floor):.4f},"
        f"gate_end_gain={float(stage3_c1_phaseb_gate_end_gain_floor):.4f})",
        flush=True,
    )
    print(
        f"{log_prefix} setup: scan_controls "
        f"tier_time_cap_seconds={float(scan_tier_time_cap_seconds):.1f} "
        f"stage2_continue_to_gate={1 if bool(scan_stage2_continue_to_gate) else 0} "
        f"stage2_continue_cap_seconds={float(scan_stage2_continue_cap_seconds):.1f} "
        f"stage3_gate_low_match={float(scan_stage3_gate_low_match):.3f} "
        f"stage3_gate_high_match={float(scan_stage3_gate_high_match):.3f}",
        flush=True,
    )
    print(
        f"{log_prefix} setup: tiers={int(tiers_count)} text_offsets={list(text_offsets)} key_seeds={list(key_seeds)}",
        flush=True,
    )
    print(f"{log_prefix} reports: {reports_rel_path}", flush=True)
    print(
        f"{log_prefix} audit: csv={audit_csv_rel_path} jsonl={audit_jsonl_rel_path}",
        flush=True,
    )
