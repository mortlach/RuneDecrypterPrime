# Telemetry

Telemetry records what happened during a run.

It is enabled by default in `RunSpec`:

```python
request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
    telemetry_enabled=True,
)
```

The default is `True`. Set it to `False` when the run does not need execution
telemetry.

The complete `RunSpec` defaults are listed in
[RunSpec parameters](../reference/parameters/run_spec.md).

## Reading telemetry

Telemetry is returned with the result:

```python
result = api.run(request)

telemetry = result.telemetry
```

`result.telemetry` is a mapping. The exact contents depend on the solver and
features used, but normal runs may include:

```text
run
solver
solver_spans
solver_progress
pipeline
scorer
seed
wall_time_s
encoding_dir
```

The run block records the main execution context such as seed, solver, device,
start and end times.

`solver_spans` records solver-specific timing and result information.
`solver_progress` contains progress events emitted during the search.

The pipeline block records text direction and a stable summary of any input
permutation. Scorer telemetry records the effective scoring implementation,
device and related execution details.

A small inspection is often enough:

```python
telemetry = result.telemetry

print(telemetry.get("run", {}))
print(telemetry.get("solver_spans", {}))
print(telemetry.get("solver_progress", [])[:3])
```

Telemetry is returned as data. A log file is not required.

## Telemetry and the result reports

Telemetry answers questions about execution.

Other parts of `RunResult` answer different questions:

- `solver_report` records the solver outcome and search accounting
- `scorer_report` records the scoring configuration and capability state
- `configuration` records the effective run configuration
- `reproducibility` records replay-relevant metadata
- `status` records why the run stopped

For a normal result inspection, start with
[Reading a result](results.md). For a formatted view, see
[Displaying results](displaying_results.md).

## Live progress callbacks

Collected telemetry and live progress are separate controls.

A caller that wants updates while the solver is running can pass a progress
callback to `api.run(...)`:

```python
def show_progress(event):
    print(event)

result = api.run(
    request,
    progress_callback=show_progress,
    progress_interval=10,
)
```

`progress_interval` controls how often the runtime progress hook is called.

The callback receives progress data while the run is active. The final
`RunResult.telemetry` remains the place to inspect collected telemetry after the
run.

Live presentation therefore stays outside the durable run request.

## Telemetry and logging are separate

Telemetry collection does not require `LoggingConfig`.

A run can collect telemetry and return it entirely in memory:

```python
request = api.RunSpec(
    problem_input=problem_input,
    cipher=cipher,
    key_space=key_space,
    solver=solver,
    telemetry_enabled=True,
)

result = api.run(request)
```

`LoggingConfig` is only needed when files should be written.

See [Outputs](outputs.md) and
[Logging parameters](../reference/parameters/logging.md).

## Comparing runs

Telemetry helps when the final plaintext alone does not explain the difference
between two runs.

For example, two runs may return similar candidates but differ in:

- evaluations performed
- solver duration
- progress behaviour
- device or scorer implementation
- pipeline direction
- input permutation

Those differences can help decide whether a change improved the search or only
changed the cost.

Telemetry should not affect candidate ranking. It observes the run.

## Runnable example

`tutorials/v1/getting_started/08_reading_a_result.py` is the closest
getting-started example for inspecting run evidence.

It reads the result, stop reason, solver report and reproducibility information.
Telemetry belongs to the same inspection step and is returned on the same
`RunResult`.

See [Tutorials and examples](../tutorials/README.md) for the full numbered
route.
