# First solve

Start with `tutorials/v1/Tutorial_Start_Here.py`. It uses the same typed public
API as normal applications.

The smallest runnable shape is:

```python
from rdp import api

request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=8, rounds=2, seed=7),
    text_direction=api.TextDirection.LEFT_TO_RIGHT,
)
result = api.run(request)

print(result.status)
print(result.plaintext)
```

The four required ideas are visible in the request: input, cipher, key space and
solver. The seed makes solver behaviour reproducible. Scoring, logging and other
advanced fields have typed defaults.

Use `api.RawTextInput` when RDP should encode text for you. Use
`api.RuneIndexInput` when your rune indices are already normalized. Invalid
indices, mismatched cipher/key dimensions and raw strings in typed enum fields
fail before the solve starts.

For known keys, use `api.encrypt` and `api.decrypt` with a tuple key. These
operations return immutable rune-index tuples.
