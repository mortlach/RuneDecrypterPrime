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

The original `RunSpec` is the complete durable request. It owns fields such as
the input, direction, initial keys and interruptors.

`RunResult.configuration` records requested and effective solver, scoring and
cipher component configuration. `RunResult.reproducibility` records the replay
metadata it actually owns: effective seed and component configuration, runtime
types, stop information, and authoritative run/Git identity when logging made
that evidence available. It does not independently duplicate every `RunSpec`
field. `RunResult.telemetry` records execution observations.

Compare the `RunSpec` first, then use these result sections to explain what the
runtime resolved and observed.

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
