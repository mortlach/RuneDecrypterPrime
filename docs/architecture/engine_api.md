# Engine and public API

Audience: hands-on users and contributors

The V1 public boundary is the definition-owning `rdp.api` package. Public code
uses one import style:

```python
from rdp import api
```

`api.run` is the only solve operation. It accepts either one immutable
`api.RunSpec` or the equivalent typed keyword components.

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

The boundary validates and materialises the request before the existing engine
builds the cipher, key operations, scorer and solver. Engine modules remain
implementation owners; they are not public imports.

Known-key work uses `api.encrypt` and `api.decrypt` with a semantic tuple key:

```python
cipher = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=10)
key: api.ConcreteKey = (7,)
ciphertext = api.encrypt((0, 1, 2, 3), cipher=cipher, key=key)
plaintext = api.decrypt(ciphertext, cipher=cipher, key=key)
```

There is no public runtime cipher object, generic transform operation or class
execution fallback. `api.RunResult` always contains the typed status, solver
report, scorer report, reproducibility information and requested artefacts.

Telemetry is controlled by `RunSpec.telemetry_enabled`. Logging and durable
outputs are configured with `api.LoggingConfig`; progress callbacks remain
runtime-only arguments to `api.run`.
