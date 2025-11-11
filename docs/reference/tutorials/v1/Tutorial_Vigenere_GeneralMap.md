# `tutorials/v1/Tutorial_Vigenere_GeneralMap.py`

> Purpose: reference summary for the GA Vigenere tutorial (Hands-on steps live in `docs/tutorials/v1/Tutorial_Vigenere_GeneralMap.md`).

> Hands-on Vigenère GA tutorial. Demonstrates how to call `RunAPI.run` with a seeded GA preset, inspect telemetry, and reach the ≥0.55 mono score contract.

## What It Does
- Loads a seeded ciphertext/plaintext pair (`TUTORIAL_SEED = 12345`).
- Builds Vigenère specs via `by_name.cipher("vigenere", key_len=6)`.
- Runs GA with `pop_size=64`, `generations=80`, `progress_pct=1`, `print_progress=True`.
- Logs outputs under `output/tutorials/<timestamp>__tutorials__vigenere__<git>/`.

## Usage
```bash
python tutorials/v1/Tutorial_Vigenere_GeneralMap.py --print-progress
```

Expected console output:
- progress lines (`pct=.. best_score=..`)
- plaintext preview and recovered key
- pointer to `logs/app.jsonl`

## Success Criteria
- Mono score ≥0.55 on CPU (enforced by `tests/tutorials/test_ga_stage2_regression.py`).
- Telemetry includes the pipeline block and solver spans (checked by telemetry tests).

## Related Docs
- `docs/tutorials/v1/Tutorial_Vigenere_GeneralMap.md` (Hands-on guide).
- `docs/howto/deterministic_run.md` (explains the seeded GA workflow).

