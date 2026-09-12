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

## Two-period crib search

The CPU-only two-period crib solver targets additive Vigenere over the 29-rune
alphabet. The two periods belong to `CipherSpec.two_period_vigenere`; its
compatible repeating key has `first_period + second_period` values in A-then-B
order. Each value is a semantic rune shift in `0..28`. A conflicting key length
is rejected.

Cribs must cover complete words according to the supplied word-length
information. Fixed cribs specify known placements; candidate words are tried at
every matching complete-word span. Impossible or incompatible placements are
reported as rejection evidence.

An omitted seed has the deterministic effective value `0`. Search uses S2 scout
(5 coordinate sweeps), B1 bridge (4) and F1 judge (3), then static F1 ranking over
the complete deduplicated union of candidates from all three stages.

Structural interruptors are removed before the core cipher runs and reinserted
unchanged afterwards. Crib equations use compacted core positions, not absolute
full-text positions. A crib rune on an interruptor must match the unchanged
ciphertext rune and adds no key equation.

Automatic structural search enumerates hypotheses within `bruteforce_max`.
Exceeding that cap raises an error: narrow the pool/count range, raise the cap,
or explicitly request brute force. The KeyOps search strategy is unsupported
for this constraint route. The standard `RunResult` includes the requested
interruptor configuration, hypothesis count and winning positions in its solver
report.

See [Solver parameters](../reference/parameters/solvers.md) and the runnable
[two-period crib example](../../tutorials/v1/examples/two_period_cribs.py).

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
