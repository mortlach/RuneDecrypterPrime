# Tutorial - Crib‑Drag API (Vigenère)

**Goal**  
Use a known plaintext snippet ("crib") to constrain the key search.

**Sketch**
```python
crib = "HELLO"
# Example approach: try alignments or fix partial key via KeySpec
result = RunAPI.run(
    ciphertext=CTXT,
    cipher_spec=CipherSpec(name="Vigenere", key_length=5),
    solver_spec=SolverSpec(name="SA", eval_budget=10_000),
    # key_spec=KeySpec(...),   # where supported to fix known positions
    seed=777,
)
print(result.plaintext[:120])
```

**Notes**
- Partial knowledge reduces search space significantly.
- Keep Pipeline direction consistent with the crib.
- Determinism helps compare strategies (with/without crib).

**See also**  
[Engine & API](../architecture/engine_api.md) · [Pipeline](../architecture/pipeline.md)

[← Vigenère + GA](Tutorial_Vigenere_GeneralMap.md) · [Next -> Tests](../tests/overview.md)
