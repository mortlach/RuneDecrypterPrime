# `tutorials/v1/Tutorial_Playfair29.py`

> Purpose: show how to solve the promoted Playfair-29 cipher with and without crib assistance.

## Workflow
1. Encode an Alice-in-Wonderland snippet (RTL) and strip spaces (Playfair operates without WLI).
2. Encrypt with a deterministic keyword-derived permutation using the production `playfair29` cipher.
3. Run a GA+SA hybrid search:
   - **Baseline run:** no crib, just the solver budget.
   - **Crib run:** feed a short reference phrase via `scorer_params["crib_runes"]` to accelerate convergence.
4. Use `print_run_report(...)` to emit consistent telemetry: both runs must print `Recovered? : Yes` and `Match ratio ≥ 0.90`.

## Run Command
```bash
python tutorials/v1/Tutorial_Playfair29.py
```

## Pass Criteria
- Both solver runs recover ≥90 % of the plaintext (match ratio) and report success.
- Outputs live under `output/tutorials/playfair29/...` with `force_no_wli=True` to avoid leaking spacing info.

## Related Docs
- `docs/reference/ciphers/playfair_cipher.md` – implementation details of the reduced-square cipher.
- `docs/tutorials/crib_drag.md` – broader crib strategies applicable to Playfair.
