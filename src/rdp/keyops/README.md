# Key operations

Key operations define how a solver explores valid keys. They generate candidates, normalise their representation and provide changes such as mutation or recombination. This lets the search work with different cipher-specific key structures.

## Where to look

- [base_keyops.py](base_keyops.py) — KeyOpBase and KeyCaps: the operations an implementation supports.
- [vector.py](vector.py) — Sequences of rune values, including repeating-key content.
- [permutation_ops.py](permutation_ops.py) — Orderings that contain each element once.
- [periodic_structured_matrix_ops.py](periodic_structured_matrix_ops.py) — Structured key blocks for periodic substitution.
- [composite.py](composite.py) — A core key combined with searched interruptor positions.
- [registry.py](registry.py) — Construct key operations by their canonical runtime family.

## Choices and extension

Ordinary callers select the key space with `api.KeySpec`; they do not instantiate these classes. A repeating vector allows repeated values, while a permutation must preserve a complete ordering. Composite operations add interruptor choices to the core key.

Custom key types and their search operations can be implemented during cipher development. Define the key layout and invariants first, then implement the required operations and declare capabilities. Solvers can only use operations the implementation supports. Registration uses the existing family model; public integration requires the matching typed binding.

Continue with the [guide](../../../docs/howto/build_keyops.md) or the [package map](../README.md).
