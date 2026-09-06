# Read the result


New term? See the [learner glossary](00_words_used_here.md).

Continue with `result` from the previous example. A solve returns the best
candidate together with reports about the search.

For a first experiment, start with:

```python
print(result.plaintext_text)
print(result.key)
print(result.score)
print(result.status.stop_reason.value)
print(result.solver_report.evaluations)
```

These answer five useful questions:

| Value | Question |
| --- | --- |
| `plaintext_text` | What text did the best candidate produce? |
| `key` | Which key produced it? |
| `score` | How strongly did the scorer rank it? |
| `stop_reason` | Why did the search stop? |
| `evaluations` | How many candidate evaluations were performed? |

The plaintext text is a display form of the rune-index plaintext returned by
the run.

The score is a ranking value, not a declaration that the plaintext is correct.

See [What can the score tell you?](05_scoring_limits.md) for the main limits.

A candidate can score well under the wrong cipher hypothesis.

That is why reproducible settings matter: another person can inspect and repeat
the same run, change one assumption, and see whether the result survives.

Next: [Where to go next](06_where_next.md).
