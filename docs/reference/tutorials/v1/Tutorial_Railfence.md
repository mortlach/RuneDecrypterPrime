# `tutorials/v1/Tutorial_Railfence.py`

> Purpose: reference summary for the production railfence tutorial (Hands-on instructions live alongside the script).

The tutorial demonstrates the promoted railfence cipher, using a Rune-encoded Alice-in-Wonderland excerpt, stripped of word breaks, and a scalar key search over the number of rails. The default configuration targets a 3-rail fence and recovers both plaintext and rail count with a compact beam search.

## Workflow
- Encodes the plaintext with `Direction.RTL`, removes spaces, and encrypts with the helper `encrypt_railfence`.
- Builds the official wrapper via `by_name.cipher("railfence", min_rails=2, max_rails=6)` and a scalar key spec (`KeySpec.scalar(max_val=6)`).
- Runs `SolverSpec.beam(...)` (width 64, seed 4242) with `use_word_breaks=False`, since the ciphertext lacks WLI.
- Emits `print_run_report(...)` so regression harnesses can assert `Recovered? Yes`, match ratios, and telemetry metadata.

## Run Command
```bash
python tutorials/v1/Tutorial_Railfence.py
```

## Pass Criteria
- Beam search must reach ≥0.56 rune score and recover the plaintext snippet (guarded by `tests/tutorials/test_railfence_tutorial.py`).
- Telemetry/output live under `output/tutorials/...` and respect the privacy toggle (`force_no_wli=True` keeps META clean).

## Troubleshooting
- If scores stagnate, confirm you stripped spaces from the plaintext, kept `use_word_breaks=False`, and are running with Python 3.11 + the repo on `PYTHONPATH`.
- For longer ciphertexts, widen `beam_width` or extend `stop_score`; the cipher remains scalar so search cost stays low.

## Related Docs
- `docs/reference/ciphers/railfence_cipher.md` – explains the promoted cipher implementation, key model, and helper methods.
- `docs/howto/wrappers.md` – describes how to consume `by_name.cipher(...)` wrappers in your own scripts.
