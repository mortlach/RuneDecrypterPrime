# Data & Scoring (WLI)

**Concept**  
Scorers consume plaintext rune indices and optional WLI pairs. WLI is a per-rune `(pos_in_word, word_len)` list used for word-boundary features; spaces are **not** part of rune indices. WLI values must be `<= 63` (LMPrime 6-bit encoding). When WLI is present, word boundaries are fixed by that list; when WLI is absent, there is no word-boundary contract.

## Behaviour
- English-tuned models for the 29-rune alphabet.  
- CPU-first; Torch backend (if installed) is kept on CPU for parity.  
- Deterministic across machines with fixed seed and inputs.

**Example (shape)**
```python
res = RunAPI.run(
    ciphertext="...",
    cipher_spec=CipherSpec(name="Vigenere", key_length=5),
    solver_spec=SolverSpec(name="GA", eval_budget=40_000),
    seed=33,
)
print(res.score)  # primary fitness; WLI (if provided) is metadata for scoring
```

## Appendix: Faster scorers (optional)
If you provide a faster backend (compiled extension or Torch kernels), keep these rules:

- Parity: scores must match the CPU reference path for the same inputs.  
- Determinism: keep Torch on CPU and seed via the engine's injected RNG.  
- Deployment: provide IDE-friendly setup steps in a local README under `tools/`.

**See also**  
[Telemetry](telemetry.md) · [Optimisers](optimisers.md)

[<- Telemetry](telemetry.md) · [Next -> Tutorials](../tutorials/index.md)
