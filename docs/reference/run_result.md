# RunResult

Every successful `api.run(...)` call returns a `RunResult`.

```python
result = api.run(request)
```

Its public fields are:

| Field | Contents |
| --- | --- |
| `plaintext_indices` | Candidate plaintext as rune indices, or `None`. This does not establish a successful recovery. |
| `word_length_information` | Aligned metadata: one `(position, word_length)` pair per plaintext rune, or `None`. |
| `plaintext_runes` | Rune text with spaces between known words, or `None`. |
| `plaintext_rune_latin` | Canonical RuneLatin: exact rune-token labels joined by `·`, with spaces between known words, or `None`. |
| `plaintext_reading_rune_latin` | Direction-aware RuneLatin for reading. In RTL, letters inside multichar labels are reversed for presentation, or `None`. |
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
print(result.plaintext_runes)
print(result.plaintext_rune_latin)
print(result.plaintext_reading_rune_latin)
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
