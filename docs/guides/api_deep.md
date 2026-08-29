# V1 public API — deeper guide

The canonical public package is `rdp.api`, imported through:

```python
from rdp import api
```

The root surface has three operations: `api.run`, `api.encrypt` and
`api.decrypt`. Public definitions live in `src/rdp/api`; the engine package does
not define a second public interface.

## Typed request flow

Ordinary code constructs typed objects directly:

```python
scoring = api.ScoringConfig(
    objective=api.advanced.ScoringObjective.average_log_probability(),
    backend=api.advanced.ScorerBackend.NUMPY,
)
request = api.RunSpec(
    problem_input=api.RawTextInput("A SHORT EXAMPLE"),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=6),
    solver=api.SolverSpec.genetic_algorithm(
        population_size=128,
        generations=50,
        seed=11,
    ),
    scoring=scoring,
    text_direction=api.TextDirection.LEFT_TO_RIGHT,
)
result = api.run(request)
```

`RunSpec` owns durable run configuration. `progress_callback` and
`progress_interval` are runtime-only arguments to `api.run` and do not alter the
request replay key.

## Construction rules

- Use the named `CipherSpec`, `KeySpec` and `SolverSpec` constructors in normal
  code and tutorials.
- Use `from_name` or `from_dict` only at a genuine serialized or dynamic
  configuration boundary.
- Pass enum instances to typed constructor fields; raw strings belong only at a
  parser boundary.
- Pass immutable rune indices and `ConcreteKey` tuples across public known-key
  operations. Normalize lists and arrays first.
- Use `api.experimental.define_cipher_map` for typed custom map extensions.

Invalid or conflicting configuration fails before engine execution. There are
no aliases, automatic fallbacks, forwarding facades or public runtime cipher
instances.

The complete supported surface is recorded in
`v1_docs/reference/public_api_allowlist.md`.
