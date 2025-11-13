# `tutorials/v1/Tutorial_Autokey.py`

> Purpose: companion notes for the Autokey tutorial. Demonstrates both a “noise” run (no prior knowledge) and a crib-assisted run that seeds the solver with derived keys.

## Workflow
1. Encode a deterministic Alice-in-Wonderland excerpt (RTL) and encrypt it with a known Autokey seed.
2. Run `SolverSpec.ga(...)` once **without** a crib to show baseline behaviour.
3. Run a second solve **with** a short crib (e.g., “WHITE RABBIT”) that is transformed into candidate seeds and fed via `initial_keys`.
4. Each run calls `print_run_report(...)`, so regression tests assert `Recovered? : Yes` and `Match ratio ≥ 0.90`.

## Run Command
```bash
python tutorials/v1/Tutorial_Autokey.py
```

## Pass Criteria
- Both runs must achieve match ratio ≥ 0.90 and print `Recovered? : Yes`.
- Telemetry/logs live under `output/tutorials/autokey/...` and should respect the usual privacy toggles.

## Tips
- Adjust `seed_len` in the script or via `by_name.cipher("autokey", seed_len=...)` to explore longer seeds.
- To experiment with other cribs, change the `crib_text` constant; the helper recomputes seed candidates automatically.

## Related Docs
- `docs/reference/ciphers/autokey_cipher.md` – implementation details for the promoted cipher.
- `docs/tutorials/crib_drag.md` – broader discussion on crib-assisted search strategies.
