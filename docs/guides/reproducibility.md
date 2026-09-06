# Repeating a run

A fixed seed controls the random choices made by a seeded solver. It does not,
by itself, define the whole run.

For a repeatable experiment, the relevant parts normally include:

- problem input
- cipher
- key space
- solver settings and seed
- scoring
- WLI
- text direction
- initial keys
- interruptor configuration
- compute device
- RDP and asset versions where exact replay matters

`RunResult.configuration` records the effective run configuration.
`RunResult.reproducibility` records the replay-relevant metadata.

These are the first places to compare when two runs that should match do not.

## A minimal comparison

```python
first = api.run(request)
second = api.run(request)

print(first.reproducibility)
print(second.reproducibility)
```

For seeded solvers, the requested seed lives in the `SolverSpec`.

For example:

```python
solver = api.SolverSpec.beam_search(
    width=96,
    rounds=12,
    seed=12345,
)
```

The solver parameters are documented in
[Solver parameters](../reference/parameters/solvers.md).

## Telemetry can explain a mismatch

Two runs may use the same high-level request but behave differently because an
execution detail changed.

`RunResult.telemetry` can help compare device, scorer, timing, progress and
pipeline information.

See [Telemetry](telemetry.md).

## Different standards for different jobs

Exploratory solving and strict replay do not always need the same standard.

A solver experiment may care that the same useful plaintext is recovered.

A contract test may require an exact key, score, stop reason and configuration.

A wider qualification campaign may care about the recovery rate across many
seeds or generated cases.

The intended level of repeatability belongs with the experiment.

See [Comparing solve experiments](working_a_solve.md) and
[Extending RDP](extending_rdp.md).

## Runnable example

`tutorials/v1/getting_started/04_reproducible_runs.py` is the numbered example
for seeded repeatability.

See [Tutorials and examples](../tutorials/README.md).
