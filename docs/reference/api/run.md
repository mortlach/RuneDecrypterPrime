# `api/run.py`

> Purpose: High-level entrypoint that normalises ciphertext, scorer configs, and solver specs before delegating to `api.pipeline.execute_run`. All tutorials and tests call `RunAPI.run` (or the module-level `run` alias) to ensure telemetry, RNG seeding, and logging flows through the same path.

## Public Surface
| Symbol | Description |
| --- | --- |
| `RunAPI.run(...)` | Classmethod that accepts ciphertext (string, indices, tuple `(indices, wli)`), `CipherSpec`, `KeySpec`, and `SolverSpec`, plus optional scorer/logging knobs. Normalises every argument and builds `SolverConfig` + `ScoringConfig` before invoking the pipeline. |
| `RunAPI.solve` | Backwards-compatible alias to `RunAPI.run`. |
| `run(*args, **kwargs)` / `solve(*args, **kwargs)` | Module-level helpers that forward to `RunAPI.run` for legacy imports (`from rune_decrypter_prime.api.run import run`). |

## Key Behaviours
- Normalises `device`, `encoding_dir`, ciphertext, and optional WLI data via `api.normalize`.
- Resolves scorer aliases (`resolve_scorer_aliases`), converts params into a `ScoringConfig`, and records the encoding direction for telemetry.
- Flattens `SolverSpec` into canonical solver params (name + seed) via `normalize_optimizer_spec`.
- Forwards all metadata (`initial_keys`, `initial_text_permutation_indices`, telemetry flag) to `api.pipeline.execute_run`, which emits telemetry + outputs under `output/<kind>/...`.

## Usage Example
```python
from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name

solution = RunAPI.run(
    text="ᛗᛖᛏᚻᚩᚾ",
    cipher=by_name.cipher("vigenere", key_len=6),
    key=KeySpec.repeat(len=6),
    solver=SolverSpec.ga(pop_size=64, generations=40, seed=1337, progress_pct=1),
    scorer="rune",
    scorer_params=dict(objective="pct.logp.win10"),
    telemetry_on=True,
    initial_text_permutation_indices=None,
)
print(solution.meta["telemetry"]["run"]["device"])
```

## Tests & Guardrails
- `tests/smoke/test_runapi_determinism.py` - ensures identical seeds/devices yield the same result and telemetry spans.
- `tests/ciphers/test_columnar_device_parity.py` - calls `RunAPI.run` on CPU vs CUDA to guarantee parity and proper telemetry.
- `tests/pipeline/test_permutation_tracking.py` - verifies `initial_text_permutation_indices` propagate through the pipeline block.

## See Also
- `docs/guides/architecture.md` - walkthrough of the RunAPI -> problem -> engine flow.
- `docs/reference/api/pipeline.md` - details the execution hand-off after `RunAPI` finishes normalising inputs.

