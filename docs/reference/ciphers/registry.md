# `ciphers/registry.py`

> Purpose: runtime registry that maps cipher names to constructor callables. The by-name wrappers and engine builders rely on this registry to instantiate concrete cipher implementations without hard-coded imports.

## API
| Function | Description |
| --- | --- |
| `register_cipher(name)` | Decorator used by cipher implementations. Registers the constructor under `name.lower()`. Raises `ValueError` if the name already exists. |
| `has(name)` | Returns `True` if a cipher is registered under that name. |
| `get(name)` | Retrieves the constructor callable; raises `KeyError` if not found. |
| `available()` | Returns a sorted list of registered cipher names, useful for diagnostics or CLI listing. |

## Usage Example
```python
from rune_decrypter_prime.ciphers.registry import register_cipher

@register_cipher("my_cipher")
def build_my_cipher(cfg):
    return MyCipher(cfg)
```

Engine builders (`api/wrappers/registry.py`) call `get(name)` when `by_name` requests a cipher instance. Tutorials never touch this module directly, but it keeps the extension story clean.

## Tests
- Exercised indirectly by wrapper/cipher tests (`tests/ciphers/test_by_name_future_wrappers.py`, `tests/ciphers/test_columnar_device_parity.py`), since failing registrations surface when the wrapper tries to instantiate a cipher.

## Related Docs
- `docs/reference/api/wrappers/by_name.md` - user-facing path that ultimately calls into this registry.
- `docs/howto/add_cipher.md` - guides contributors to register promoted ciphers.

