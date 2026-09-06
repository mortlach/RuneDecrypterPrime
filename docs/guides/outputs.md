# Outputs

A normal run can remain in memory:

```python
result = api.run(request)
```

`RunSpec.logging` defaults to `None`, so no run directory is required.

Add `LoggingConfig` when files are needed:

```python
from pathlib import Path
from rdp import api

logging = api.LoggingConfig(
    output_root=Path("my_runs"),
    run_category="solve",
    label="welcome_pilgrim",
    write_solver_report=True,
    write_display_summary=True,
    write_artifact_manifest=True,
)

request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
    logging=logging,
)
```

## Default logging behaviour

A default `LoggingConfig()` uses:

```text
verbose=False
show_progress=True
write_event_log=False
run_category="run"
portable_output=True
write_solver_report=False
write_display_summary=False
write_artifact_manifest=False
```

`output_root`, `label` and `run_directory` default to `None`.

The complete field list is in
[Logging parameters](../reference/parameters/logging.md).

## Telemetry is not logging

Telemetry is returned in memory through `RunResult.telemetry`.

Logging controls files.

A run can therefore use telemetry without creating a run directory, or it can
write selected artifacts through `LoggingConfig`.

See [Telemetry](telemetry.md).

## Display summaries

A run can request a saved display summary through:

```python
logging = api.LoggingConfig(
    write_display_summary=True,
)
```

The same summary can be inspected directly in Python with `api.display`.

See [Displaying results](displaying_results.md).

## Source-checkout output

When no explicit output root is supplied, a source checkout uses its normal
`output/` area.

Use `LoggingConfig.output_root` for another location. The public documentation
uses explicit configuration rather than environment variables.

## Sharing output

Portable output is enabled by default. The normal metadata omits user and
machine identity.

Raw logs and tracebacks can still contain local paths and should be checked
before publication.

For the result-side view of generated files, see `RunResult.artifacts` in
[Reading a result](results.md).
