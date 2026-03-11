from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from rune_decrypter_prime.api import Direction
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher

from tools.benchmarks.periodic_sub_trans.common.runner_types import Tier
from tools.benchmarks.periodic_sub_trans.no_wli.iteration_runtime import (
    build_iteration_runtime as _build_iteration_runtime_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage1_substitution import (
    run_stage1_substitution as _run_stage1_substitution_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage2_search import (
    finalize_stage2_archive as _finalize_stage2_archive_external,
    run_stage2_search as _run_stage2_search_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_policy import (
    evaluate_stage3_entry_policy as _evaluate_stage3_entry_policy_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_seeding import (
    prepare_stage3_refine_inputs as _prepare_stage3_refine_inputs_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage_iteration_payload import (
    build_iteration_payloads as _build_iteration_payloads_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage_iteration_commit import (
    commit_iteration_outputs as _commit_iteration_outputs_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_runtime_calls import (
    Stage3RuntimeCallContext,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_topk import (
    append_stage3_topk_from_kaeding as _append_stage3_topk_from_kaeding_external,
    append_stage3_topk_from_phasea as _append_stage3_topk_from_phasea_external,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_metrics import (
    extract_kaeding_metrics as _extract_kaeding_metrics_external,
)


def build_iteration_runtime_bridge(
    *,
    state: Mapping[str, Any],
    tier: Tier,
    pt_idx: np.ndarray,
    key_seed: int,
    direction: Direction,
    span_assets_dir: Path,
    scoring_experiment_meta: Mapping[str, Any],
) -> Dict[str, Any]:
    return _build_iteration_runtime_external(
        tier_period=int(tier.period),
        tier_columns=int(tier.columns),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        key_seed=int(key_seed),
        alphabet_size=int(state["ALPHABET_SIZE"]),
        order=str(state["ORDER"]),
        direction=direction,
        scorer_stage1_base=dict(state["SCORER_STAGE1"]),
        scorer_stage2_base=dict(state["SCORER_STAGE2"]),
        scorer_impl=str(state["SCORER_IMPL"]),
        pipeline_run_mode=str(state["PIPELINE_RUN_MODE"]),
        stage3_two_phase_enabled=bool(state["STAGE3_TWO_PHASE_ENABLED"]),
        scoring_experiment_profile=str(
            scoring_experiment_meta.get("profile", "off") or "off"
        ),
        span_assets_dir=span_assets_dir,
        stage2_judge_policy_value=str(state["STAGE2_JUDGE_POLICY"]),
        stage2_exact_max_columns=int(state["STAGE2_EXACT_MAX_COLUMNS"]),
        stage2_exact_two_pass=bool(state["STAGE2_EXACT_TWO_PASS"]),
        stage2_pass1_primary_char_weights=dict(state["STAGE2_PASS1_PRIMARY_CHAR_WEIGHTS"]),
        stage2_pass1_fallback_char_weights=dict(state["STAGE2_PASS1_FALLBACK_CHAR_WEIGHTS"]),
        canonical_run_mode_fn=state["_canonical_run_mode"],
        is_adaptive_focus_mode_fn=state["_is_adaptive_focus_mode"],
        stage3_search_cfg_fn=state["_stage3_char4_avg_fulltext_search_cfg"],
        build_stage3_experiment_cfg_fn=state["_build_stage3_experiment_cfg"],
        build_word_ngram_report_cfg_fn=state["_build_word_ngram_report_cfg"],
        guard_no_ecdf_usage_fn=state["_guard_no_ecdf_usage"],
    )


def run_stage1_substitution_bridge(
    *,
    state: Mapping[str, Any],
    tier: Tier,
    text_id: int,
    key_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    true_sub: np.ndarray,
    sub_len: int,
    wli: Sequence[Sequence[int]],
    direction: Direction,
    scorer_stage1: Dict[str, Any],
    scorer_stage1_runtime: Any,
    sub_cipher: PeriodicSubstitutionCipher,
    stages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    base_mod = state["base"]
    return _run_stage1_substitution_external(
        tier_name=str(tier.name),
        tier_period=int(tier.period),
        tier_columns=int(tier.columns),
        text_id=int(text_id),
        key_seed=int(key_seed),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        true_sub=np.asarray(true_sub, dtype=np.int16),
        sub_len=int(sub_len),
        wli=wli,
        direction_value=str(direction.value),
        alphabet_size=int(state["ALPHABET_SIZE"]),
        scorer_stage1=dict(scorer_stage1),
        scorer_stage1_runtime=scorer_stage1_runtime,
        sub_cipher=sub_cipher,
        stages=stages,
        solver_stage1=dict(state["SOLVER_STAGE1"]),
        stage1_seed_restarts=int(state["STAGE1_SEED_RESTARTS"]),
        stage1_sub_candidates=int(state["STAGE1_SUB_CANDIDATES"]),
        stage1_sub_candidates_by_columns=dict(state["STAGE1_SUB_CANDIDATES_BY_COLUMNS"]),
        stage12_archive_keep=int(state["STAGE12_ARCHIVE_KEEP"]),
        stage12_scout_runs=int(state["STAGE12_SCOUT_RUNS"]),
        stage1_scout_min_steps=int(state["STAGE1_SCOUT_MIN_STEPS"]),
        stage1_scout_step_scale=float(state["STAGE1_SCOUT_STEP_SCALE"]),
        stage1_scout_min_restarts=int(state["STAGE1_SCOUT_MIN_RESTARTS"]),
        stage1_scout_restart_scale=float(state["STAGE1_SCOUT_RESTART_SCALE"]),
        stage1_seed_n_blocks=int(state["STAGE1_SEED_N_BLOCKS"]),
        stage1_seed_total=int(state["STAGE1_SEED_TOTAL"]),
        stage1_seed_swaps=int(state["STAGE1_SEED_SWAPS"]),
        batch_eval_chunk_size=int(state["BATCH_EVAL_CHUNK_SIZE"]),
        require_batch_scoring=bool(state["REQUIRE_BATCH_SCORING"]),
        stage1_scout_no_improve_delta=float(state["STAGE1_SCOUT_NO_IMPROVE_DELTA"]),
        stage1_scout_min_new_archive=int(state["STAGE1_SCOUT_MIN_NEW_ARCHIVE"]),
        stage1_scout_early_stop_min_scouts=int(state["STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS"]),
        stage1_scout_no_improve_patience=int(state["STAGE1_SCOUT_NO_IMPROVE_PATIENCE"]),
        extract_top_keys_fn=lambda sol, limit: state["_extract_top_keys"](sol, limit=int(limit)),
        key_hash_fn=lambda key_vals: state["_key_hash16"](key_vals),
        match_ratio_fn=lambda a, b: float(base_mod._match_ratio(list(a), list(b))),
        print_stage_preview_fn=state["_print_stage_preview"],
        log_prefix="[pipeline_no_wli]",
    )


def run_stage2_search_bridge(
    *,
    state: Mapping[str, Any],
    tier: Tier,
    text_id: int,
    key_seed: int,
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    wli: Sequence[Sequence[int]],
    sub_candidates: Sequence[Sequence[int]],
    direction: Direction,
    full_cipher: PeriodicColumnarCipher,
    sub_cipher: PeriodicSubstitutionCipher,
    scorer_stage2: Dict[str, Any],
    scorer_stage2_runtime: Any,
    scorer_stage2_pass1_primary_runtime: Any | None,
    scorer_stage2_pass1_fallback_runtime: Any | None,
    stages: List[Dict[str, Any]],
    oracle_assist_selection_effective: bool,
    mark_oracle_decision_use: Callable[[], None],
) -> Dict[str, Any]:
    base_mod = state["base"]
    return _run_stage2_search_external(
        tier_name=str(tier.name),
        tier_columns=int(tier.columns),
        text_id=int(text_id),
        key_seed=int(key_seed),
        ct_idx=np.asarray(ct_idx, dtype=np.uint8),
        pt_idx=np.asarray(pt_idx, dtype=np.uint8),
        wli=wli,
        sub_candidates=sub_candidates,
        direction_value=str(direction.value),
        full_cipher=full_cipher,
        sub_cipher=sub_cipher,
        scorer_stage2=dict(scorer_stage2),
        scorer_stage2_runtime=scorer_stage2_runtime,
        scorer_stage2_pass1_primary_runtime=scorer_stage2_pass1_primary_runtime,
        scorer_stage2_pass1_fallback_runtime=scorer_stage2_pass1_fallback_runtime,
        stages=stages,
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        mark_oracle_decision_use=mark_oracle_decision_use,
        preview_latin_fn=state["_preview_latin"],
        print_stage_preview_fn=state["_print_stage_preview"],
        match_ratio_fn=lambda a, b: float(base_mod._match_ratio(list(a), list(b))),
        is_better_score_first_fn=lambda cand_score, cand_match, best_score, best_match: state[
            "_is_better_score_first"
        ](
            cand_score=float(cand_score),
            cand_match=float(cand_match),
            best_score=float(best_score),
            best_match=float(best_match),
        ),
        scan_mode_active_stage2=bool(state["_mode_stage3_can_skip"](state["PIPELINE_RUN_MODE"])),
        cfg=dict(
            stage12_archive_keep=int(state["STAGE12_ARCHIVE_KEEP"]),
            stage12_promote_top=int(state["STAGE12_PROMOTE_TOP"]),
            scan_stage2_continue_to_gate=bool(state["SCAN_STAGE2_CONTINUE_TO_GATE"]),
            scan_stage3_gate_low_match=float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
            scan_stage2_continue_cap_seconds=float(state["SCAN_STAGE2_CONTINUE_CAP_SECONDS"]),
            stage2_exact_sub_candidates=int(state["STAGE2_EXACT_SUB_CANDIDATES"]),
            stage2_exact_sub_candidates_by_columns=dict(state["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"]),
            stage2_exact_pass1_top_tails=int(state["STAGE2_EXACT_PASS1_TOP_TAILS"]),
            stage2_exact_pass1_top_tails_by_columns=dict(state["STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS"]),
            stage2_hybrid_sub_candidates=int(state["STAGE2_HYBRID_SUB_CANDIDATES"]),
            stage2_hybrid_sub_candidates_by_columns=dict(state["STAGE2_HYBRID_SUB_CANDIDATES_BY_COLUMNS"]),
            batch_eval_chunk_size=int(state["BATCH_EVAL_CHUNK_SIZE"]),
            require_batch_scoring=bool(state["REQUIRE_BATCH_SCORING"]),
            stage2_exact_two_pass=bool(state["STAGE2_EXACT_TWO_PASS"]),
            stage2_exact_early_solve_break=bool(state["STAGE2_EXACT_EARLY_SOLVE_BREAK"]),
            stage2_pass1_diversity_min_first_symbols=int(state["STAGE2_PASS1_DIVERSITY_MIN_FIRST_SYMBOLS"]),
            stage2_pass1_diversity_min_hamming_factor=float(state["STAGE2_PASS1_DIVERSITY_MIN_HAMMING_FACTOR"]),
            stage2_exact_max_columns=int(state["STAGE2_EXACT_MAX_COLUMNS"]),
            solve_match_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
            solver_stage2=dict(state["SOLVER_STAGE2"]),
        ),
        log_prefix="[pipeline_no_wli]",
    )


def finalize_stage2_archive_bridge(
    *,
    state: Mapping[str, Any],
    tier: Tier,
    text_id: int,
    key_seed: int,
    stage2_archive: Dict[Tuple[int, ...], Dict[str, Any]],
    stage2_archive_keep: int,
    stage2_promote_top: int,
    best2_key: List[int] | None,
    best2_pt: List[int] | None,
    best2_preview: str,
    best2_score: float,
    best2_match: float,
    scorer_stage2: Dict[str, Any],
    scorer_stage2_judge_cfg: Dict[str, Any],
    scorer_stage2_judge_runtime: Any,
    scorer_full_runtime: Any,
    oracle_assist_selection_effective: bool,
    mark_oracle_decision_use: Callable[[], None],
) -> Dict[str, Any]:
    return _finalize_stage2_archive_external(
        tier_name=str(tier.name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        stage2_archive=stage2_archive,
        stage2_archive_keep=int(stage2_archive_keep),
        stage2_promote_top=int(stage2_promote_top),
        best2_key=best2_key,
        best2_pt=best2_pt,
        best2_preview=str(best2_preview),
        best2_score=float(best2_score),
        best2_match=float(best2_match),
        scorer_stage2=dict(scorer_stage2),
        scorer_stage2_judge_cfg=dict(scorer_stage2_judge_cfg),
        scorer_stage2_judge_runtime=scorer_stage2_judge_runtime,
        scorer_full_runtime=scorer_full_runtime,
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        mark_oracle_decision_use=mark_oracle_decision_use,
        stage2_promote_by_stage3_judge=bool(state["STAGE2_PROMOTE_BY_STAGE3_JUDGE"]),
        save_stage2_topk=int(state["SAVE_STAGE2_TOPK"]),
        batch_eval_chunk_size=int(state["BATCH_EVAL_CHUNK_SIZE"]),
        require_batch_scoring=bool(state["REQUIRE_BATCH_SCORING"]),
        objective_space_key_fn=state["_objective_space_key"],
        stage2_judge_pool_limit_fn=state["_stage2_judge_pool_limit"],
        ensure_best_entry_in_ranked_fn=state["_ensure_best_entry_in_ranked"],
        ensure_best_entry_in_promoted_fn=state["_ensure_best_entry_in_promoted"],
        entry_key_tuple_fn=state["_entry_key_tuple"],
        log_prefix="[pipeline_no_wli]",
    )


def evaluate_stage3_entry_policy_bridge(
    *,
    state: Mapping[str, Any],
    tier: Tier,
    text_id: int,
    key_seed: int,
    best2_match: float,
    stage2_continue_to_gate: bool,
    stage2_continue_stop_reason: str,
    tier_elapsed_before_stage3: float,
    stages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return _evaluate_stage3_entry_policy_external(
        tier_name=str(tier.name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        best2_match=float(best2_match),
        solve_match_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
        scan_mode_active=bool(state["_mode_stage3_can_skip"](state["PIPELINE_RUN_MODE"])),
        scan_time_cap_seconds=float(state["SCAN_TIER_TIME_CAP_SECONDS"]),
        tier_elapsed_before_stage3=float(tier_elapsed_before_stage3),
        scan_stage3_gate_low_match=float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
        scan_stage3_gate_high_match=float(
            max(float(state["SCAN_STAGE3_GATE_LOW_MATCH"]), float(state["SCAN_STAGE3_GATE_HIGH_MATCH"]))
        ),
        stage2_continue_to_gate=bool(stage2_continue_to_gate),
        stage2_continue_stop_reason=str(stage2_continue_stop_reason),
        stages=stages,
        log_prefix="[pipeline_no_wli]",
    )


def prepare_stage3_refine_inputs_bridge(
    *,
    state: Mapping[str, Any],
    tier: Tier,
    key_len: int,
    key_seed: int,
    best2_key: Sequence[int],
    best2_match: float,
    stage2_promoted: Sequence[Dict[str, Any]],
    stage2_entry_score: float,
    stage2_entry_score_judge: float,
    scorer_stage2: Dict[str, Any],
    scorer_full: Dict[str, Any],
    oracle_s3: float,
    oracle_decision_paths_enabled: bool,
) -> Dict[str, Any]:
    return _prepare_stage3_refine_inputs_external(
        tier_period=int(tier.period),
        tier_columns=int(tier.columns),
        key_len=int(key_len),
        key_seed=int(key_seed),
        best2_key=best2_key,
        best2_match=float(best2_match),
        stage2_promoted=stage2_promoted,
        stage2_entry_score=float(stage2_entry_score),
        stage2_entry_score_judge=float(stage2_entry_score_judge),
        scorer_stage2=dict(scorer_stage2),
        scorer_full=dict(scorer_full),
        stage3_dynamic_bands=list(state["STAGE3_DYNAMIC_BANDS"]),
        oracle_s3=float(oracle_s3),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        stage2_entry_band_by_stage3_judge=bool(state["STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE"]),
        stage3_c1_focus_enabled_cfg=bool(state["STAGE3_C1_FOCUS_ENABLED"]),
        stage3_c1_init_keys=int(state["STAGE3_C1_INIT_KEYS"]),
        stage3_initial_keys=int(state["STAGE3_INITIAL_KEYS"]),
        stage3_initial_keys_by_columns=dict(state["STAGE3_INITIAL_KEYS_BY_COLUMNS"]),
        stage3_period_init_mult_by_period=dict(state["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"]),
        stage3_period_step_mult_by_period=dict(state["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"]),
        stage3_period_restart_bonus_by_period=dict(state["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"]),
        stage3_init_keys_cap=int(state["STAGE3_INIT_KEYS_CAP"]),
        stage3_phasea_cfg=dict(state["STAGE3_PHASEA_CFG"]),
        stage3_phaseb_cfg=dict(state["STAGE3_PHASEB_CFG"]),
        stage3_phaseb_top_n=int(state["STAGE3_PHASEB_TOP_N"]),
        stage3_phaseb_gate_delta_floor=float(state["STAGE3_PHASEB_GATE_DELTA_FLOOR"]),
        stage3_phaseb_gate_end_gain_floor=float(state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"]),
        stage3_c1_phasea_steps=int(state["STAGE3_C1_PHASEA_STEPS"]),
        stage3_c1_phaseb_steps=int(state["STAGE3_C1_PHASEB_STEPS"]),
        stage3_c1_phaseb_top_n=int(state["STAGE3_C1_PHASEB_TOP_N"]),
        stage3_c1_phaseb_gate_delta_floor=float(state["STAGE3_C1_PHASEB_GATE_DELTA_FLOOR"]),
        stage3_c1_phaseb_gate_end_gain_floor=float(state["STAGE3_C1_PHASEB_GATE_END_GAIN_FLOOR"]),
        solver_stage3_cfg=dict(state["SOLVER_STAGE3"]),
        build_stage3_promoted_keys_fn=lambda promoted_entries, best_key, key_len: state["_build_stage3_promoted_keys"](
            promoted_entries=promoted_entries,
            best_key=best_key,
            key_len=int(key_len),
        ),
        mutate_full_key_fn=lambda seed_key, period, columns, seed, n: state["_mutate_full_key"](
            seed_key,
            period=int(period),
            columns=int(columns),
            seed=int(seed),
            n=int(n),
        ),
        objective_space_key_fn=state["_objective_space_key"],
        resolve_stage3_gap_and_band_fn=state["_resolve_stage3_gap_and_band_external"],
    )


def build_iteration_payloads_bridge(
    *,
    state: Mapping[str, Any],
    tier: Tier,
    text_id: int,
    key_seed: int,
    off: int,
    offset_used: int,
    status: str,
    stop_reason: str,
    best_stage: str,
    best_match: float,
    sub_key_match: float,
    best2_match: float,
    best3_match: float,
    stage2_gap_to_oracle: float,
    stage3_band_name: str,
    stage3_basin_judge_span_calls_total: int,
    stage3_basin_judge_span_calls_active: int,
    stage3_basin_judge_span_calls_rejected_or_gated: int,
    stage3_basin_judge_span_seconds_total: float,
    stage3_basin_judge_unique_end_hash: int,
    oracle_mode: str,
    oracle_consulted_in_decisions: bool,
    dt_i: float,
    total_evals: int,
    preview_best: str,
    outcome_code: str,
    final_best_score: float,
    oracle_scores: Dict[str, float],
    score_minus_oracle: Dict[str, float],
    ct_idx: np.ndarray,
    pt_idx: np.ndarray,
    final_best_key_idx: List[int] | None,
    final_best_plaintext_idx: List[int] | None,
    stage2_topk_payload: List[Dict[str, Any]],
    stage2_topk_has_best_match: bool,
    stage2_diagnostics: Dict[str, Any],
    stage3_topk_payload: List[Dict[str, Any]],
    stage3_diagnostics: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    return _build_iteration_payloads_external(
        tier_name=str(tier.name),
        period=int(tier.period),
        columns=int(tier.columns),
        length=int(tier.length),
        text_id=int(text_id),
        key_seed=int(key_seed),
        offset_hint=int(off),
        offset_used=int(offset_used),
        status=str(status),
        stop_reason=str(stop_reason),
        solve_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
        best_stage=str(best_stage),
        best_match_ratio=float(best_match),
        stage1_sub_key_match=float(sub_key_match),
        stage2_match_ratio=float(best2_match if np.isfinite(best2_match) else np.nan),
        stage3_match_ratio=float(best3_match if np.isfinite(best3_match) else np.nan),
        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
        stage3_band=str(stage3_band_name),
        basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
        basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
        basin_judge_span_calls_rejected_or_gated=int(stage3_basin_judge_span_calls_rejected_or_gated),
        basin_judge_span_seconds_total=float(stage3_basin_judge_span_seconds_total),
        basin_judge_unique_end_hash=int(stage3_basin_judge_unique_end_hash),
        oracle_mode=str(oracle_mode),
        oracle_consulted_in_decisions=bool(oracle_consulted_in_decisions),
        total_seconds=round(float(dt_i), 3),
        total_evals=int(total_evals),
        preview_best_latin=str(preview_best),
        outcome_code=str(outcome_code),
        profile_id=str(state["PROFILE"]),
        mode=str(state["_canonical_run_mode"](state["PIPELINE_RUN_MODE"])),
        direction=str(state["ENCODING_DIR"]),
        order=str(state["ORDER"]),
        alphabet_size=int(state["ALPHABET_SIZE"]),
        best_score=float(final_best_score),
        oracle_scores=dict(oracle_scores),
        score_minus_oracle=dict(score_minus_oracle),
        ciphertext_idx=[int(x) for x in np.asarray(ct_idx, dtype=np.uint8).tolist()],
        target_plaintext_idx=[int(x) for x in np.asarray(pt_idx, dtype=np.uint8).tolist()],
        final_best_key_idx=(list(map(int, final_best_key_idx)) if final_best_key_idx is not None else []),
        final_best_plaintext_idx=(
            list(map(int, final_best_plaintext_idx)) if final_best_plaintext_idx is not None else []
        ),
        stage2_topk=stage2_topk_payload,
        stage2_topk_has_best_match=bool(stage2_topk_has_best_match),
        stage2_diagnostics=stage2_diagnostics,
        stage3_topk=(stage3_topk_payload if bool(state["SAVE_STAGE3_TOPK"]) else []),
        stage3_diagnostics=stage3_diagnostics,
    )


def commit_iteration_outputs_bridge(
    *,
    state: Mapping[str, Any],
    run_dir: Path,
    final_dir: Path,
    root: Path,
    hist_path: Path,
    tiers: Sequence[Tier],
    instances: List[Dict[str, Any]],
    stages: List[Dict[str, Any]],
    inst_row: Dict[str, Any],
    artifact_payload: Dict[str, Any],
    done: int,
    total: int,
    t0_all: float,
    last_hb: float,
    heartbeat_seconds: float,
    best_global: Dict[str, Any],
    history_rows_written: int,
    audit_rows_written: int,
    audit_enabled: bool,
    audit_csv: Path,
    audit_jsonl: Path,
    audit_prev_chain_hash: str,
) -> Dict[str, Any]:
    base_mod = state["base"]
    return _commit_iteration_outputs_external(
        run_dir=run_dir,
        final_dir=final_dir,
        root=root,
        hist_path=hist_path,
        tiers=tiers,
        instances=instances,
        stages=stages,
        inst_row=inst_row,
        artifact_payload=artifact_payload,
        done=int(done),
        total=int(total),
        t0_all=float(t0_all),
        last_hb=float(last_hb),
        heartbeat_seconds=float(heartbeat_seconds),
        best_global=dict(best_global),
        history_rows_written=int(history_rows_written),
        audit_rows_written=int(audit_rows_written),
        audit_enabled=bool(audit_enabled),
        audit_csv=audit_csv,
        audit_jsonl=audit_jsonl,
        audit_prev_chain_hash=str(audit_prev_chain_hash),
        write_json_fn=state["write_json"],
        build_summary_fn=state["_build_summary"],
        write_pipeline_snapshot_files_fn=state["write_pipeline_snapshot_files"],
        append_csv_row_fn=state["_append_csv_row"],
        append_iteration_audit_row_fn=state["_append_iteration_audit_row"],
        hash_payload_fn=state["_hash_payload"],
        sha256_file_fn=state["_sha256_file"],
        format_seconds_fn=lambda seconds: base_mod._format_seconds(float(seconds)),
    )


def extract_kaeding_metrics_bridge(*, kaeding_obj: Any) -> Dict[str, float]:
    return _extract_kaeding_metrics_external(kaeding_obj)


def append_stage3_topk_from_kaeding_bridge(
    *,
    state: Mapping[str, Any],
    payload: List[Dict[str, Any]],
    kaeding_obj: Any,
    key_len: int,
    full_cipher: PeriodicColumnarCipher,
    ciphertext: np.ndarray,
    scorer_full_runtime: Any,
    target_plaintext: np.ndarray,
) -> None:
    base_mod = state["base"]
    _append_stage3_topk_from_kaeding_external(
        payload=payload,
        kaeding_obj=kaeding_obj,
        save_enabled=bool(state["SAVE_STAGE3_TOPK"]),
        save_limit=int(state["SAVE_STAGE3_TOPK_LIMIT"]),
        key_len=int(key_len),
        full_cipher=full_cipher,
        ciphertext=np.asarray(ciphertext, dtype=np.uint8),
        scorer_full_runtime=scorer_full_runtime,
        batch_eval_chunk_size=int(state["BATCH_EVAL_CHUNK_SIZE"]),
        require_batch_scoring=bool(state["REQUIRE_BATCH_SCORING"]),
        match_ratio_fn=lambda a, b: float(base_mod._match_ratio(list(a), list(b))),
        target_plaintext=np.asarray(target_plaintext, dtype=np.uint8),
    )


def append_stage3_topk_from_phasea_bridge(
    *,
    state: Mapping[str, Any],
    payload: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    key_len: int,
) -> None:
    _append_stage3_topk_from_phasea_external(
        payload=payload,
        rows=rows,
        save_enabled=bool(state["SAVE_STAGE3_TOPK"]),
        save_limit=int(state["SAVE_STAGE3_TOPK_LIMIT"]),
        key_len=int(key_len),
    )


def build_stage3_runtime_call_context_bridge(
    *,
    state: Mapping[str, Any],
) -> Stage3RuntimeCallContext:
    base_mod = state["base"]
    return Stage3RuntimeCallContext(
        order=str(state["ORDER"]),
        alphabet_size=int(state["ALPHABET_SIZE"]),
        batch_eval_chunk_size=int(state["BATCH_EVAL_CHUNK_SIZE"]),
        require_batch_scoring=bool(state["REQUIRE_BATCH_SCORING"]),
        solve_match_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
        stage3_continue_after_solve=bool(state["STAGE3_CONTINUE_AFTER_SOLVE"]),
        stage3_heartbeat_seconds=float(state["STAGE3_HEARTBEAT_SECONDS"]),
        stage3_heartbeat_min_step=int(state["STAGE3_HEARTBEAT_MIN_STEP"]),
        stage3_heartbeat_min_elapsed_seconds=float(state["STAGE3_HEARTBEAT_MIN_ELAPSED_SECONDS"]),
        stage3_span_basin_judge_require_span_active=bool(
            state["STAGE3_SPAN_BASIN_JUDGE_REQUIRE_SPAN_ACTIVE"]
        ),
        stage3_span_basin_judge_dedupe_by_end_hash=bool(
            state["STAGE3_SPAN_BASIN_JUDGE_DEDUPE_BY_END_HASH"]
        ),
        stage3_span_basin_judge_tie_eps=float(state["STAGE3_SPAN_BASIN_JUDGE_TIE_EPS"]),
        stage3_span_basin_judge_tie_max_seeds=int(state["STAGE3_SPAN_BASIN_JUDGE_TIE_MAX_SEEDS"]),
        stage3_word_ngram_decision_influence=bool(
            state.get("WORD_NGRAM_REPORT_DECISION_INFLUENCE", False)
        ),
        extract_kaeding_metrics_fn=state["_extract_kaeding_metrics"],
        solution_span_counter_summary_fn=state["_solution_span_counter_summary"],
        stage3_progress_logging_fn=state["_stage3_progress_logging"],
        match_ratio_fn=lambda a, b: float(base_mod._match_ratio(list(a), list(b))),
        key_hash_fn=state["_key_hash16"],
        append_stage3_topk_from_phasea_fn=state["_append_stage3_topk_from_phasea"],
        append_stage3_topk_from_kaeding_fn=state["_append_stage3_topk_from_kaeding"],
        is_better_stage3_candidate_preserving_solve_fn=state[
            "_is_better_stage3_candidate_preserving_solve"
        ],
        scorer_span_counter_summary_fn=state["_scorer_span_counter_summary"],
        span_counter_delta_fn=state["_span_counter_delta"],
        fmt_finite_float_fn=state["_fmt_finite_float"],
        log_prefix="[pipeline_no_wli]",
    )
