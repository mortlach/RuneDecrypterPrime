# KeyOps - Invariants & Plans

Audience: Expert
Time: 6-10 minutes
Outcome: Use/extend permutation and vector key families with invariant-preserving ops
Prereqs: Read Architecture overview; ran a permutation-based tutorial

- Permutation keys remain bijective after `mutate`/`recombine`/`neighbour`.
- Vector keys wrap modulo-29.
- Invalid candidates are filtered without consuming RNG.

Use `api/specs.py::KeySpec` helpers (e.g., `repeat`, `permutation`, `const`) to define KNF.


