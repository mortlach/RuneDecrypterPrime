# Candidate evaluation

A problem binds the input, cipher, key operations and scoring evidence. Solvers evaluate candidates through this boundary so those components operate on the same text and key representation.

## Where to look

- [spec.py](spec.py) — ProblemSpec describes the problem and transformations.
- [instance.py](instance.py) — ProblemInstance materialises the specification.
- [runtime.py](runtime.py) — DecryptionProblem evaluates key batches and applies constraints.

## Choices and extension

Use the public input types to supply rune text or reviewed indices and word information. Position permutations, interruptors and cribs change the evaluation problem; they are not display choices. Start at `runtime.py` to trace what happens to a candidate key.

Continue with the [guide](../../../../docs/guides/pipeline.md) or the [package map](../../README.md).
