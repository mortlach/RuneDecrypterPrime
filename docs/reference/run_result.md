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
| `scorer_report` | Scoring report. Its capabilities are the typed scorer-lane states observed at runtime, and its telemetry is scorer-specific. |
| `configuration` | Requested and effective solver, scoring and cipher configuration. Resolved scorer backend evidence is used when available. |
| `reproducibility` | Replay metadata owned by the result, including effective seed/configuration and authoritative run/Git identity when available. It is not a replacement for the complete `RunSpec`. |
| `oracle` | Normally unavailable because `api.run()` has no general oracle input. Explicit internal test-key use is reported as test-mode oracle evidence. |
| `telemetry` | Complete run telemetry mapping. |
| `artifacts` | Agreement-backed rows for files actually present. Empty when logging is disabled. |

`RunResult.key` and the solver report's best key are required to agree.
`RunResult.score`, `SolverReport.best_score` and `ScorerReport.score` describe
the same selected primary-objective score. `ScorerReport.raw_score` is separate
raw diagnostic evidence when the runtime supplies it.

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
