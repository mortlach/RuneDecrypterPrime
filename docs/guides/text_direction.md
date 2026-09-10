# Text direction

Text direction is a field on `RunSpec`:

```python
text_direction=api.TextDirection.LTR
```

or:

```python
text_direction=api.TextDirection.RTL
```

The library default is:

```python
api.TextDirection.LTR
```

`LTR` and `RTL` are the preferred names. `LEFT_TO_RIGHT` and
`RIGHT_TO_LEFT` remain equivalent aliases when the longer wording is useful.

The direction is passed through the input, solver, and scoring path. English
`RuneInput` values are converted using this direction; scoring lanes and models
may also be directional.

When direction is part of the question, the clean comparison is to run
the same experiment in both directions and compare the results. The ciphertext,
key space, solver and scoring settings can remain unchanged.

The direction field does not replace the ciphertext representation. `RuneInput`
records what was supplied, and the complete run uses the direction to
materialise, interpret, and score it.

See [Ciphertext input](ciphertext_input.md) and [Scoring](scoring.md).

## Where the setting is recorded

Direction is part of the durable `RunSpec`. Runtime pipeline telemetry also
records direction when telemetry is enabled. The current reproducibility schema
does not independently duplicate this field.

That makes an LTR/RTL comparison easier to review after the run rather than
relying on a comment in the solving script.

See [RunSpec](../reference/run_spec.md),
[Repeating a run](reproducibility.md) and [Telemetry](telemetry.md).
