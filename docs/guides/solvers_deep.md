# Solvers — deeper guide

The public request layer describes solver work with `api.SolverSpec`; it does not
expose runtime solver instances.

```python
from rdp import api

solver = api.SolverSpec.hybrid(
    genetic_algorithm=api.SolverSpec.genetic_algorithm(
        population_size=128,
        generations=50,
        seed=11,
    ),
    simulated_annealing=api.SolverSpec.simulated_annealing(
        iterations=10_000,
        seed=11,
    ),
    beam_width=32,
    beam_rounds=4,
    seed=11,
)
```

Beam, genetic algorithm, simulated annealing, hybrid, Kaeding and two-period
crib search share typed seed, budget, plateau and target-score concepts where
applicable. Each constructor exposes only parameters that its implementation
supports.

The engine owns counters, RNGs, progress events and stop production. The public
result normalizes those into `RunStatus`, `SolverReport` and reproducibility
metadata without a compatibility execution class.
