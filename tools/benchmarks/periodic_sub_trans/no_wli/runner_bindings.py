from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping, MutableMapping

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.path_hash_utils import (
    canonical_json,
    git_commit,
    git_dirty,
    git_short,
    hash_payload,
    resolve_repo_path,
    sanitize_jsonable,
    scorer_cfg_for_output,
    scoring_meta_for_output,
    sha256_file,
    sha256_text,
    to_repo_rel_path,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_lock_payload import (
    build_non_scoring_lock_payload,
    build_scoring_lock_payload,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_oracle_audit import (
    append_iteration_audit_row,
    append_jsonl_row,
    oracle_score_for_stage,
)
from tools.benchmarks.periodic_sub_trans.no_wli.run_summary import (
    build_summary,
    derive_outcome_code,
    load_proven_solved_index,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_bridges import (
    append_stage3_topk_from_kaeding_bridge,
    append_stage3_topk_from_phasea_bridge,
    extract_kaeding_metrics_bridge,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runner_utils import (
    extract_top_keys,
    key_hash16,
    mutate_full_key,
    objective_text,
    preview_latin,
    print_stage_preview,
    weights_text,
)
from tools.benchmarks.periodic_sub_trans.no_wli.scoring_experiment_config import (
    apply_scoring_experiment_profile,
    build_stage3_experiment_cfg,
    stage3_char4_avg_fulltext_search_cfg,
    stage3_char4_pct_baseline_cfg,
)
from tools.benchmarks.periodic_sub_trans.no_wli.scoring_policy import (
    effective_stage3_impl,
    guard_no_ecdf_usage,
    is_avg_fulltext_scorer,
    objective_space_key,
    scorer_objective_summary,
    stage2_judge_pool_limit,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage2_promotion import (
    build_stage3_promoted_keys,
    ensure_best_entry_in_promoted,
    ensure_best_entry_in_ranked,
    entry_key_tuple,
    is_better_match_first,
    is_better_score_first,
    is_better_stage3_candidate_preserving_solve,
    is_solved_match,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage2_search import (
    tail_diversity_collapsed,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_band_policy import (
    select_stage3_band,
    select_stage3_default_band,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_progress import (
    as_nonneg_float,
    fmt_finite_float,
    scorer_span_counter_summary,
    solution_span_counter_summary,
    span_counter_delta,
    span_counter_summary_from_obj,
    stage3_progress_logging,
)


def install_runner_bindings(
    *,
    state: MutableMapping[str, Any],
    root: Path,
    base_module: Any,
    append_csv_row_common_fn: Callable[..., Any],
    write_csv_rows_common_fn: Callable[..., Any],
    scoring_config_cls: type,
    build_scorer_fn: Callable[..., Any],
) -> None:
    state["_repo_root"] = lambda: root
    state["_resolve_repo_path"] = lambda path_like: resolve_repo_path(path_like, root=root)
    state["_to_repo_rel_path"] = (
        lambda path_like, *, root: str(to_repo_rel_path(path_like, root=root))
    )
    state["_scorer_cfg_for_output"] = (
        lambda cfg, *, root: dict(scorer_cfg_for_output(dict(cfg), root=root))
    )
    state["_scoring_meta_for_output"] = (
        lambda meta, *, root: dict(scoring_meta_for_output(dict(meta), root=root))
    )
    state["_git_short"] = lambda: str(git_short(repo_root=root))
    state["_git_commit"] = lambda: str(git_commit(repo_root=root))
    state["_git_dirty"] = lambda: bool(git_dirty(repo_root=root))
    state["_sanitize_jsonable"] = sanitize_jsonable
    state["_canonical_json"] = lambda value: str(canonical_json(value))
    state["_sha256_text"] = lambda text: str(sha256_text(str(text)))
    state["_hash_payload"] = lambda payload: str(hash_payload(dict(payload)))
    state["_sha256_file"] = lambda path: str(sha256_file(path))

    state["_build_non_scoring_lock_payload"] = lambda: dict(
        build_non_scoring_lock_payload(
            state=state,
            build_run_mode_info_fn=state["_build_run_mode_info"],
        )
    )
    state["_build_scoring_lock_payload"] = lambda: dict(
        build_scoring_lock_payload(state=state)
    )
    state["_stage3_char4_pct_baseline_cfg"] = lambda: dict(
        stage3_char4_pct_baseline_cfg(scorer_impl=str(state["SCORER_IMPL"]))
    )
    state["_stage3_char4_avg_fulltext_search_cfg"] = lambda *, direction: dict(
        stage3_char4_avg_fulltext_search_cfg(
            scorer_stage2_cfg=dict(state["SCORER_STAGE2"]),
            scorer_stage3_impl_avg_fulltext=str(state["SCORER_STAGE3_IMPL_AVG_FULLTEXT"]),
            direction=direction,
        )
    )

    def _apply_scoring_experiment_profile_local() -> Dict[str, Any]:
        result = dict(
            apply_scoring_experiment_profile(
                scoring_experiment_profile=str(state["SCORING_EXPERIMENT_PROFILE"]),
                profile_name=str(state["PROFILE"]),
                scorer_stage2_cfg=dict(state["SCORER_STAGE2"]),
                scoring_experiment_span_assets_dir=state["SCORING_EXPERIMENT_SPAN_ASSETS_DIR"],
                scoring_experiment_span_coverage_min=float(
                    state["SCORING_EXPERIMENT_SPAN_COVERAGE_MIN"]
                ),
                scoring_experiment_span_quality_min=float(
                    state["SCORING_EXPERIMENT_SPAN_QUALITY_MIN"]
                ),
                scoring_experiment_c_char_pct_min=float(
                    state["SCORING_EXPERIMENT_C_CHAR_PCT_MIN"]
                ),
                scoring_experiment_enforce_locks=bool(
                    state["SCORING_EXPERIMENT_ENFORCE_LOCKS"]
                ),
                resolve_repo_path_fn=state["_resolve_repo_path"],
                hash_payload_fn=state["_hash_payload"],
                build_non_scoring_lock_payload_fn=state["_build_non_scoring_lock_payload"],
                build_scoring_lock_payload_fn=state["_build_scoring_lock_payload"],
                to_repo_rel_path_fn=lambda p, root: state["_to_repo_rel_path"](p, root=root),
                repo_root=state["_repo_root"](),
                stage3_char4_pct_baseline_cfg_fn=state["_stage3_char4_pct_baseline_cfg"],
            )
        )
        updated_profile = str(result.pop("updated_profile", state["PROFILE"]))
        updated_stage3_label = str(
            result.pop("updated_stage3_label", state["SCORER_STAGE3_LABEL"])
        )
        updated_stage3_cfg = dict(result.pop("updated_stage3_cfg", {}))
        if bool(result.get("enabled", False)):
            state["PROFILE"] = str(updated_profile)
            state["SCORER_STAGE3_LABEL"] = str(updated_stage3_label)
            if updated_stage3_cfg:
                state["SCORER_FULL"] = dict(updated_stage3_cfg)
        return result

    state["_apply_scoring_experiment_profile"] = _apply_scoring_experiment_profile_local
    state["_build_stage3_experiment_cfg"] = (
        lambda *,
        profile_name,
        direction,
        span_assets_dir,
        char_pct_min_override=None,
        disable_char_pct_gate=False: dict(
            build_stage3_experiment_cfg(
                profile_name=str(profile_name),
                direction=direction,
                span_assets_dir=span_assets_dir,
                char_pct_min_override=char_pct_min_override,
                disable_char_pct_gate=bool(disable_char_pct_gate),
                scoring_experiment_span_coverage_min=float(
                    state["SCORING_EXPERIMENT_SPAN_COVERAGE_MIN"]
                ),
                scoring_experiment_span_quality_min=float(
                    state["SCORING_EXPERIMENT_SPAN_QUALITY_MIN"]
                ),
                scoring_experiment_c_char_pct_min=float(
                    state["SCORING_EXPERIMENT_C_CHAR_PCT_MIN"]
                ),
                baseline_cfg=state["_stage3_char4_pct_baseline_cfg"](),
            )
        )
    )

    state["_extract_top_keys"] = lambda sol, *, limit: extract_top_keys(sol, limit=int(limit))
    state["_mutate_full_key"] = (
        lambda base_key, *, period, columns, seed, n: mutate_full_key(
            base_key,
            period=int(period),
            columns=int(columns),
            seed=int(seed),
            n=int(n),
            alphabet_size=int(state["ALPHABET_SIZE"]),
        )
    )
    state["_key_hash16"] = lambda key_vals: str(key_hash16(key_vals))
    state["_preview_latin"] = lambda pt, wli: str(
        preview_latin(
            pt,
            wli,
            safe_preview_latin_fn=base_module._safe_preview_latin,
            limit=int(state["PREVIEW_CHARS"]),
        )
    )
    state["_print_stage_preview"] = (
        lambda *, label, pt, wli, match_ratio=None: print_stage_preview(
            label=str(label),
            pt=pt,
            wli=wli,
            match_ratio=(float(match_ratio) if match_ratio is not None else None),
            preview_fn=state["_preview_latin"],
            log_prefix="[pipeline_no_wli]",
        )
    )
    state["_objective_text"] = lambda obj: str(objective_text(obj))
    state["_weights_text"] = lambda weights: str(weights_text(dict(weights)))
    state["_is_better_match_first"] = (
        lambda cand_match, cand_score, best_match, best_score: bool(
            is_better_match_first(
                cand_match=float(cand_match),
                cand_score=float(cand_score),
                best_match=float(best_match),
                best_score=float(best_score),
            )
        )
    )
    state["_is_better_score_first"] = (
        lambda cand_score, cand_match, best_score, best_match: bool(
            is_better_score_first(
                cand_score=float(cand_score),
                cand_match=float(cand_match),
                best_score=float(best_score),
                best_match=float(best_match),
            )
        )
    )
    state["_is_solved_match"] = lambda match_ratio: bool(
        is_solved_match(
            match_ratio=float(match_ratio),
            solve_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
        )
    )
    state["_is_better_stage3_candidate_preserving_solve"] = (
        lambda cand_score, cand_match, best_score, best_match, *, score_first: bool(
            is_better_stage3_candidate_preserving_solve(
                cand_score=float(cand_score),
                cand_match=float(cand_match),
                best_score=float(best_score),
                best_match=float(best_match),
                solve_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
                score_first=bool(score_first),
            )
        )
    )

    state["_as_nonneg_float"] = as_nonneg_float
    state["_span_counter_summary_from_obj"] = span_counter_summary_from_obj
    state["_span_counter_delta"] = span_counter_delta
    state["_solution_span_counter_summary"] = solution_span_counter_summary
    state["_scorer_span_counter_summary"] = scorer_span_counter_summary
    state["_fmt_finite_float"] = fmt_finite_float
    state["_stage3_progress_logging"] = stage3_progress_logging

    state["_scorer_objective_summary"] = lambda scorer_cfg: str(
        scorer_objective_summary(dict(scorer_cfg))
    )
    state["_is_avg_fulltext_scorer"] = lambda scorer_cfg: bool(
        is_avg_fulltext_scorer(dict(scorer_cfg))
    )
    state["_objective_space_key"] = lambda scorer_cfg: str(
        objective_space_key(dict(scorer_cfg))
    )
    state["_effective_stage3_impl"] = lambda scorer_cfg: str(
        effective_stage3_impl(
            dict(scorer_cfg),
            scorer_impl=str(state["SCORER_IMPL"]),
            scorer_stage3_impl_avg_fulltext=str(state["SCORER_STAGE3_IMPL_AVG_FULLTEXT"]),
        )
    )
    state["_stage2_judge_pool_limit"] = (
        lambda *,
        ranked_count,
        archive_keep,
        stage2_scorer_cfg=None,
        stage3_scorer_cfg: int(
            stage2_judge_pool_limit(
                ranked_count=int(ranked_count),
                archive_keep=int(archive_keep),
                stage2_scorer_cfg=(
                    dict(stage2_scorer_cfg) if stage2_scorer_cfg is not None else None
                ),
                stage3_scorer_cfg=dict(stage3_scorer_cfg),
                stage2_promote_by_stage3_judge=bool(state["STAGE2_PROMOTE_BY_STAGE3_JUDGE"]),
                stage2_entry_band_by_stage3_judge=bool(
                    state["STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE"]
                ),
                save_stage2_topk=int(state["SAVE_STAGE2_TOPK"]),
            )
        )
    )
    state["_guard_no_ecdf_usage"] = (
        lambda *, scorer_runtime, scorer_cfg, stage_label: guard_no_ecdf_usage(
            scorer_runtime=scorer_runtime,
            scorer_cfg=dict(scorer_cfg),
            stage_label=str(stage_label),
            require_no_ecdf_for_avg_fulltext=bool(state["REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT"]),
        )
    )
    state["_entry_key_tuple"] = lambda entry: tuple(entry_key_tuple(entry))
    state["_ensure_best_entry_in_ranked"] = (
        lambda *, ranked_entries, best_entry: ensure_best_entry_in_ranked(
            ranked_entries=ranked_entries,
            best_entry=best_entry,
        )
    )
    state["_ensure_best_entry_in_promoted"] = (
        lambda *, promoted_entries, best_entry, promote_top: ensure_best_entry_in_promoted(
            promoted_entries=promoted_entries,
            best_entry=best_entry,
            promote_top=promote_top,
        )
    )
    state["_build_stage3_promoted_keys"] = (
        lambda *, promoted_entries, best_key, key_len: build_stage3_promoted_keys(
            promoted_entries=promoted_entries,
            best_key=best_key,
            key_len=key_len,
        )
    )

    state["_tail_diversity_collapsed"] = (
        lambda tails, *, columns: tail_diversity_collapsed(
            tails=tails,
            columns=int(columns),
            min_first_symbols=int(state["STAGE2_PASS1_DIVERSITY_MIN_FIRST_SYMBOLS"]),
            min_hamming_factor=float(state["STAGE2_PASS1_DIVERSITY_MIN_HAMMING_FACTOR"]),
        )
    )
    state["_select_stage3_band"] = lambda gap_to_oracle: select_stage3_band(
        dynamic_bands=list(state["STAGE3_DYNAMIC_BANDS"]),
        gap_to_oracle=float(gap_to_oracle),
    )
    state["_select_stage3_default_band"] = lambda: select_stage3_default_band(
        dynamic_bands=list(state["STAGE3_DYNAMIC_BANDS"]),
        preferred_name="mid",
    )

    state["_oracle_score_for_stage"] = (
        lambda *, pt_idx, cipher_cfg, scorer_params: oracle_score_for_stage(
            pt_idx=pt_idx,
            cipher_cfg=cipher_cfg,
            scorer_params=scorer_params,
            scoring_config_cls=scoring_config_cls,
            build_scorer_fn=build_scorer_fn,
            scorer_objective_summary_fn=state["_scorer_objective_summary"],
        )
    )
    state["_write_csv_rows"] = lambda path, rows: write_csv_rows_common_fn(path, rows)
    state["_append_csv_row"] = lambda path, row: append_csv_row_common_fn(
        path, row, merge_fieldnames=True
    )
    state["_append_jsonl_row"] = lambda path, row: append_jsonl_row(
        path=path,
        row=row,
        sanitize_jsonable_fn=state["_sanitize_jsonable"],
    )
    state["_append_iteration_audit_row"] = (
        lambda *, audit_csv, audit_jsonl, prev_chain_hash, payload: append_iteration_audit_row(
            audit_csv=audit_csv,
            audit_jsonl=audit_jsonl,
            prev_chain_hash=str(prev_chain_hash),
            payload=payload,
            sanitize_jsonable_fn=state["_sanitize_jsonable"],
            canonical_json_fn=state["_canonical_json"],
            sha256_text_fn=state["_sha256_text"],
            append_csv_row_fn=state["_append_csv_row"],
            append_jsonl_row_fn=state["_append_jsonl_row"],
        )
    )

    state["_derive_outcome_code"] = derive_outcome_code
    state["_load_proven_solved_index"] = load_proven_solved_index
    state["_build_summary"] = lambda tiers, instances: build_summary(
        tiers=tiers,
        instances=instances,
        solve_match_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
        derive_outcome_code_fn=state["_derive_outcome_code"],
    )
    state["_extract_kaeding_metrics"] = (
        lambda kaeding_obj: extract_kaeding_metrics_bridge(kaeding_obj=kaeding_obj)
    )
    state["_append_stage3_topk_from_kaeding"] = (
        lambda *,
        payload,
        kaeding_obj,
        key_len,
        full_cipher,
        ciphertext,
        scorer_full_runtime,
        target_plaintext: append_stage3_topk_from_kaeding_bridge(
            state=state,
            payload=payload,
            kaeding_obj=kaeding_obj,
            key_len=int(key_len),
            full_cipher=full_cipher,
            ciphertext=np.asarray(ciphertext, dtype=np.uint8),
            scorer_full_runtime=scorer_full_runtime,
            target_plaintext=np.asarray(target_plaintext, dtype=np.uint8),
        )
    )
    state["_append_stage3_topk_from_phasea"] = (
        lambda *, payload, rows, key_len: append_stage3_topk_from_phasea_bridge(
            state=state,
            payload=payload,
            rows=rows,
            key_len=int(key_len),
        )
    )
