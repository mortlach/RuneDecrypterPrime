# `api/pipeline.py`

> Purpose: turn the high-level objects assembled by `RunAPI` into the stage‑2 `ProblemInstance` that the solver engine consumes. This module applies known-key fast paths, builds `CipherConfig`, and finalises the outward-facing `Solution` with telemetry.

## Workflow (`execute_run`)
1. **Known-key fast path** - `maybe_known_key_fastpath` returns early when the cipher/key combo can be evaluated without invoking the solver (used in tutorials/tests to ensure deterministic shortcuts).
2. **CipherConfig build** - `build_cipher_config` (from `api.wrappers.registry`) materialises cipher/key metadata, captures permutation indices, device, encoding direction, and any seeded keys. (Permutation indices are normalised/validated by `RunAPI` before this point.)
3. **Problem materialisation** - creates `ProblemSpec` + `ProblemInstance`, wiring the scorer configuration and pipeline block (`telemetry.pipeline`).
4. **Engine execution** - converts the `SolverConfig` into `EngineConfig` (`normalize_optimizer_name`, log interval, seed keys), then calls `core.engine.solve`.
5. **Finalize solution** - `pipeline_helpers.finalize_solution` attaches telemetry, plaintext/ciphertext views, WLI, and the pipeline block so callers receive a consistent `Solution`.

## Usage
Normally you won't call `execute_run` directly; it is invoked by `RunAPI.run` once inputs are normalised. When writing new fast paths or instrumentation, import it like this:
```python
from rune_decrypter_prime.api.pipeline import execute_run

result = execute_run(
    ciphertext=ct_idx,
    wli=wli_spans,
    cipher=cipher_spec,
    key=key_spec,
    solver=solver_cfg,
    scoring=scoring_cfg,
    scorer_name="rune",
    logging=dict(log_interval=100),
    telemetry_on=True,
    device=Device.CPU,
    encoding_dir=Direction.LTR,
    initial_keys=None,
    initial_text_permutation_indices=None,
)
```

## Tests & Guardrails
- `tests/pipeline/test_permutation_tracking.py` - confirms permutations that enter `execute_run` are emitted back via telemetry.
- `tests/telemetry/test_solver_pipeline_block.py` - verifies pipeline blocks survive the engine hop.
- `tests/smoke/test_runapi_determinism.py` - exercises the entire pipeline end-to-end to ensure no hidden randomness sneaks in.

## Related Docs
- `docs/reference/api/pipeline_helpers.md` - explains how `finalize_solution` standardises outputs.
- `docs/reference/api/run.md` - details the normalisation work that happens before `execute_run`.
- `docs/guides/outputs.md` - shows where the pipeline writes telemetry/log artifacts.

