# Solvers

Public code selects a solver with an immutable `api.SolverSpec`:

```python
from rdp import api

beam = api.SolverSpec.beam_search(width=32, rounds=8, seed=7)
ga = api.SolverSpec.genetic_algorithm(
    population_size=256,
    generations=100,
    seed=7,
)
sa = api.SolverSpec.simulated_annealing(iterations=20_000, seed=7)
```

The supported constructors also include hybrid, Kaeding and two-period crib
search. Required budgets are explicit and shared stop/reporting semantics are
returned through `RunResult.status` and `RunResult.solver_report`.

Typed constructor fields receive typed enum values. Name/dictionary parsers are
reserved for serialized or dynamically loaded configuration.

Solver algorithms and their RNG streams remain in their exact engine modules.
The public spec describes a request; it is not a runtime solver object.
