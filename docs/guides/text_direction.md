# Text direction

Text direction is a field on `RunSpec`:

```python
text_direction=api.TextDirection.LEFT_TO_RIGHT
```

or:

```python
text_direction=api.TextDirection.RIGHT_TO_LEFT
```

The library default is:

```python
api.TextDirection.RIGHT_TO_LEFT
```

The direction is passed through the solver and scoring path. It therefore
matters when a scoring lane or model is directional.

When direction is part of the question, the clean comparison is to run
the same experiment in both directions and compare the results. The ciphertext,
key space, solver and scoring settings can remain unchanged.

The direction field does not replace the ciphertext representation. Input is
prepared first, then the run records the direction used to interpret and score
it.

See [Ciphertext input](ciphertext_input.md) and [Scoring](scoring.md).

## Where the setting is recorded

Direction is part of the durable `RunSpec`, so it is also available through the
result configuration and reproducibility information.

That makes an LTR/RTL comparison easier to review after the run rather than
relying on a comment in the solving script.

See [RunSpec](../reference/run_spec.md),
[Repeating a run](reproducibility.md) and [Telemetry](telemetry.md).
