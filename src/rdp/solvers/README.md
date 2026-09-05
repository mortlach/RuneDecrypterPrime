# Search algorithms

Solvers decide which candidate keys to evaluate next. Candidate evaluation binds decryption and scoring through the problem object; key operations supply valid candidate changes.

## Where to look

- [beam.py](beam.py) — Retain promising alternatives while extending or refining keys.
- [ga.py](ga.py) — Evolve a population through selection, recombination and mutation.
- [sa.py](sa.py) — Follow a candidate trajectory with temperature-controlled acceptance.
- [hybrid.py](hybrid.py) — Coordinate beam, genetic and annealing stages.
- [kaeding_periodic_structured.py](kaeding_periodic_structured.py) — Search structured periodic substitution keys.
- [two_period_cribs.py](two_period_cribs.py) — Reduce and search two-period problems using crib constraints.
- [solver_base.py](solver_base.py) — Shared solver services and evaluation hooks.
- [seed_generation.py](seed_generation.py) — Construct initial candidate pools.
- [progress/](progress/) — Progress reporting helpers.

## Choices and extension

Choose the algorithm with `api.SolverSpec`. Beam width retains alternatives; GA population size and generations control population work; SA iterations and temperature settings control a trajectory. Hybrid exposes stage-specific budgets. Hold the problem and seed fixed when comparing one setting. A larger budget can cost more without improving the answer.

An extension must use the problem evaluation boundary, respect supplied RNG state and report why it stopped. Check that the selected key operations support the algorithm.

Continue with the [guide](../../../docs/guides/solvers.md) or the [package map](../README.md).
