# Reading a result

`api.run(...)` returns a `RunResult`.

The fields normally read first are:

```text
plaintext_indices
word_length_information
plaintext_runes
plaintext_rune_latin
key
score
status
```

## Candidate

`plaintext_indices` contains rune indices. `word_length_information` records
the word boundaries when they are known. `plaintext_runes` renders those
indices as rune characters, while `plaintext_rune_latin` renders the same runes
with `·` between rune tokens. For example, the direction-specific encoding of
“THE” can be `TH·E` in LTR or `T·H·E` in RTL. Both are correct RuneLatin for
the rune sequence actually produced.

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

Useful follow-on pages are:

- [Telemetry](telemetry.md) for execution behaviour
- [Repeating a run](reproducibility.md) for replay information
- [Outputs](outputs.md) for saved artifacts
- [RunResult reference](../reference/run_result.md) for the field list

## Known answers

When an expected plaintext or key is available, the oracle report records the
known-answer side of the result.

Truth used only after the search checks recovery. Truth used to rank candidates
or stop the search is part of the method and supports a different claim.

This distinction is also used in the
[project design principles](../project_overview.md).

## Runnable example

`tutorials/v1/getting_started/08_reading_a_result.py` walks through the main
result fields, stop reason, solver report and reproducibility metadata.

See [Tutorials and examples](../tutorials/README.md).
