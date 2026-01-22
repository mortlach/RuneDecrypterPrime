# Ciphers

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Recognise cipher key models and where they plug in
Prereqs: Completed one tutorial

**Concept**  
Reversible mappings over the 29-rune alphabet. Each cipher declares a **Key Normal Form (KNF)** so keys are valid and comparable.

## Included (v1)
| Cipher | Key model | Notes |
|---|---|---|
| Substitution | Permutation(29) | Full monoalphabetic mapping |
| Columnar Transposition | Permutation(N) | Column order over N columns (N <= 255) |
| Vigenere | Vector(N) (0..28) | Repeating additive shifts |
| Generic-Map (affine-like) | Vector(2) (0..28) | Add/Sub/Mul/Div (mod 29); invalid ops rejected |
| Periodic Substitution | Matrix(periodic_structured) | p inverse tables of size A |
| Periodic Columnar | Matrix(periodic_structured) | p*A + W (W <= 255); order is configurable |

Note: Columnar keys currently use uint8 storage in the cipher core, so N/W must be <= 255.
To lift this, switch the columnar kernels to use KEY_DTYPE throughout.

**Examples (shape)**
```python
# Substitution (permutation key)
res = RunAPI.run(
    ciphertext="...",
    cipher_spec=CipherSpec(name="Substitution"),
    solver_spec=SolverSpec(name="GA", eval_budget=100_000),
    seed=11,
)

# Vigenere (vector key, length known)
res2 = RunAPI.run(
    ciphertext="...",
    cipher_spec=CipherSpec(name="Vigenere", key_length=5),
    solver_spec=SolverSpec(name="GA", eval_budget=50_000),
    seed=12,
)
```

## Key Normal Forms (KNF)
- **Permutation**: bijection over expected symbols (no duplicates or gaps).
- **Vector**: integers wrapped mod-29 per element; fixed length.

## Compatibility
- Periodic Substitution/Periodic Columnar  Matrix KeyOps (periodic_structured).
- Substitution/Columnar ↔ Permutation KeyOps.  
- Vigenere/Generic-Map ↔ Vector KeyOps.

**Related tests**
- `tests/ciphers/test_columnar_device_parity.py`
- `tests/ciphers/test_generic_map_cipher_keylength.py`
**See also**  
[KeyOps](keyops.md) · [Engine & API](engine_api.md)

[<- Pipeline](pipeline.md) · [Next -> KeyOps](keyops.md)

