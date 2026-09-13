# RunSpec

`RunSpec` is the typed request for one solve.

```python
request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
)
```

The four fields above are required.

The remaining fields have library defaults. In particular, the current default
text direction is `LTR`, the compute device is `CPU`, WLI policy is
`INFER`, and telemetry is enabled.

`INFER` preserves or derives WLI when the input provides boundaries. `REQUIRE`
fails before solver execution if aligned WLI is unavailable. `DISABLED` removes
WLI and is rejected when the selected scoring configuration requires it.

See [Defaults at a glance](defaults.md).

## Optional run choices

`RunSpec` can also carry:

```text
scoring
initial_keys
logging
word_length_policy
text_direction
compute_device
telemetry_enabled
text_permutation
interruptors
```

For example:

```python
request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
    scoring=scoring,
    text_direction=api.TextDirection.LTR,
    telemetry_enabled=True,
)
```

The complete field table is in
[RunSpec parameters](parameters/run_spec.md).

Live progress is not part of the durable request. Pass a one-argument
`progress_callback` to `api.run(...)` when runtime updates are needed.

## Where the pieces are explained

- [Ciphertext input](../guides/ciphertext_input.md)
- [Keys and key spaces](../guides/keyops.md)
- [Solvers](../guides/solvers.md)
- [Scoring](../guides/scoring.md)
- [Interruptors](../guides/interruptors.md)
- [Telemetry](../guides/telemetry.md)
- [Outputs](../guides/outputs.md)

For the whole request in context, see
[Building a run](../guides/building_a_run.md).
