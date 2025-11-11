# `tutorials/v1/Tutorial_MonoSubstitution_HYBRID.py`

> Purpose: reference companion describing the mono hybrid tutorial and its success criteria.

> Hands-on hybrid preset for mono substitution. Demonstrates staged solving (Beam warm start -> GA -> SA polish) with the same deterministic seeds used in the GA/SA tutorials so learners can compare performance.

## What It Does
- Generates deterministic ciphertext via `_build_ciphertext` (English -> rune indices) and `_invert_perm`.
- Seeds permutation pools using `seed_utils.make_seeds_from_freq`.
- Runs `SolverSpec.hybrid` with tuned beam/GA/SA sub-phases to reach ≥0.62 score / ≥98 % match thresholds specified in the docs plan.

## Run Command
```bash
python tutorials/v1/Tutorial_MonoSubstitution_HYBRID.py --print-progress
```

Expect to see progress buckets for each phase, decrypted plaintext preview, recovered key, and a pointer to `output/tutorials/<run>/logs/app.jsonl`.

## Success Criteria & Tests
- `tests/tutorials/test_hybrid_stage2_regression.py` - enforces mono score/match thresholds for this tutorial.
- `tests/telemetry/test_solver_pipeline_block.py` - verifies the hybrid solver emits proper pipeline spans when the tutorial runs.

## Related Docs
- `docs/tutorials/mono_ga.md` - explains how Hands-on users should interpret the mono results (GA vs Hybrid).
- `docs/reference/utils/seed_utils.md` - details the helper functions shared across mono tutorials.

