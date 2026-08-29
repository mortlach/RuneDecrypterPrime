# Telemetry essentials

Telemetry is controlled by `RunSpec.telemetry_enabled` and returned in the typed
`RunResult` reports.

```python
from rdp import api

request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=8, rounds=2, seed=7),
    telemetry_enabled=True,
)
result = api.run(request)
```

Use `result.status`, `result.solver_report`, `result.scorer_report`,
`result.reproducibility` and `result.telemetry` instead of parsing human console
text. Requested/effective seed, device, objective, work counters, stop reason
and scorer capability remain explicit.

Durable JSONL and summary artefacts require a typed `api.LoggingConfig`. Public
display/share output uses `api.display`; contributor tools that need raw
telemetry import the exact telemetry owner.

When telemetry is disabled, lower-layer stale values must not leak into the
public result. Truth/oracle use and report-only diagnostics remain separately
labelled and cannot silently steer ranking.
