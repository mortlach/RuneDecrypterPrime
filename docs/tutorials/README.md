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

## Contents

- [Run the normal set](#run-the-normal-set)
- [Reading a larger example](#reading-a-larger-example)
- [Where each concept is documented](#where-each-concept-is-documented)

## Run the normal set

```text
python tutorials/v1/run_tutorials.py --list
python tutorials/v1/run_tutorials.py getting-started
python tutorials/v1/run_tutorials.py release
python tutorials/v1/run_tutorials.py --only 01 07 10
```

The runner has separate groups for getting started, the release set,
bundled-asset examples, full-asset examples and qualification. The default is
the release set. Select `bundled`, `full-assets` or `qualification` by name when
you want those groups. `--list` lists the catalogue without running anything.
`--only` selects numbered or named items from the complete catalogue.

You can use the runner without installing RDP. It puts this checkout's `src`
first for itself and its child processes, and launches tutorials with UTF-8.
Prepare the dependencies as described in [Using RDP](../guides/using_rdp.md).

- 01, 07 and 10 work in the basic NumPy source setup with no RDP-native build
- Other normal search tutorials need `_fastlm`, zstandard and bundled LM1/LM2
- Hamming and fast span-Hamming are not prerequisites for the normal groups
- Full-asset examples and qualifications need full_v1 LM1–LM4

Qualification programs may take hours. Read the
[full catalogue and runtime notes](../../tutorials/v1/README.md) before selecting
one. Group membership and tutorial acceptance checks are unchanged.

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
| First search | [Building a run](../guides/building_a_run.md) |
| Repeating keys | [Keys and key spaces](../guides/keyops.md) |
| Reproducibility | [Repeating a run](../guides/reproducibility.md) |
| Interruptors | [Interruptors](../guides/interruptors.md) |
| Liber Primus source | [Ciphertext input](../guides/ciphertext_input.md) |
| Reading a result | [Reading a result](../guides/results.md) |
| Search budget | [Solvers](../guides/solvers.md) |
| Real source search | [Comparing solve experiments](../guides/working_a_solve.md) |

The guides explain the choices. The tutorial files show the same public calls in
runnable form.

