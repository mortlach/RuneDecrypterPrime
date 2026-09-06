# RunResult

Every successful `api.run(...)` call returns a `RunResult`.

```python
result = api.run(request)
```

Its public fields are:

| Field | Contents |
| --- | --- |
| `plaintext` | Recovered rune indices, or `None`. |
| `plaintext_text` | Rendered plaintext, or `None`. |
| `key` | Best key, or `None`. |
| `score` | Best score, or `None`. |
| `status` | `RunStatus`. |
| `solver_report` | Solver report. |
| `scorer_report` | Scoring report. |
| `configuration` | Effective run configuration. |
| `reproducibility` | Reproducibility metadata. |
| `oracle` | Known-answer/oracle report. |
| `telemetry` | Telemetry mapping. |
| `artifacts` | Artifact-manifest rows. |

`RunResult.key` and the solver report's best key are required to agree.

## A normal first look

```python
print(result.plaintext_text)
print(result.key)
print(result.score)
print(result.status.stop_reason.value)
```

For a standard formatted view:

```python
api.display.print_result(
    result,
    spec=request,
)
```

See [Displaying results](../guides/displaying_results.md).

## Evidence beyond the candidate

The result reports are deliberately separate:

- [Telemetry](../guides/telemetry.md) describes execution behaviour
- [Repeating a run](../guides/reproducibility.md) describes replay information
- [Outputs](../guides/outputs.md) describes saved artifacts
- [Reading a result](../guides/results.md) explains how to interpret the pieces
