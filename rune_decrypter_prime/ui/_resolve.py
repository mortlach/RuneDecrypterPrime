# ---- rune_decrypter_prime/ui/_resolve.py
from __future__ import annotations
from typing import Any, Dict, Optional

def _pop_first(d: Dict[str, Any], *names: str, default: Any = None) -> Any:
    """Pop and return the first present/non-None alias from names; else default."""
    for n in names:
        if n in d and d[n] is not None:
            return d.pop(n)
    return default

def resolve_optimizer_aliases(name: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Canonicalise optimiser params so the core sees the correct keys.

    Conventions
    -----------
    - BEAM:  width/beam_width        -> beam_width
    - GA:    population/pop/pop_size -> pop_size
             generations/gens/(GA-only) iterations/iters -> generations
    - SA:    sa_iters / iterations / iters -> sa_iters

    For HYBRID:
      * GA MUST use 'generations' or 'gens' (NOT 'iters'/'iterations')
      * SA uses 'sa_iters' OR the friendly 'iters'/'iterations'
    """
    # todo this all needs cross-checking etc
    p = dict(params or {})
    out: Dict[str, Any] = {}
    n = (name or "").lower()

    if n == "beam":
        bw = _pop_first(p, "beam_width", "width", default=4)
        out["beam_width"] = int(bw)
        depth = _pop_first(p, "depth","steps")
        if depth is not None:
            out["depth"] = int(depth)
        for k in ("stop_score", "verbose", "test_key", "seed_keys", "initial_keys", "stop_score"):
            if k in p and p[k] is not None:
                out[k] = p.pop(k)
        return out

    if n == "ga":
        pop = _pop_first(p, "pop_size", "population", "pop", default=128)
        out["pop_size"] = int(pop)
        # In pure GA mode, 'iterations/iters' remain accepted for convenience
        gens = _pop_first(p, "steps","generations", "gens", "iterations", "iters", default=200)
        out["generations"] = int(gens)
        out.setdefault("mut_prob", out.get("mutation_rate", 0.3))  # default 0.3 if not provided
        for k in ("elite_frac", "cx_frac", "mut_prob", "local_improve_iters",
                  "stop_score", "verbose", "test_key", "seed_keys", "stop_score"):
            if k in p and p[k] is not None:
                out[k] = p.pop(k)
        return out

    if n == "sa":
        iters_ = _pop_first(p, "steps","sa_iters", "iterations", "iters", default=1000)
        out["sa_iters"] = int(iters_)
        for k in ("sa_init_temp", "sa_min_temp", "sa_cooling",
                  "stop_score", "verbose", "test_key", "seed_keys", "stop_score"):
            if k in p and p[k] is not None:
                out[k] = p.pop(k)
        return out

    if n == "hybrid":
        # Beam (optional warm start)
        use_beam = _pop_first(p, "use_beam")
        if use_beam is not None:
            out["use_beam"] = bool(use_beam)
        bw = _pop_first(p, "beam_width", "width")
        if bw is not None:
            out["beam_width"] = int(bw)
        bstop = _pop_first(p, "beam_stop_score", "stop_score")
        if bstop is not None:
            out["stop_score"] = bstop

        # GA (main exploration): ONLY 'generations'/'gens' here.
        pop = _pop_first(p, "pop_size", "population", "pop")
        if pop is not None:
            out["pop_size"] = int(pop)
        gens = _pop_first(p, "generations", "gens")
        if gens is not None:
            out["generations"] = int(gens)
        for k in ("elite_frac", "cx_frac", "mut_prob", "local_improve_iters"):
            if k in p and p[k] is not None:
                out[k] = p.pop(k)

        # SA (polish): 'sa_iters' OR friendly 'iterations'/'iters'
        iters_ = _pop_first(p, "sa_iters", "iterations", "iters")
        if iters_ is not None:
            out["sa_iters"] = int(iters_)
        for k in ("sa_init_temp", "sa_min_temp", "sa_cooling", "sa_perm_improve"):
            if k in p and p[k] is not None:
                out[k] = p.pop(k)

        # Common passthroughs
        for k in ("stop_score", "verbose", "test_key", "seed_keys", "initial_keys"):
            if k in p and p[k] is not None:
                out[k] = p.pop(k)
        return out

    # Unknown optimiser: pass-through unchanged (defensive)
    return p


def resolve_scorer_aliases(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Canonicalise scorer params so the core sees consistent keys.

    Aliases (accepted) -> Canonical (emitted)
    -----------------------------------------
    window, win                 -> win
    nchar, n_chars, nChars      -> n_char
    nwli, n_wlis, nWLI          -> n_wli
    objective                   -> objective (pass-through; no change)

    Notes
    -----
    * We do NOT invent defaults here. Missing keys stay missing.
    * Unknown keys are passed through unchanged (defensive, UI-flexible).
    """
    p: Dict[str, Any] = dict(params or {})
    out: Dict[str, Any] = {}

    # objective just passes through if provided
    if "objective" in p and p["objective"] is not None:
        out["objective"] = p.pop("objective")

    # window size
    if "win" in p and p["win"] is not None:
        out["win"] = p.pop("win")
    elif "window" in p and p["window"] is not None:
        out["win"] = p.pop("window")

    # n_char
    for alias in ("n_char", "nchar", "n_chars", "nChars"):
        if alias in p and p[alias] is not None:
            out["n_char"] = p.pop(alias)
            break

    val = None
    for alias in ("direction", "dir"):
        if alias in p and p[alias] is not None:
            val = str(p.pop(alias)).lower()
            break
    if val is not None:
        out["direction"] = val
        out["dir"] = val  # todo get rid safely

    # n_wli
    for alias in ("n_wli", "nwli", "n_wlis", "nWLI"):
        if alias in p and p[alias] is not None:
            out["n_wli"] = p.pop(alias)
            break

    # pass-through any other provided keys unchanged
    for k, v in p.items():
        if v is not None:
            out[k] = v

    return out
