# Pipeline & Enums

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Know how to set direction, permutation, and device
Prereqs: Completed one tutorial

> DRAFT - concise overview only. For the full contract and examples, see `guides/architecture.md` and `guides/telemetry.md`.

- Direction: `Direction.LTR` or `Direction.RTL` (in `core.types`).
- Permutation: `initial_text_permutation_indices` (list of ints) for pre-decrypt reordering.
- Device: `Device.CPU` on v1 surface.

## What this controls
- Direction flips text encoding order for scoring and for cipher wrapper logic.
- Permutation applies a whole-text reordering before decrypt (e.g. reverse).
- Device selects backends; v1 user surface prefers CPU. CUDA is tested for parity.

## How to use it (Hands-on)
- Tutorials pass `encoding_dir=Direction.LTR` and omit `wli_data` for ciphers without spaces.
- To apply a reverse permutation: `initial_text_permutation_indices=list(reversed(range(L)))`.

## Deep-dive examples
```python
from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.core.types import Direction

perm = list(reversed(range(200)))  # toy example
sol = RunAPI.run(
    text="??????",
    cipher=by_name.cipher("vigenere", key_len=6),
    key=KeySpec.repeat(len=6),
    solver=SolverSpec.ga(seed=1337, progress_pct=1),
    encoding_dir=Direction.LTR,
    initial_text_permutation_indices=perm,
    telemetry_on=True,
)
```

## Related tests
- `tests/pipeline/test_permutation_tracking.py` - pipeline block captures permutations/direction.
- `tests/telemetry/test_solver_pipeline_block.py` - solver spans include pipeline info.

