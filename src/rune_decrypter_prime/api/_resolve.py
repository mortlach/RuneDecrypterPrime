# ============================================================
# rune_decrypter_prime/patche_old_ui/_resolve.py
#   Strict validators for optimiser/scorer specs (no aliases)
# ============================================================
from __future__ import annotations
from typing import Dict, Any, Optional


# ----------------------------- optimiser ----------------------------- #

# Canonical parameter sets per optimiser (v1).
# NOTE: aliases are normalized in resolve_optimizer_aliases().
_CANON_OPTS: dict[str, set[str]] = {
    "beam": {
        "params", "beam_width", "rounds",
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
        "local_improve_on_accept", "sa_elitism", "sa_rescue_drop_abs", "sa_rescue_drop_ratio",
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

    # Shallow copy to avoid caller mutation; values pass through unchanged
    return dict(normalized)


# ------------------------------ scorer ------------------------------ #
_CANON_SCORER_KEYS = {"model_root","smoothing","alpha","oov_policy","include_char",
                      "use_word_breaks","n_char","n_wli","win","se_mode","objective",
                      "weights","maximize","encoding_dir","char_weights","wli_weights",
                      "impl","dtype",
                      "hamming_enabled","hamming_wordlist_dir","hamming_build_rtl",
                      "hamming_weight","hamming_weight_max","hamming_ramp_start_frac","hamming_ramp_end_frac",
                      "hamming_max_hd","hamming_length_weights",
                      "hamming_direction_mode"}

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
