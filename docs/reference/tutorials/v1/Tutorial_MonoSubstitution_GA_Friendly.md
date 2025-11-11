# `tutorials/v1/Tutorial_MonoSubstitution_GA_Friendly.py`

> Purpose: reference companion to the mono GA tutorial.

> GA-focused mono substitution tutorial. Shows how to seed permutation keys from ranked frequency analysis and reach the ≥0.55 mono score target with deterministic settings.

## Highlights
- `_build_ciphertext` and `_invert_perm` generate reproducible ciphertext/cribs.
- Calls `seed_utils.make_seeds_from_freq` to create GA seed pools.
- Uses `SolverSpec.ga(pop_size=80, generations=120, seed=12345, progress_pct=1)` with `print_progress=True`.
- Writes outputs to `output/tutorials/<run>/...`.

## Run Command
```bash
python tutorials/v1/Tutorial_MonoSubstitution_GA.py --print-progress
```

## Expectations
- Mono score ≥0.55 (tested via `tests/tutorials/test_mono_substitution.py`).
- Telemetry includes permutation hashes (`tests/pipeline/test_permutation_tracking.py`).

## Related Docs
- `docs/tutorials/mono_ga.md` - Hands-on instructions.
- `docs/reference/utils/seed_utils.md` - details the helper functions used for GA seeds.

