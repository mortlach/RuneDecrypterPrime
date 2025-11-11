# Data & Scoring (WLI)

**Concept**  
Scorers evaluate plaintext candidates and return WLI pairs (list of numeric pairs). The first element ranks candidates; the second is auxiliary (e.g. a length or secondary metric).

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
print(res.score)  # primary fitness; raw WLI pairs appear in telemetry
```

## Appendix: Faster scorers (optional)
If you provide a faster backend (compiled extension or Torch kernels), keep these rules:

- Parity: scores must match the CPU reference path for the same inputs.  
- Determinism: keep Torch on CPU and seed via the engine's injected RNG.  
- Deployment: provide IDE-friendly setup steps in a local README under `tools/`.

**See also**  
[Telemetry](telemetry.md) · [Optimisers](optimisers.md)

[<- Telemetry](telemetry.md) · [Next -> Tutorials](../tutorials/index.md)

