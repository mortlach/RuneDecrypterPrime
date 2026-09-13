# Read the result


New term? See the [learner glossary](00_words_used_here.md).

Continue with `result` from the previous example. A solve returns the best
candidate together with reports about the search.

For a first experiment, start with:

```python
print(result.plaintext_runes)
print(result.plaintext_rune_latin)
print(result.plaintext_reading_rune_latin)
print(result.key)
print(result.score)
print(result.status.stop_reason.value)
print(result.solver_report.evaluations)
```

These answer seven useful questions:

| Value | Question |
| --- | --- |
| `plaintext_runes` | What runes did the best candidate produce? |
| `plaintext_rune_latin` | What are their exact canonical RuneLatin identities? |
| `plaintext_reading_rune_latin` | How are those RuneLatin tokens presented for the run direction? |
| `key` | Which key produced it? |
| `score` | How strongly did the scorer rank it? |
| `stop_reason` | Why did the search stop? |
| `evaluations` | How many candidate evaluations were performed? |

`plaintext_indices`, `plaintext_runes`, `plaintext_rune_latin`, and
`plaintext_reading_rune_latin` represent the candidate. Canonical
`plaintext_rune_latin` preserves exact rune labels with `·` between tokens.
The reading field is direction-aware: RTL canonical `R·AE·D` is displayed as
`R·EA·D` for reading. Neither form is an English translation.

The score is a ranking value, not a declaration that the plaintext is correct.

See [What can the score tell you?](05_scoring_limits.md) for the main limits.

A candidate can score well under the wrong cipher hypothesis.

That is why reproducible settings matter: another person can inspect and repeat
the same run, change one assumption, and see whether the result survives.

Next: [Where to go next](06_where_next.md).
