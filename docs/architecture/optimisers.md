# Optimisers

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Pick and compare solvers by shared semantics
Prereqs: Completed one tutorial

**Concept**  
Algorithms that search the key space. Common interface and shared semantics across all algorithms.

## Available
- **SA (Simulated Annealing)** - local moves with early flexibility, then stricter.
- **GA (Genetic Algorithm)** - population, selection, recombination, mutation.
- **Beam** - keep top-B candidates each step, expand systematically.
- **Hybrid** - fixed sequence of phases: **Beam -> GA -> SA**.

## Shared semantics
| Field            | Meaning                                      |
|------------------|----------------------------------------------|
| `eval_budget`    | Maximum candidate evaluations                |
| `time_budget_s`  | Optional time ceiling (seconds)              |
| `patience`       | Stop after this many evaluations without improvement |
| `evals`          | Total evaluations so far                     |
| `since_improve`  | Evaluations since last improvement           |

**Examples (shape)**
```python
best_sa = RunAPI.run(
    ciphertext="...",
    cipher_spec=CipherSpec(name="Substitution"),
    solver_spec=SolverSpec(name="SA", eval_budget=60_000, patience=2_000),
    seed=21,
)

best_ga = RunAPI.run(
    ciphertext="...",
    cipher_spec=CipherSpec(name="Substitution"),
    solver_spec=SolverSpec(name="GA", eval_budget=60_000, patience=2_000),
    seed=21,
)
```

**Telemetry**
- Phase tags are logged for Hybrid (`"phase":"beam" -> "ga" -> "sa"`).  
- `new_best` events include `evals`, `since_improve`, and `best_score`.

**See also**  
[KeyOps](keyops.md) · [Telemetry](telemetry.md) · [Engine & API](engine_api.md)

[<- KeyOps](keyops.md) · [Next -> Telemetry](telemetry.md)

**Related tests**
- `tests/solvers/test_permutation_optimizers.py`
- `tests/tutorials/test_ga_stage2_regression.py`
