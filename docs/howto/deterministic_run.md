# Run a deterministic solve

Put the seed on the typed solver specification and retain the request/result
pair:

```python
from rdp import api

request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=16, rounds=5, seed=2025),
    text_direction=api.TextDirection.LEFT_TO_RIGHT,
    compute_device=api.ComputeDevice.CPU,
)
result = api.run(request)
```

Compare `result.reproducibility`, `result.status`, the recovered key/plaintext
and score across runs. Requested and effective seeds are reported separately.

Keep inputs, assets, package version, compute device and scoring configuration
the same. A deterministic seed cannot compensate for a different runtime or
asset set.
