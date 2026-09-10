# Solvers

`SolverSpec` defines how RDP searches the key space.

The current public constructors are:

- `beam_search`
- `genetic_algorithm`
- `simulated_annealing`
- `hybrid`
- `kaeding`
- `two_period_cribs`

The complete constructor tables are in
[Solver parameters](../reference/parameters/solvers.md).

## Solvers do not own key mutation

A solver controls the search strategy, not the details of every key type.

RDP supplies each solver with runtime key operations. Beam can ask for an
expansion, GA can ask for recombination and mutation, and SA can ask for a
neighbour.

The KeyOps implementation preserves the invariants of the selected key model.

Beam and GA order top candidates by score descending. Exact score ties keep the
earlier candidate index, including ties at the top-k cutoff, so fixed-seed runs
do not depend on an arbitrary tied sort.

See [Key models and search operations](../architecture/key_model_and_search.md)
and [Solver mechanics](../architecture/solver_mechanics.md).

## Beam search

```python
solver = api.SolverSpec.beam_search(
    width=96,
    rounds=12,
    seed=12345,
)
```

`width` defaults to `64`. `rounds=None` lets the runtime choose the round count.
An explicit positive integer requests that many rounds; `rounds=0` is rejected
at the public boundary because it used to mean something other than zero.

The public defaults use one restart, sweep expansion and a top-parent
fraction of `0.5`.

`plateau_rounds=None` is the request default, but the current engine supplies an
effective plateau of 16 rounds when it is omitted. `rounds=None` also has runtime
meaning: Beam uses `max(2 * key_length, 12)` rounds.

## Genetic algorithm

```python
solver = api.SolverSpec.genetic_algorithm(
    population_size=256,
    generations=200,
    seed=12345,
)
```

The default fractions are `0.1` elite, `0.2` mutation and `0.8` crossover.
Tournament size defaults to `3`.

## Simulated annealing

```python
solver = api.SolverSpec.simulated_annealing(
    iterations=10000,
    seed=12345,
)
```

Only `iterations` is required.

Temperature and cooling settings are optional. Automatic cooling is off by
default.

When the temperature fields are omitted, the current runtime uses `1.0`,
`0.001` and `0.995` for initial temperature, minimum temperature and cooling
rate respectively.

## Hybrid

Hybrid combines a GA spec and a simulated-annealing spec.

A beam phase is enabled by default. When its budget is omitted, the runtime
uses the documented Hybrid defaults.

The Hybrid `target_score` is passed to its Beam, GA and SA phases. A target on a
nested child spec takes precedence for that child, and reaching a target can end
the active phase and the Hybrid run early.

## Kaeding

Kaeding requires `steps`, `restarts` and `inner_batch_size`.

Block scheduling, slip behaviour and plateau stopping have explicit defaults in
the parameter reference.

The public result uses the requested primary scoring objective:
`RunResult.score`, `SolverReport.best_score` and `ScorerReport.score` agree.
When the scorer supplies a raw diagnostic, it remains separate in
`ScorerReport.raw_score`.

## Two-period crib search

The specialised crib solver accepts fixed cribs, candidate words, optional
candidate positions and a start count.

`starts` defaults to `96`.

## Changing the search budget

A larger budget is useful when a smaller run is finding promising structure but
stopping before the search has settled.

Typical comparisons change one budget dimension at a time:

```text
beam width 96 vs 192
beam rounds 12 vs 24
GA generations 200 vs 400
SA iterations 10,000 vs 20,000
```

The final candidate is only part of that comparison. Solver accounting and
telemetry can show whether the extra work changed the search behaviour.

See [Telemetry](telemetry.md) and [Reading a result](results.md).

## Starting keys

`RunSpec.initial_keys` can supply prepared starting points to solvers that
support them.

That changes the experiment and should be recorded as such.

See [Keys and key spaces](keyops.md) and [Comparing solve experiments](working_a_solve.md).

## Runnable examples

- `tutorials/v1/getting_started/02_first_search.py` introduces a solver
- `tutorials/v1/getting_started/09_changing_search_budget.py` changes the search
  budget

See [Tutorials and examples](../tutorials/README.md).

For the full request/effective-default distinction, see
[Solver parameters](../reference/parameters/solvers.md).
