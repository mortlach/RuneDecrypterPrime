# Telemetry

Telemetry is explicit run state, not a side effect hidden behind an execution
class. Set `RunSpec.telemetry_enabled` to request it and use an optional
`api.LoggingConfig` for durable files.

```python
from rdp import api

request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=8, rounds=2, seed=7),
    telemetry_enabled=False,
)
result = api.run(request)
```

When disabled, the public result reports that choice and does not expose stale
lower-layer telemetry. When enabled, solver and scorer reporting includes
requested/effective configuration, work counters, timing and capability data.

Durable artefact writes are controlled by typed logging fields. Output paths
must remain outside the repository in release work.
