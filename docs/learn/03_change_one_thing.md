# Change one thing


New term? See the [learner glossary](00_words_used_here.md).

A useful solve experiment usually changes one assumption at a time.

Here we ask whether the same ciphertext looks better under a repeating
three-value key or a repeating four-value key:

```python
from rdp import api

ciphertext = api.RuneInput("ᚠᚢᚦᚩᚱᚳ")

for key_length in (3, 4):
    result = api.run(
        api.RunSpec(
            problem_input=ciphertext,
            cipher=api.CipherSpec.vigenere(),
            key_space=api.KeySpec.repeating(
                length=key_length
            ),
            solver=api.SolverSpec.beam_search(),
        )
    )

    print(
        key_length,
        result.score,
        result.plaintext_runes,
    )
```

The cipher, solver and seed stayed the same.

Only this changed:

```text
key length 3
vs
key length 4
```

That makes the comparison easier to interpret than changing the cipher, key
length, scoring and search budget all at once.

This is also the beginning of a useful community result:

> under these exact settings, these were the scores for key lengths 3 and 4.

Someone else can now run the same comparison rather than trying to infer what
you meant by “I tested Vigenere”.

Next: [Use Liber Primus data](04_use_liber_primus.md).
