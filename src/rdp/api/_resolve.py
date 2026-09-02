# ============================================================
# rune_decrypter_prime/api/_resolve.py
#   Strict validators for optimiser/scorer specs (no aliases)
# ============================================================
from __future__ import annotations
from typing import Dict, Any, Optional

from rdp.core.config.validation import strict_positive_int


# ----------------------------- optimiser ----------------------------- #

# Canonical parameter sets per optimiser (v1).
# NOTE: aliases are normalized in resolve_optimizer_aliases().
_CANON_OPTS: dict[str, set[str]] = {
    "beam": {
        "params", "beam_width", "rounds", "restarts",
        "expand_mode", "sample_per_parent", "top_parents_factor",
        "max_children_per_parent",
        "plateau_rounds", "plateau_min_delta", "stop_score",
        "progress_pct", "print_progress", "progress_preview_chars",
        "verbose_console", "verbose", "initial_keys", "seed_keys", "test_key", "seed", "log_interval",
    },
    "ga": {
        "params", "pop_size", "generations", "elite_frac", "cx_frac", "mut_prob", "local_improve_iters",
        "tournament_k",
        "plateau_rounds", "plateau_min_delta", "stop_score",
        "progress_pct", "print_progress", "progress_preview_chars",
        "verbose_console", "verbose", "initial_keys", "seed_keys", "test_key", "seed", "log_interval",
    },
    "sa": {
        "params", "tol", "iters", "T0", "Tmin", "cool", "auto_cooling",
        "local_improve_on_accept", "sa_rescue_drop_abs", "sa_rescue_drop_ratio",
        "sa_reseed_interval",
        "plateau_rounds", "plateau_min_delta", "stop_score",
        "progress_pct", "print_progress", "progress_preview_chars",
        "verbose_console", "verbose", "initial_keys", "seed_keys", "test_key", "seed", "log_interval",
    },
    "hybrid": {
        "ga", "sa", "beam_width", "generations", "pop_size", "iters", "phase_order",
        "plateau_rounds", "plateau_min_delta", "stop_score", "progress_pct", "print_progress",
        "progress_preview_chars",
        "verbose_console", "verbose", "initial_keys", "seed_keys", "test_key", "use_beam", "rounds",
        "expand_mode", "sample_per_parent", "top_parents_factor", "seed", "log_interval",
    },
    "kaeding": {
        "params", "steps", "restarts", "inner_batch", "block_schedule",
        "slip_every", "slip_blocks", "col_every", "col_batch",
        "slip_policy", "stall_rounds", "stall_slip_limit", "slip_swaps", "stall_stop_on_limit",
        "slip_follow_steps", "use_raw_score", "seed_selection_metric", "seed_restarts",
        "raw_accept_min_delta", "pct_plateau_min_delta",
        "delta_window", "top_k",
        "plateau_rounds", "plateau_min_delta", "stop_score",
        "progress_pct", "print_progress", "progress_preview_chars",
        "verbose_console", "verbose", "initial_keys", "seed_keys", "test_key", "seed", "log_interval",
    },
}

_COMMON_ALIASES: dict[str, str] = {
    "patience_rounds": "plateau_rounds",
    "no_improve_rounds": "plateau_rounds",
    "patience_min_delta": "plateau_min_delta",
    "patience_delta": "plateau_min_delta",
}

_ALIAS_MAP: dict[str, dict[str, str]] = {
    "beam": {
        "width": "beam_width",
        "max_children_per_parent": "sample_per_parent",
    },
    "ga": {
        "gens": "generations",
        "iterations": "generations",
        "iters": "generations",
        "pop": "pop_size",
        "population": "pop_size",
        "plateau_gens": "plateau_rounds",
    },
    "sa": {
        "sa_iters": "iters",
        "iterations": "iters",
        "sa_init_temp": "T0",
        "sa_min_temp": "Tmin",
        "sa_cooling": "cool",
        "sa_auto_cooling": "auto_cooling",
    },
    "hybrid": {
        "gens": "generations",
        "iters": "iters",
        "iterations": "iters",
        "pop": "pop_size",
        "population": "pop_size",
        "plateau_gens": "plateau_rounds",
    },
    "kaeding": {
        "iters": "steps",
        "iterations": "steps",
    },
}

def _apply_aliases(params: Dict[str, Any], aliases: Dict[str, str]) -> Dict[str, Any]:
    out = dict(params)
    for alias, canonical in aliases.items():
        if alias in out:
            if canonical not in out:
                out[canonical] = out[alias]
            out.pop(alias)
    return out

def resolve_optimizer_aliases(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Strict canonicalisation: normalize legacy aliases to canonical keys and raise on unknowns."""
    name_key = (name or "").lower()
    keyset = _CANON_OPTS.get(name_key)
    if keyset is None:
        raise ValueError(f"Unknown optimiser '{name}'. Allowed: {sorted(_CANON_OPTS)}")

    normalized = _apply_aliases(params, _COMMON_ALIASES)
    normalized = _apply_aliases(normalized, _ALIAS_MAP.get(name_key, {}))

    unknown = [k for k in normalized.keys() if k not in keyset]
    if unknown:
        allowed = ", ".join(sorted(keyset))
        bad = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown {name} parameter(s): {bad}. Allowed: {allowed}")

    budget_fields = {
        "ga": ("generations",),
        "sa": ("iters",),
        "hybrid": ("generations", "iters"),
    }
    for field in budget_fields.get(name_key, ()):
        if field in normalized:
            normalized[field] = strict_positive_int(normalized[field], field)
    if name_key == "beam" and "restarts" in normalized:
        normalized["restarts"] = strict_positive_int(normalized["restarts"], "restarts")

    # Shallow copy to avoid caller mutation; values pass through unchanged
    return dict(normalized)


# ------------------------------ scorer ------------------------------ #
_CANON_SCORER_KEYS = {"model_root","smoothing","alpha","oov_policy","include_char",
                      "use_word_breaks","n_char","n_wli","win","se_mode","objective",
                      "weights","maximize","encoding_dir","char_weights","wli_weights",
                      "avg_window_policy",
                      "impl","dtype","compute_dtype","acc_dtype","hard_crib",
                      "stride","ecdf_clamp_min","ecdf_clamp_max","diagnostics_enabled",
                      "hamming_dictionary_policy","hamming_dictionary_policy_root",
                      "hamming_enabled","hamming_wordlist_dir","hamming_build_rtl",
                      "hamming_weight","hamming_weight_max","hamming_ramp_start_frac","hamming_ramp_end_frac",
                      "hamming_max_hd","hamming_length_weights",
                      "hamming_direction_mode",
                      "span_hamming_enabled","span_hamming_wordlist_dir","span_hamming_weight",
                      "span_hamming_len_min","span_hamming_len_max","span_hamming_max_hd",
                      "span_hamming_start_stride","span_hamming_max_windows_total",
                      "span_hamming_max_candidates_per_window","span_hamming_max_intervals_considered_per_start",
                      "span_hamming_min_quality_threshold","span_hamming_debug_return_intervals",
                      "span_hamming_require_selected",
                      "span_hamming_mode","span_hamming_assets_dir","span_hamming_bucket_policy",
                      "span_hamming_assets_dictionary_policy","span_hamming_allow_dictionary_policy_mismatch",
                      "span_hamming_ecdf_clamp_min","span_hamming_ecdf_clamp_max",
                      "span_hamming_combine_mode","span_hamming_weight_span","span_hamming_weight_char",
                      "span_hamming_coverage_min","span_hamming_quality_min",
                      "span_hamming_span_pct_min","span_hamming_char_pct_min",
                      "span_hamming_gate_fail_policy","span_hamming_gate_score_floor",
                      "span_hamming_lm_assets_json","span_hamming_lm_profile_source",
                      "span_hamming_lm_tail_start_index","span_hamming_lm_weight",
                      "word_ngram_judge_enabled","word_ngram_judge_sqlite_path",
                      "word_ngram_judge_alpha","word_ngram_judge_miss_logp",
                      "word_ngram_judge_min_positions","word_ngram_judge_prefix_total_thresholds"}

def resolve_scorer_aliases(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate scorer params to canonical v1 keys; raise on unknown.

    Keys pass through unchanged; we do **not** invent defaults here.
    """
    p: Dict[str, Any] = dict(params or {})
    unknown = [k for k in p if k not in _CANON_SCORER_KEYS]
    if unknown:
        allowed = ", ".join(sorted(_CANON_SCORER_KEYS))
        bad = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown scorer parameter(s): {bad}. Allowed: {allowed}")
    return p
