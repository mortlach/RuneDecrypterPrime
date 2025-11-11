# `api/_resolve.py`

> Purpose: strict validation layer for solver/scorer parameters before they enter RunAPI. By constraining the allowed keys we eliminate magic strings and keep telemetry deterministic.

## Optimiser Validation
- `_CANON_OPTS` lists allowed parameter names per optimiser (`beam`, `ga`, `sa`, `hybrid`).
- `resolve_optimizer_aliases(name, params)` ensures the incoming dict uses only those keys; raises `ValueError` if unknown keys sneak in.

```python
from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases

params = resolve_optimizer_aliases("ga", {"pop_size": 64, "generations": 80, "progress_pct": 1})
# -> {"pop_size": 64, "generations": 80, "progress_pct": 1}

resolve_optimizer_aliases("ga", {"population": 64})
# ValueError: Unknown ga parameter(s): population. Allowed: ...
```

## Scorer Validation
- `_CANON_SCORER_KEYS` enumerates the only keys accepted by `resolve_scorer_aliases(params)`.
- The function returns a shallow copy of the dict (or `{}`) so callers can mutate safely after validation.
- No defaults are injected; RunAPI passes the validated dict to `normalize_scorer_params`.

```python
from rune_decrypter_prime.api._resolve import resolve_scorer_aliases

sc_params = resolve_scorer_aliases({"objective": "pct.logp.win10", "encoding_dir": "ltr"})
# Unknown keys raise immediately:
# resolve_scorer_aliases({"foo": 1}) -> ValueError
```

## Tests & Guardrails
- `tests/guardrails/test_normalize_scorer_and_optimizer_enums.py` - exercises the combination of `_resolve` + normalisation to ensure only canonical enums/keys survive.
- `tests/guardrails/test_core_no_direction_magic_tokens.py` - indirectly depends on `_resolve` since RunAPI refuses unrecognised direction/scorer keys that could reintroduce "fwd/rev" tokens.

## See Also
- `docs/reference/api/run.md` - shows how RunAPI calls `resolve_scorer_aliases` before building `ScoringConfig`.
- `docs/reference/api/pipeline.md` - `resolve_optimizer_aliases` ensures `EngineConfig` only receives known parameters.

