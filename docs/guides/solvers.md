# Choosing and configuring a solver

A solver chooses which keys to try. The cipher turns each key into candidate
plaintext; the scorer ranks that plaintext. A different solver changes the
search strategy while the cryptanalytic hypothesis can stay the same.

Choose a nearby [worked example](../../tutorials/v1/README.md) with a compatible
key shape before tuning a new recipe.

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

## A bounded beam request

```python
from rdp import api

solver = api.SolverSpec.beam_search(
    width=16,
    rounds=0,
    seed=4242,
)
```

These are example settings, not general defaults. `width` controls the retained
alternatives; a wider beam can keep candidates that a narrow beam discards, at
additional cost. `rounds=0` asks the beam implementation to choose its automatic
refinement count; it does not mean zero work. Set a positive value when you want
an explicit round limit. Keep the seed fixed when comparing a budget change.

`plateau_rounds` and `plateau_minimum_delta` describe insufficient improvement;
GA and SA expose corresponding generation and iteration controls. `target_score`
can stop at a configured score, but its meaning depends on the scorer. If known
plaintext was used to choose that target, disclose that reference use.

## Compare one change

Keep ciphertext, key space, scoring, direction and seed fixed. Change one budget
and compare the returned candidate, score, evaluation count and stop reason.
The [budget comparison](../../tutorials/v1/getting_started/09_changing_search_budget.py)
shows a case where the wider search does more work and returns the same answer.
More search is useful when it finds a better candidate; it is not evidence by
itself that the candidate is correct.

Use `result.solver_report` for work performed and `result.status` for execution
and stopping. Timings vary between runs; the seed alone does not make different
backends, assets or software versions equivalent.

For implementation details, see the [solver source map](../../src/rdp/solvers/README.md)
and [adding a solver](../howto/add_solver.md). The [key-space guide](keyops.md)
explains the structures those algorithms explore.
