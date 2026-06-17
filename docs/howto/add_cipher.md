# How-To: Add a Cipher

> Tracks: **Hands-on** covers promoting a tutorial cipher into `src/rune_decrypter_prime/ciphers/`; **Expert** covers wiring tests, specs, and docs.

Audience: Expert contributors
Time: 20-40 minutes
Outcome: New cipher registered and tested
Prereqs: Python 3.11+, pytest, familiarity with `CipherSpec`/`KeySpec`

## Hands-on Checklist
- Finish the prototype in `tutorials/v1/dev/<name>/` and verify it logs to `output/tutorials/...` (follow `guides/quickstart.md` if setup is missing).
- Keep encrypt/decrypt helpers deterministic (seeded RNG, enums for direction/device).
- Capture notes/screenshots you want in the eventual tutorial doc.

## Expert Implementation Steps
1. **Implement** `src/rune_decrypter_prime/ciphers/<name>.py` with encrypt/decrypt plus Key Normal Form helpers.
2. **Register** the cipher in `ciphers/registry.py` and expose a by-name wrapper via `api/by_name.py`.
3. **Add KeySpec support** if needed (permutation/matrix helpers under `api/specs.py` or `keyops/`).
4. **Write tests** in `tests/ciphers/test_<name>.py` covering:
   - encrypt -> decrypt -> encrypt round-trip
   - Key normal form validation/normalisation
   - scoring sanity on a short plaintext (seeded RNG)
5. **Document** the cipher in `docs/tutorials/<name>.md` and link it from `docs/guides/architecture.md` if it affects the pipeline.

## Verification
- `pytest tests/ciphers/test_<name>.py -q`
- If a tutorial exists, `pytest tests/tutorials -k <name> -q`
- Confirm new runs land in `output/tests/<timestamp>__tests__.../logs/app.jsonl` with the cipher name captured in telemetry (`telemetry.run.cipher`).

## Tips
- Use enums/KeySpec objects instead of raw strings to preserve determinism.
- If the cipher needs direction metadata, pass it through `RunAPI.run(..., encoding_dir=...)` and update `docs/guides/telemetry.md`.

