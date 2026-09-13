# API reference

The stable public route starts with:

```python
from rdp import api
```

A normal search is:

```python
request = api.RunSpec(
    problem_input=...,
    cipher=...,
    key_space=...,
    solver=...,
)

result = api.run(request)
```

## Core reference

- [Full A-Z glossary](glossary.md)
- [Public API surface](public_api.md)
- [Problem inputs](inputs.md)
- [RunSpec](run_spec.md)
- [RunResult](run_result.md)
- [Configuration objects](configuration.md)
- [Known-key encrypt and decrypt](known_key.md)
- [Liber Primus data](liber_primus.md)
- [Public errors](errors.md)
- [Experimental ciphers](experimental.md)

## Parameters and defaults

- [Defaults at a glance](defaults.md)
- [Complete parameter reference](parameters/README.md)

The guides explain why a setting matters. The parameter pages record the exact
public fields and library defaults.
