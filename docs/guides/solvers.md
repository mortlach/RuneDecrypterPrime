# Choosing and configuring a solver

A solver chooses which keys to try. The cipher turns each key into candidate
plaintext; the scorer ranks that plaintext. We can try a different search method
while keeping the same ciphertext, cipher and possible keys.

Choose a nearby [worked example](../../tutorials/v1/README.md) with a compatible
key shape as a starting point for your own settings.

## Main choices

| Constructor on `api.SolverSpec` | Search approach | Useful controls |
| --- | --- | --- |
| `beam_search(...)` | Retain promising alternatives during key construction and refinement. | `width`, `rounds`, `restarts` |
| `genetic_algorithm(...)` | Select, recombine and mutate a population. | `population_size`, `generations`, `mutation_probability` |
| `simulated_annealing(...)` | Explore changes to a candidate, sometimes accepting a worse score. | `iterations`, `initial_temperature`, `cooling_rate` |
| `hybrid(...)` | Combine beam exploration with genetic and annealing stages. | Beam controls and the two nested solver specifications. |
| `kaeding(...)` | Explore structured periodic keys. | `steps`, `restarts`, block and column controls. |
| `two_period_cribs(...)` | Use crib constraints to reduce a two-period search. | Periods, crib evidence and the bounded search configuration. |

The last two serve specialised problems. A solver needs compatible key
operations, so choosing an algorithm is more than swapping a name.

## Set up a beam search

```python
from rdp import api

solver = api.SolverSpec.beam_search(
    width=16,
    rounds=0,
    seed=4242,
)
```

These values are settings for this example, rather than library defaults.
`width` controls how many alternatives the beam keeps. Making it wider can
keep promising candidates that a narrow beam would discard, but takes more work. `rounds=0` asks the beam implementation to choose its automatic
refinement count; it does not mean zero work. Set a positive value when you want
an explicit round limit. Keep the seed fixed when comparing a budget change.

`plateau_rounds` and `plateau_minimum_delta` describe insufficient improvement;
GA and SA expose corresponding generation and iteration controls. `target_score`
can stop at a configured score, but its meaning depends on the scorer. If you used the original
plaintext to choose that target, say so in the example.

## Compare one change

Keep ciphertext, key space, scoring, direction and seed fixed. Change one budget
and compare the returned candidate, score, evaluation count and stop reason.
The [budget comparison](../../tutorials/v1/getting_started/09_changing_search_budget.py)
shows a case where the wider search does more work and returns the same answer.
Here, the extra work does not improve the result. Try a similar comparison
when deciding whether a larger budget is useful for your problem.

Use `result.solver_report` for work performed and `result.status` for execution
and stopping. Timings vary between runs; the seed alone does not make different
backends, assets or software versions equivalent.

For implementation details, see the [solver source map](../../src/rdp/solvers/README.md)
and [adding a solver](../howto/add_solver.md). The [key-space guide](keyops.md)
explains the structures those algorithms explore.
