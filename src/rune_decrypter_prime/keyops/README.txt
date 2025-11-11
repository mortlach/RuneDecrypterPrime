rune_decrypter_prime/keyops
===========================

KeyOps = key manipulation layer. It is responsible for generating, mutating,
normalising, and batching keys for optimisers; ciphers never perform these steps.

Key pieces
----------
- `registry.py`: maps `KeyOpsFamily` enums (`vector`, `permutation`, …) to the
  concrete classes and exposes `create(...)`.
- `vector.py`: additive vector keys (Vigenère-style) with neighbourhood and
  population helpers.
- `permutation_ops.py` (and future modules): permutation-based keys for
  substitution/columnar ciphers.
- `base_keyops.py`: base class plus `KeyCaps` describing available operations.

Guidelines
----------
- KeyOps must be deterministic when given the same RNG seed.
- They own every mutation strategy. Solvers call verbs like `random`, `mutate`,
  `recombine`, `batch_neighbors`, etc., without knowing cipher specifics.
- Validation lives here: a cipher should trust that any key coming through
  `Problem.evaluate_keys` already matches the declared family/length.
