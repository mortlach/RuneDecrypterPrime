# Use Liber Primus data

New term? See the [learner glossary](00_words_used_here.md).

Use a named source instead of copying runes out of the book. The source keeps
its catalogue label and transcript version in the run request.

```python
from rdp import api

result = api.run(
    api.RunSpec(
        problem_input=api.liber_primus.source("welcome_pilgrim"),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=8),
        solver=api.SolverSpec.beam_search(),
    )
)

print(result.plaintext_text)
print(result.key)
print(result.score)
```

[CipherSpec](00_words_used_here.md#cipherspec) describes the cipher hypothesis.
[KeySpec](00_words_used_here.md#keyspec) describes the allowed keys.
[SolverSpec](00_words_used_here.md#solverspec) selects the search method.
[RunSpec](00_words_used_here.md#runspec) brings the experiment together.

RDP resolves the named ciphertext and word-length information when the run is
materialised. It rejects a saved source reference if its transcript version no
longer matches the installed data.

This tests a fixed eight-value Vigenere key using ordinary CPU Beam defaults.
It is an experiment, not the complete known Welcome Pilgrim recovery recipe.
It does not supply the interruptor information used by that worked recovery.
An unreadable candidate is therefore possible even when the program succeeds.
Do not interpret completion or a high score as proof of decryption.

For the reviewed recovery with its stated prior information, see
[the solved LP workbook](../../solving/solved_lp/README.md).

Next: [Read the result](05_read_the_result.md).
