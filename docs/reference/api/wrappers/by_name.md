# `api/wrappers/by_name.py`

> Purpose: user-facing registry that maps friendly cipher names (`"vigenere"`, `"columnar"`, `"hill"`, etc.) to canonical `CipherSpec`/`KeySpec` pairs. Tutorials use this surface so Hands-on solvers can request ciphers without importing internal modules.

## Main Entry Points
| Helper | Description |
| --- | --- |
| `by_name.cipher(name, **kwargs)` | Returns a `CipherSpec` for a registered cipher. Extra kwargs (e.g., `key_len`, `key_n`, `alphabet_size`) are forwarded to the handler. |
| `by_name.cipher_with_key(name, **kwargs)` | Returns `(CipherSpec, KeySpec or tuple)` so callers can reuse default keys from tutorials. |
| `by_name.cipher_instance(name, **overrides)` | Materialises a live cipher object from the registry (encrypt/decrypt methods). |
| `cipher_instance(spec_or_name, **overrides)` | Lower-level helper used by the class; accepts either a name or a `CipherSpec`. |

Handlers such as `_vigenere`, `_columnar`, `_hill`, `_affine`, `_xor_mod`, etc., all return `(CipherSpec, optional KeySpec)` and rely on `_make_vigenere_like_spec` for fallbacks when the runtime lacks dedicated wrappers.

## Usage
```python
from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name

# Columnar tutorial-style call
cipher_spec = by_name.cipher("columnar", key_len=7)
key_spec = KeySpec.permutation(len=7)

solution = RunAPI.run(
    text="ᚦᛖᚱᛖᛋᚩᛗᛖᛏᛖᛋᛏ",
    cipher=cipher_spec,
    key=key_spec,
    solver=SolverSpec.hybrid(seed=2024),
    telemetry_on=True,
)

# Pull both spec and default key for a Vigenere demo
vig_spec, default_key = by_name.cipher_with_key("vigenere", key_len=6, default_key=True)
```

## Tests
- `tests/ciphers/test_by_name_future_wrappers.py` - ensures every registered name returns a viable cipher instance and round-trips plaintext.
- `tests/ciphers/test_columnar_device_parity.py`, `tests/solvers/test_permutation_optimizers.py` - use `by_name.cipher(...)` to guarantee wrappers integrate with RunAPI and solver engines.
- `tests/smoke/test_runapi_determinism.py` - exercises the Vigenere wrapper in the determinism canary.

## Related Docs
- `docs/howto/wrappers.md` - Hands-on instructions for using and extending by-name wrappers.
- `docs/reference/api/wrappers/registry.md` - describes how the wrapper outputs turn into `CipherConfig` objects for the engine.

