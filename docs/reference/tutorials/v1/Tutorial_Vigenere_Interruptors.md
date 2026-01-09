# `tutorials/v1/Tutorial_Vigenere_Interruptors.py`

> Purpose: reference summary for the Vigenere interruptors tutorial (hands-on steps live in `docs/tutorials/Tutorial_Vigenere_Interruptors.md`).

Short, deterministic example that demonstrates interruptor handling: positions are removed before encryption, the core text is encrypted, and the original symbols are reinserted at the same indices.

## Workflow
- Builds a 20-rune plaintext and fixed interruptor positions (zero-based).
- Encrypts via `cipher_instance("vigenere", key_length=...)` with `interrupt_idx=...`.
- Verifies interruptor symbols are unchanged in the ciphertext.
- Runs the full pipeline with `interruptors_exact` and a known key (test_key).

## Run Command
```bash
python tutorials/v1/Tutorial_Vigenere_Interruptors.py
```

## Pass Criteria
- Interruptor symbols are preserved in ciphertext (same values at the same positions).
- Recovered plaintext matches the original reference.

## Related Docs
- `docs/tutorials/Tutorial_Vigenere_Interruptors.md`
- `docs/architecture/pipeline.md`

