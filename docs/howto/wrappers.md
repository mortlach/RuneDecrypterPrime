# Typed constructors and serialized parsers

The former wrapper guide is retired. V1 ordinary code uses typed constructors:

```python
from rdp import api

cipher = api.CipherSpec.vigenere()
key_space = api.KeySpec.repeating(length=6)
solver = api.SolverSpec.beam_search(width=32, rounds=8, seed=7)
```

`CipherSpec.from_name`, `KeySpec.from_name`, `SolverSpec.from_name` and the
`from_dict` methods remain secondary boundaries for genuinely serialized or
dynamically loaded configuration. They are not the normal tutorial route.

Do not add aliases, friendly-name forwarding modules or a runtime-object
materializer. A new supported public family needs an approved typed constructor,
an exact compatible key binding and end-to-end tests.
