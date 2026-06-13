# API Layer - Deep Commentary

Audience: Expert
Time: 6-10 minutes
Outcome: Understand RunAPI inputs/outputs, specs, and where to plug new components
Prereqs: Read the Architecture overview and ran one tutorial

**Files**: `api/run.py`, `api/api.py`, `api/specs.py`, `api/wrappers/by_name.py`, `api/normalize.py`, `api/pipeline.py`

## Responsibilities
- **RunAPI.run** is the single public entry point for decryption runs.
- **specs.py** declares `CipherSpec`, `KeySpec`, `SolverSpec`, `ScoringConfig` (strict types; enums only).
- **by_name.py** exposes friendly constructors that return the strict specs (no magic strings beyond registered names).
- **normalize.py** converts user-friendly inputs (strings, indices) to canonical forms (indices, WLI pairs using `(pos_in_word, word_len)` when provided). It rejects out-of-range rune indices (must be 0..28) and disallows scorer params that belong in other configs (device/channel).
- **pipeline.py** defines direction and permutation handling used by the core runtime.

## Data flow (API -> Core)
1. Inputs normalised (indices, WLI, direction, permutation). `initial_text_permutation_indices` is validated to match ciphertext length.
2. A `ProblemSpec` is built and materialised into a `ProblemInstance`.
3. The `Engine` selects a solver family and executes with injected RNG.
4. Scores and telemetry flow back into a `Solution`.

## Contracts to preserve
- **Determinism**: seed comes from `SolverSpec` and drives all RNG streams.
- **No globals**: pass state via config/specs, not module-level singletons.
- **Type clarity**: prefer enums and dataclasses; avoid bare dicts in the public surface.

## Example (all enums, typed specs)
```python
from rune_decrypter_prime.api.wrappers.by_name import by_name
from rune_decrypter_prime.api.run import RunAPI
from rune_decrypter_prime.api.specs import KeySpec, SolverSpec, ScoringConfig
from rune_decrypter_prime.core.types import Direction, Device

SEED = 1337
cipher = by_name.cipher("vigenere", key_len=8)
key = KeySpec.repeat(len=8)
solver = SolverSpec.ga(pop_size=128, generations=120, seed=SEED)
scoring = ScoringConfig(model="unigram", direction=Direction.LTR)

sol = RunAPI.run(
    text=[19, 7, 11, 11, 14, 22, 14, 17],
    cipher=cipher,
    key=key,
    solver=solver,
    device=Device.CPU,
    scorer="rune",
    scorer_params={"encoding_dir": Direction.LTR, "objective": "pct.logp.win10"},
    telemetry_on=True,
    encoding_dir=Direction.LTR,
)
```

## FAQ (API layer)
- **Where does the seed live?** In the `SolverSpec`; the engine fans out named RNG streams.
- **How do I pass an initial permutation?** Use `initial_text_permutation_indices` on `RunAPI.run`. It must be a full-length permutation of the ciphertext indices.
- **Can I run without WLI?** Yes; pass `wli_data=[]` and set `scorer_params.use_word_breaks=False`. Otherwise, the API will infer WLI from spaces in strings or fall back to a single-word WLI for index inputs (WLI pos/len must be `<= 63`).
- **Where do I set device/channel?** `device` is a top-level RunAPI argument; channel weights live in `scorer_params` (`char_weights`, `wli_weights`). Passing `device` or `channel` inside `scorer_params` is rejected.


## Related tests
- `tests/smoke/test_runapi_determinism.py`
- `tests/api/test_normalize_direction.py`
- `tests/pipeline/test_permutation_tracking.py`
- `tests/telemetry/test_schema_contract.py`
