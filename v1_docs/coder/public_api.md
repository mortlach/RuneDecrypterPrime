# V1 Public API

Status: implemented

Use one import style:

```python
from rdp import api
```

The root has three operations: `api.run`, `api.encrypt`, and `api.decrypt`.
There is no generic transform operation and no public runtime cipher object.
The complete 141-path contract is recorded in
[`../reference/public_api_allowlist.md`](../reference/public_api_allowlist.md).

## Canonical solve request

```python
request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=16, rounds=5, seed=7),
    text_direction=api.TextDirection.LEFT_TO_RIGHT,
)
result = api.run(request)
```

The component overload `api.run(problem_input=..., cipher=..., key_space=...,
solver=...)` is a convenience route to the same immutable request.

| `RunSpec` field | Role |
| --- | --- |
| `problem_input` | One typed raw-text, rune-index, or source-reference input. |
| `cipher` | Immutable `CipherSpec`. |
| `key_space` | The exactly compatible immutable `KeySpec`. |
| `solver` | Immutable `SolverSpec`. |
| `scoring` | Typed `ScoringConfig`. |
| `initial_keys` | Optional tuple of concrete semantic keys. |
| `logging` | Optional typed `LoggingConfig`. |
| `word_length_policy` | Typed policy for missing word-length information. |
| `text_direction` | `TextDirection`, never a raw string. |
| `compute_device` | `ComputeDevice`, never a raw string. |
| `telemetry_enabled` | Explicit boolean telemetry request. |
| `text_permutation` | Optional full-length index permutation. |
| `interruptors` | Optional immutable `InterruptorConfig`. |

## Known-key operations

```python
cipher = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=10)
key: api.ConcreteKey = (7,)
ciphertext = api.encrypt((0, 1, 2, 3), cipher=cipher, key=key)
plaintext = api.decrypt(ciphertext, cipher=cipher, key=key)
```

`ConcreteKey` is exactly `tuple[int, ...]`. Values are semantic values: seven
Rail Fence rails is `(7,)`. Lists and arrays must be normalized before crossing
the public boundary. Both operations return immutable `RuneIndices`.

## Typed construction and parsers

Typed constructors are primary. `from_name` and `from_dict` are secondary
boundaries for genuinely serialized or dynamically loaded configuration. Enum
fields receive enum values directly; ordinary code and tutorials do not pass
raw strings to typed constructors.

Experimental two-input maps and lookups live only under `api.experimental`.
Normal tutorials use no engine implementation imports. Contributor utilities
that need internals import their exact owning module.
