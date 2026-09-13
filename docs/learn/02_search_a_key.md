# Search a key

Now let RDP search for an unknown key.

If the terminology is unfamiliar, see
[Words used in the learning examples](00_words_used_here.md).

This first search uses a very short rune string so the structure of the request
is easy to see.

For `width`, `rounds`, `seed` and the other Beam controls, see
[Basic solver settings](02_basic_solver_settings.md).

```python
from rdp import api

request = api.RunSpec(
    problem_input=api.RuneInput("ᚠᚢᚦᚩᚱᚳ"),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(),
)

result = api.run(request)

print(result.plaintext_runes)
print(result.key)
print(result.score)
```

The rune characters are the ciphertext.

`RuneInput` converts them to the same `0..28` rune indices used by the cipher
maths.

The request says:

```text
input       these ciphertext runes
cipher      try Vigenere
key space   search repeating keys of length 3
solver      use Beam search
```

The default scorer ranks the candidate plaintexts.

`api.run(...)` then returns the best candidate found by that search.

The ordinary Beam defaults are enough to try this first experiment.

This tiny ciphertext is for learning the shape of a run. The next steps use the
same structure with real Liber Primus source data.

Next: [Change one thing](03_change_one_thing.md).
