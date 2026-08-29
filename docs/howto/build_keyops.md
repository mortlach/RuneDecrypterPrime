# Build a cipher and key operations

Audience: contributors

Prototype new engine behaviour in the existing cipher-development workspace.
Do not expose implementation modules through the public package while the
design is still experimental.

## Implementation checklist

1. Define the concrete semantic key layout and validation rules.
2. Reuse the closest existing cipher and key-operation owners.
3. Implement deterministic encrypt/decrypt behaviour and key-space operations.
4. Register the runtime implementation with its exact existing registry.
5. Add focused round-trip, invalid-key, determinism and solver tests.
6. Add a public typed constructor only when the V1 surface explicitly supports
   the family.

For a supported family, normal public code should read like:

```python
from rdp import api

cipher = api.CipherSpec.vigenere()
key_space = api.KeySpec.repeating(length=6)
solver = api.SolverSpec.genetic_algorithm(
    population_size=128,
    generations=50,
    seed=11,
)
```

Custom two-input map experiments use the typed
`api.experimental.define_cipher_map` contract. They must not add a generic
facade, automatic fallback or public runtime cipher object.

Public known-key calls receive `ConcreteKey = tuple[int, ...]`; they never
receive legacy offsets, mutable lists or arrays.
