# Pipeline

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Know how to set direction, permutation, device
Prereqs: Completed one tutorial

**Concept**  
Text-level transforms applied *outside* the cipher: direction and whole-text permutation. Always reversible; logged in telemetry.

**Fields**
- `text_encoding_direction`: `"ltr"` or `"rtl"` (aliases normalised to enum).
- `input_permutation`: telemetry summary of the full-text permutation (identity when none).

**Example**
```python
ciphertext_idx = [0, 1, 2, 3]  # toy indices
perm = list(reversed(range(len(ciphertext_idx))))
result = RunAPI.run(
    ciphertext=ciphertext_idx,
    cipher_spec=CipherSpec(name="Substitution"),
    solver_spec=SolverSpec(name="GA", eval_budget=20_000),
    text_encoding_direction="rtl",
    initial_text_permutation_indices=perm,
    seed=7,
)
# The engine undoes the permutation after decryption so plaintext is in natural order.
```

## Round-trip and scope notes
- **Round-trip:** pipeline changes are always reversed before the final plaintext is returned.  
  Example: `initial_text_permutation_indices=perm` -> decrypt -> undo perm -> readable plaintext.
- **Scope:** pipeline is cipher-agnostic; it does not implement cipher logic.
- **Interruptors:** model interruptors in the cipher or a higher layer; keep pipeline focused on direction and whole-text permutations.
  Interruptor indices are interpreted in pre-permutation coordinates and mapped internally when a permutation is provided.

**Telemetry**
A pipeline summary appears in `run_start` and `run_end` events.

**See also**  
[Engine & API](engine_api.md) · [Ciphers](ciphers.md) · [Telemetry](telemetry.md)

[<- Engine & API](engine_api.md) · [Next -> Ciphers](ciphers.md)

**Related tests**
- `tests/pipeline/test_permutation_tracking.py`
- `tests/telemetry/test_solver_pipeline_block.py`
