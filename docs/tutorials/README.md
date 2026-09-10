# Tutorials and examples

The numbered getting-started files form the learning route:

```text
tutorials/v1/getting_started/
```

They cover, in order:

1. known-key encryption and decryption
2. a first solver search
3. repeating-key search
4. reproducible runs
5. known interruptors
6. partial recovery
7. loading a Liber Primus source
8. reading a result
9. changing the search budget
10. preparing a real-source search

The larger programs under `tutorials/v1/examples/` show complete cipher and
solver combinations.

For a route built specifically around genuine solved Liber Primus material, see
[Start solving Liber Primus](../../solving/lp_getting_started/README.md). The
[detailed solved-page workbooks](../../solving/solved_lp/README.md) are separate:
they are evidence-oriented rather than a beginner tutorial.

## Run the normal set

```text
python tutorials/v1/run_tutorials.py
```

The runner has separate groups for getting started, the release set,
bundled-asset examples, full-asset examples and qualification. The default is
the release set.

## Reading a larger example

The useful structure is:

1. source or ciphertext
2. cipher hypothesis
3. key space
4. solver and search budget
5. scoring information
6. initial keys or interruptor assumptions, if any
7. expected evidence from the result

Example settings belong to that experiment. They are not library defaults
unless the example says so.

See [Comparing solve experiments](../guides/working_a_solve.md).

## Where each concept is documented

The numbered route is backed by the main guides:

| Tutorial topic | Documentation |
| --- | --- |
| Known key | [Keys and key spaces](../guides/keyops.md) |
| First search | [Defining a run](../guides/anatomy_of_a_run.md) |
| Repeating keys | [Keys and key spaces](../guides/keyops.md) |
| Reproducibility | [Repeating a run](../guides/reproducibility.md) |
| Interruptors | [Interruptors](../guides/interruptors.md) |
| Liber Primus source | [Ciphertext input](../guides/ciphertext_input.md) |
| Reading a result | [Reading a result](../guides/results.md) |
| Search budget | [Solvers](../guides/solvers.md) |
| Real source search | [Comparing solve experiments](../guides/working_a_solve.md) |

The guides explain the choices. The tutorial files show the same public calls in
runnable form.

