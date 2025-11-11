# `api/pipeline_helpers.py`

> Purpose: shared utilities that make the outward-facing `Solution` safe to consume (plaintext/ciphertext renderings, telemetry metadata) and normalise WLI spans before they reach the solver.

## Functions
| Function | Description |
| --- | --- |
| `finalize_solution(problem, res, **kwargs)` | Attaches telemetry (`telemetry.events.attach_telemetry_to_meta`, `telemetry.pipeline.finalize_run_meta`), injects the computed pipeline block, and calls `ensure_plaintext_rune` so every solution has rune/latin/plaintext views. |
| `ensure_plaintext_rune(res, *, ciphertext=None, wli=None, cipher=None, encoding_dir=Direction.RTL)` | Idempotently populates `plaintext_idx`, `plaintext_rune`, `plaintext_latin`, and ciphertext equivalents. Handles numpy arrays, rune strings, and ensures keys/WLIs are serialisable lists. |
| `coerce_wli_for_config(wli)` | Converts user-provided WLI spans into `(start, end)` pairs that `CipherConfig` accepts, handling span-style inputs and guarding against reversed ranges. |

## Usage Snippet
```python
from rune_decrypter_prime.api.pipeline_helpers import finalize_solution, coerce_wli_for_config

cipher_cfg = build_cipher_config(
    cipher=spec,
    key=key_spec,
    ciphertext=ct_idx,
    wli=coerce_wli_for_config(wli_spans),
    device=device,
    encoding_dir=encoding_dir,
    initial_keys=initial_keys,
    initial_text_permutation_indices=perm,
)

result = finalize_solution(
    problem=instance.problem,
    res=engine_result,
    ciphertext=ct_idx,
    wli=wli_spans,
    cipher=spec,
    encoding_dir=encoding_dir,
    cfg=SimpleNamespace(cipher=cipher_cfg, scorer_params=scoring_cfg, solver=solver_cfg),
    telemetry_on=True,
    pipeline_block=instance.pipeline_block,
)
print(result.plaintext_rune[:80], result.meta["telemetry"]["run"]["device"])
```

## Tests & Guardrails
- `tests/pipeline/test_permutation_tracking.py` - ensures pipeline blocks survive finalisation.
- `tests/telemetry/test_solver_pipeline_block.py` / `tests/telemetry/test_pipeline_block_itp.py` - rely on `finalize_solution` to attach telemetry metadata.
- `tests/patche_old_ui/test_normalize.py` and `tests/patche_old_ui/test_representation_conventions.py` indirectly validate `ensure_plaintext_rune` conversions (rune ↔ latin).

## See Also
- `docs/reference/api/pipeline.md` - shows where these helpers are called in the broader pipeline.
- `docs/guides/outputs.md` - demonstrates how the enriched solution fields are exposed in tutorials/logs.

