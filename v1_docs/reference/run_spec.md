# RunSpec reference

Status: implemented

Owner:

```text
src/rdp/api/run_spec.py
```

`RunSpec` is the immutable typed recipe accepted by `api.run`.

| Field | Meaning |
| --- | --- |
| `problem_input` | `RawTextInput`, `RuneIndexInput`, or `SourceReferenceInput`. |
| `cipher` | An immutable `CipherSpec`. |
| `key_space` | The exactly compatible immutable `KeySpec`. |
| `solver` | An immutable `SolverSpec`. |
| `scoring` | Typed `ScoringConfig`. |
| `initial_keys` | Optional tuple of semantic concrete keys. |
| `logging` | Optional typed `LoggingConfig`. |
| `word_length_policy` | Typed policy for missing word-length information. |
| `text_direction` | `TextDirection`; typed constructors reject raw strings. |
| `compute_device` | `ComputeDevice`; typed constructors reject raw strings. |
| `telemetry_enabled` | Explicit telemetry request. |
| `text_permutation` | Optional full-length index permutation. |
| `interruptors` | Optional typed `InterruptorConfig`. |

```python
from rdp import api

request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=16, rounds=5, seed=7),
)
result = api.run(request)
```

The component overload of `api.run` creates the same request. Runtime progress
callbacks are operation arguments and are deliberately absent from durable
`RunSpec` state.
