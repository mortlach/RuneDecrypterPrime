# Public API

This directory owns the public Python surface reached through:

```python
from rdp import api
```

Normal callers should not need implementation modules below this layer.

## Main owners

- `specs.py` owns `CipherSpec`, `KeySpec` and `SolverSpec`
- `run_spec.py` owns public inputs and `RunSpec`
- `run.py` binds a typed request to execution
- `known_key.py` owns public known-key encrypt/decrypt
- `run_result.py` owns `RunResult`
- `solver_report.py` owns solver, configuration, oracle and reproducibility reports
- `display.py` owns standard human/JSON result summaries
- `liber_primus.py` owns the public LP data namespace
- `experimental.py` owns typed experimental cipher maps and lookups

## Boundary

The public objects describe the experiment.

Runtime configuration and implementation classes below `src/rdp/` are derived
from those objects. They are not additional public request routes.

See [Public API surface](../../../docs/reference/public_api.md),
[Building a run](../../../docs/guides/building_a_run.md) and
[Architecture](../../../docs/architecture/README.md).
