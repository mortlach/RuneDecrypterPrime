# `keyops/registry.py`

> Purpose: registry of key-operations families (permutation, vector, etc.). Solvers and wrappers look up the correct mutation/recombination logic via this module so new key families can be added without touching the engine.

## API
| Function | Description |
| --- | --- |
| `_normalize_family(name)` | Internal helper that maps strings to the `KeyOpsFamily` enum via `ensure_keyops_family`. |
| `register_keyop(name)` | Decorator for factories/classes that implement a key-operations family. Automatically normalises the name and stores the factory. |
| `has(name)` / `get(name)` / `available()` | Capability queries; used by diagnostics and tests (`available()` returns the enum list). |
| `create(name, **kwargs)` | Instantiates a keyops implementation, applying alias conversions for legacy kwarg names (e.g., `length` -> `K`). |

Imports at the bottom (`permutation_ops`, `vector`) register the built-in families when the module loads.

## Usage
```python
from rune_decrypter_prime.keyops.registry import create

perm_ops = create("permutation", K=6)
vector_ops = create("vector", K=29, mod=29)
```

## Tests
- `tests/keyops/test_permutation_key_ops.py`, `tests/keyops/test_vector_key_ops.py` - exercise the factories via `create`.
- `tests/keyops/test_registry_aliases.py` - ensures kwarg aliasing (`length`, `L`, `alphabet_size`) maps to canonical parameters.

## Related Docs
- `docs/reference/core/types.md` - defines the `KeyOpsFamily` enum consumed here.
- `docs/reference/solvers/solver_base.md` - describes how solvers interact with keyops instances during mutation/recombination.

