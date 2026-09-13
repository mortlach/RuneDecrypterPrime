# Interruptors

Interruptors are part of the run configuration when the cipher hypothesis
includes positions that interrupt or alter the normal key operation.

RDP supports two common cases:

- exact interruptor positions are already known
- a set of candidate positions should be searched

The configuration is attached to `RunSpec.interruptors`.

## Known positions

When the positions are known:

```python
interruptors = api.InterruptorConfig.exact(
    (12, 47, 81),
)

request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
    interruptors=interruptors,
)
```

Positions are zero-based and duplicates are rejected.

## Search a candidate pool

When the candidate positions are known but the exact subset is not:

```python
interruptors = api.InterruptorConfig.search(
    candidate_positions,
    minimum_count=8,
    maximum_count=12,
)
```

The search defaults are:

```text
minimum_count=0
maximum_count=None
strategy=InterruptorSearchStrategy.AUTO
maximum_combinations=5000
```

When `maximum_count=None`, the upper limit is the size of the candidate pool.

A specific search strategy can be supplied through `api.advanced`:

```python
interruptors = api.InterruptorConfig.search(
    candidate_positions,
    minimum_count=11,
    maximum_count=11,
    strategy=api.advanced.InterruptorSearchStrategy.KEY_OPERATIONS,
    maximum_combinations=5000,
)
```

The complete constructor reference is in
[Interruptor parameters](../reference/parameters/interruptors.md).

## Why the distinction matters

Exact positions and searched positions represent different amounts of prior
information.

If the positions came from a known solution, an exact-position run can still be
useful for testing the cipher and key search. It does not demonstrate discovery
of the interruptor positions.

A candidate-pool search makes that uncertainty part of the experiment.

That distinction belongs in the interpretation of the result, particularly for
solved Liber Primus examples.

See [Comparing solve experiments](working_a_solve.md) and
[Project aims and design principles](../project_overview.md).

## Runnable examples

The numbered tutorials contain both forms:

- `tutorials/v1/getting_started/05_known_interruptors.py` uses known positions
- `tutorials/v1/getting_started/10_prepare_a_real_source_search.py` prepares an
  interruptor search for a Liber Primus source

See [Tutorials and examples](../tutorials/README.md).
