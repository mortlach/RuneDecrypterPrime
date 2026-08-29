# Pipeline: direction, permutation and device

Pipeline controls are typed `RunSpec` fields, not loose dictionaries.

```python
from rdp import api

indices = (0, 1, 2, 3)
request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=indices),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=16, rounds=3, seed=7),
    text_direction=api.TextDirection.LEFT_TO_RIGHT,
    compute_device=api.ComputeDevice.CPU,
    text_permutation=tuple(reversed(range(len(indices)))),
)
result = api.run(request)
```

`text_direction` describes rune interpretation. `text_permutation` is a
full-length permutation applied before solve-time cipher/scoring work and is
validated against the materialised input length. Interruptor positions remain
in the coordinate system defined by the accepted interruptor contract.

Typed constructors require `TextDirection` and `ComputeDevice` enum members.
Serialized strings are accepted only through documented parser boundaries.

Pipeline state is represented in the result's configuration and
reproducibility reports so a run can be replayed without guessing which values
were effective.
