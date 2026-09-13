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
run_category="run"
portable_output=True
write_solver_report=False
write_display_summary=False
write_artifact_manifest=False
```

`output_root`, `label` and `run_directory` default to `None`.

`LoggingConfig` owns durable file output, not console presentation or live
progress. Pass `progress_callback` directly to `api.run(...)` for live updates.

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

With no logging, `RunResult.artifacts` is empty. When logging is enabled, it
contains agreement-backed rows for the metadata/config files and requested
solver-report or display-summary files that are actually present. If a manifest
is requested, its rows agree with the returned rows; the manifest does not list
itself.

## Artifact contracts

Known run-relative paths are `META.json`, `config/logging.json`,
`artifacts/solver_report.json`, `artifacts/rdp_display_summary.json` and
`artifacts/run_artifacts_manifest.json`. The manifest writer requires the first
two files. Solver-report and display-summary files are optional.

Artifact classifications distinguish `candidate`, `not_candidate` and
`needs_review`. Unregistered logs, caches and asset output are not automatically
export candidates. Manifest paths use `/`, stay below the run directory and
must not contain `..` or an absolute machine path.
