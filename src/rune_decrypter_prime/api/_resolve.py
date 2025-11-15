# ============================================================
# rune_decrypter_prime/patche_old_ui/_resolve.py
#   Strict validators for optimiser/scorer specs (no aliases)
# ============================================================
from __future__ import annotations
from typing import Dict, Any, Optional


# ----------------------------- optimiser ----------------------------- #

# Canonical parameter sets per optimiser (v1)
_CANON_OPTS: dict[str, set[str]] = {
    "beam": {
        "patience_delta", "plateau_rounds","max_children_per_parent","params","beam_width", "rounds",
        "patience_rounds", "patience_min_delta", "stop_score", "progress_pct", "print_progress",
        "progress_preview_chars",
        "verbose_console", "verbose", "initial_keys", "seed_keys", "test_key","expand_mode",
        "sample","sample_per_parent","top_parents_factor",'seed','log_interval'
    },
    "ga": {
        "params","pop_size", "generations", "elite_frac", "cx_frac", "mut_prob", "local_improve_iters",
        "patience_rounds", "patience_min_delta", "stop_score", "progress_pct", "print_progress",
        "progress_preview_chars",
        "verbose_console", "verbose","initial_keys", "seed_keys", "test_key",'seed','log_interval',
        'auto_cooling', 'gens', 'plateau_gens', 'pop', 'tournament_k'
    },
    "sa": {
        "sa_auto_cooling", "sa_iters", "tol","params","iters", "sa_init_temp", "sa_min_temp", "sa_cooling",
        "patience_rounds","patience_min_delta", "stop_score", "progress_pct", "print_progress",
        "progress_preview_chars",
        "verbose_console", "verbose", "initial_keys","seed_keys", "test_key",'seed','log_interval',
        'auto_cooling', 'local_improve_on_accept','sa_elitism', 'sa_rescue_drop_abs',
        'sa_rescue_drop_ratio', 'sa_reseed_interval'
    },
    "hybrid": {
        "ga", "sa", "beam_width", "generations", "pop_size", "iters", "phase_order",
        "patience_rounds", "patience_min_delta", "stop_score", "progress_pct", "print_progress",
        "progress_preview_chars",
        "verbose_console", "verbose","initial_keys", "seed_keys", "test_key","use_beam","rounds",
        "expand_mode","sample","sample_per_parent","top_parents_factor",'seed','log_interval'
    }
}

def resolve_optimizer_aliases(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """**Strict** canonicalisation: accepts only v1 keys; raises on unknowns.

    We keep the function name for compatibility with existing import sites,
    but it no longer expands legacy aliases. This aligns with the v1 goal
    to remove magic strings and synonyms.
    """
    keyset = _CANON_OPTS.get((name or "").lower())
    if keyset is None:
        raise ValueError(f"Unknown optimiser '{name}'. Allowed: {sorted(_CANON_OPTS)}")

    unknown = [k for k in params.keys() if k not in keyset]
    if unknown:
        allowed = ", ".join(sorted(keyset))
        bad = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown {name} parameter(s): {bad}. Allowed: {allowed}")

    # Shallow copy to avoid caller mutation; values pass through unchanged
    return dict(params)


# ------------------------------ scorer ------------------------------ #
_CANON_SCORER_KEYS = {"model_root","smoothing","alpha","oov_policy","include_char",
                      "use_word_breaks","n_char","n_wli","win","se_mode","objective",
                      "weights","maximize","encoding_dir","char_weights","wli_weights",
                      "impl","dtype"}

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
