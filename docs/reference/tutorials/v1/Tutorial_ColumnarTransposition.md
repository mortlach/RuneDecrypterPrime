# `tutorials/v1/Tutorial_ColumnarTransposition.py`

> Purpose: reference summary for the Hybrid columnar tutorial (Hands-on instructions live under `docs/tutorials`).

> Hybrid preset tutorial (Beam + SA polish) for columnar transposition ciphers. Targets ≥0.62 score / ≥98 % plaintext match when run with the default seed.

## Workflow
- Seeds ciphertext/key generation with `TUTORIAL_SEED = 2025`.
- Builds the columnar cipher via `by_name.cipher("columnar", key_len=9)` and `KeySpec.permutation`.
- Configures `SolverSpec.hybrid(...)` with Beam warm start and SA refinement.
- Prints progress buckets (1 % increments) and dumps logs to `output/tutorials/<run>/...`.

## Run Command
```bash
python tutorials/v1/Tutorial_ColumnarTransposition.py --print-progress
```

## Pass Criteria
- Score ≥0.62 and plaintext match ≥98 % (guarded by `tests/tutorials/test_hybrid_stage2_regression.py`).
- Telemetry must include the pipeline block and solver spans (`tests/telemetry/test_solver_pipeline_block.py`).

## Troubleshooting
- If scores dip below the target, re-check seeds/virtualenv; refer to `docs/appendices/high_school_troubleshooting.md`.

## Related Docs
- `docs/guides/outputs.md` (run directory layout).
- `docs/reference/api/wrappers/by_name.md` (explains the columnar wrapper).

