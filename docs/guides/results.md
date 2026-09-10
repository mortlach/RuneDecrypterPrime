# Reading a result

`api.run(...)` returns a `RunResult`.

The fields normally read first are:

```text
plaintext_indices
word_length_information
plaintext_runes
plaintext_rune_latin
plaintext_reading_rune_latin
key
score
status
```

## Candidate

`plaintext_indices` contains rune indices. `word_length_information` is aligned
metadata recording the word boundaries when they are known. `plaintext_runes`
renders those indices as rune text. `plaintext_rune_latin` is the canonical
identity view: it uses the exact RuneLatin label for each rune and joins tokens
with `·`. `plaintext_reading_rune_latin` is the direction-aware reading view.
For RTL “READ”, the same three runes are canonical `R·AE·D` and reading-order
`R·EA·D`. The reading view is for presentation; parse the canonical view when
exact rune identity must round-trip.

These are representations of the same candidate. They are not an English
translation. `key` is the best key returned by the solver.

These fields can be `None` when the run did not produce a candidate.

For a formatted console view:

```python
api.display.print_result(
    result,
    spec=request,
)
```

See [Displaying results](displaying_results.md).

## Score

`score` is the score of the selected candidate under the scoring setup used by
that run.

A score is only meaningful in the context of the scorer that produced it.
Different scoring configurations can have different scales and behaviour.

See [Scoring](scoring.md).

## Status

`status` records the execution and stopping outcome.

Typical inspection looks like:

```python
print(result.status.execution_status.value)
print(result.status.stop_category.value)
print(result.status.stop_reason.value)
```

A normal stop means the search ended according to its rules. Recovery is a
separate question.

The solver report contains the detailed search information behind that status.

## Reports

`RunResult` also contains:

- `solver_report`
- `scorer_report`
- `configuration`
- `reproducibility`
- `oracle`
- `telemetry`
- `artifacts`

These objects keep the candidate, configuration and evidence about the run
separate.

`configuration` distinguishes the public request from effective component
configuration. `scorer_report.capabilities` carries the typed runtime lane
states, and `scorer_report.telemetry` contains only scorer-owned telemetry;
whole-run observations remain in `telemetry`. `reproducibility` contains the
replay metadata it owns, while the original `RunSpec` remains the complete
durable request.

When logging is absent, `artifacts` is empty. For a logged run it lists the
agreement-backed metadata/config and requested report files actually present.

Useful follow-on pages are:

- [Telemetry](telemetry.md) for execution behaviour
- [Repeating a run](reproducibility.md) for replay information
- [Outputs](outputs.md) for saved artifacts
- [RunResult reference](../reference/run_result.md) for the field list

## Known answers

Ordinary `api.run()` has no general known-plaintext or known-key input, so its
oracle report is normally unavailable. The existing explicit internal/test-key
fast path reports test-mode oracle use and the `ORACLE_TEST_KEY_USED` stop
reason. A result is not marked as oracle-assisted merely because it happens to
recover a known answer.

Callers may still compare a result with external truth after the search. Truth
used to rank candidates or stop the search is part of the method and supports a
different claim.

This distinction is also used in the
[project design principles](../project_overview.md).

## Runnable example

`tutorials/v1/getting_started/08_reading_a_result.py` walks through the main
result fields, stop reason, solver report and reproducibility metadata.

See [Tutorials and examples](../tutorials/README.md).
