# Solver mechanics

A solver decides which candidate key to evaluate next.

The cipher defines what a key does.

KeyOps defines valid moves through the key space.

The problem object decrypts and scores candidates.

## Shared state

Generic solvers receive:

```text
problem
key operations
key length
seeded RNG
optional initial keys
stopping controls
progress callback
```

Initial keys are normalised against the runtime key model.

All solver randomness uses the RNG supplied by the engine.

## Beam search

Beam keeps a set of strong candidates and expands them repeatedly.

Its KeyOps preference is:

```text
expand_position
-> batch_neighbors
-> mutate
```

Vector keys can enumerate one key position. Permutation keys expose
permutation-safe alternatives.

Beam controls which candidates survive. KeyOps controls what a valid expansion
looks like.

## Genetic algorithm

GA uses:

```text
seed population
-> score
-> select parents
-> recombine
-> mutate
-> score children
-> retain best population
```

Population generation, recombination and mutation come from KeyOps where those
capabilities are available.

## Simulated annealing

SA follows one candidate trajectory.

It asks KeyOps for a neighbour, scores the candidate, then accepts or rejects
the move using the current temperature.

The key family defines the neighbourhood.

## Hybrid and specialised solvers

Hybrid combines existing search stages.

Kaeding is specialised for structured periodic keys.

The two-period crib solver has its own staged reduction/search path but returns
the standard public result contract.

## Evaluation

Generic solvers score candidate batches through the shared problem boundary.

See [Candidate evaluation](candidate_evaluation.md).

## Stopping

Solver configuration can include budget limits, target scores and plateau
stopping.

A stop reason describes why search ended. It is not proof of recovery.

See [Reading a result](../guides/results.md).

## Adding a solver

A new generic solver should use the supplied RNG, KeyOps capabilities, shared
candidate evaluation, common progress reporting and standard result path.

Adding a runtime implementation and adding a public `SolverSpec` family are
separate changes.

See [Add a solver](../howto/add_solver.md).
