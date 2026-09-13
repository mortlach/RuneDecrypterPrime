# Solvers

Solvers decide which candidate keys to evaluate next.

They share the same materialised problem, KeyOps, scorer and seeded RNG.

Beam retains and expands promising candidates.

GA evolves a population through selection, recombination and mutation.

SA follows a neighbour trajectory with temperature-controlled acceptance.

Hybrid coordinates existing search stages. Kaeding and two-period crib search
cover more specialised problem structures.

See [Solver mechanics](../../../docs/architecture/solver_mechanics.md) and
[Add a solver](../../../docs/howto/add_solver.md).
