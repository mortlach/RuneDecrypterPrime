# Pipeline

Direction, device and whole-text permutation are durable fields on
`api.RunSpec`:

```python
from rdp import api

indices = (0, 1, 2, 3)
request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=indices),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=16, rounds=4, seed=3),
    text_direction=api.TextDirection.RIGHT_TO_LEFT,
    compute_device=api.ComputeDevice.CPU,
    text_permutation=tuple(reversed(range(len(indices)))),
)
result = api.run(request)
```

The public boundary validates the permutation against the materialised input and
projects typed values into the existing pipeline. Requested and effective state
is retained in result reports for replay.

See `docs/guides/pipeline.md` for the user-facing rules.
