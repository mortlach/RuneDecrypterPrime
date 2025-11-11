# `api/api_utils.py`

> Purpose: lightweight helpers that enforce consistent metadata on `CipherSpec`/`KeySpec` objects before they're transformed into `CipherConfig`. These functions are used by wrappers/registry to validate key plans and infer key lengths.

## Functions
| Helper | Description |
| --- | --- |
| `resolve_cipher_kind(cipher)` | Ensures a `CipherSpec` declares `kind` and returns it as a string. `build_cipher_config` uses this to route the spec to the right builder. |
| `resolve_key_length(key_spec, ciphertext_len)` | Infers the effective key length from a `KeySpec` plan (repeat, perm, otp, const, scalar). Fallbacks to ciphertext length when appropriate. |
| `expect_key_plan(key_spec, plan, message)` | Validates that a `KeySpec` uses a specific plan and raises a readable error if not. Wrapper builders call this to enforce UX guarantees (e.g., columnar expects `KeySpec.permutation`). |

## Usage Example
```python
from rune_decrypter_prime.api.api_utils import resolve_key_length, expect_key_plan
from rune_decrypter_prime.api.specs import KeySpec

key = KeySpec.repeat(len=6)
length = resolve_key_length(key, ciphertext_len=120)  # -> 6

expect_key_plan(key, "repeat", "Vigenere requires KeySpec.repeat(len=K)")
# expect_key_plan(KeySpec.permutation(len=6), "repeat", "...") would raise ValueError
```

## Tests & Guardrails
- `tests/ciphers/test_by_name_future_wrappers.py` - exercises `expect_key_plan` and `resolve_key_length` via the wrapper builders (invalid plans raise immediately).
- `tests/ciphers/test_columnar_device_parity.py` - relies on the key-length inference to ensure the columnar cipher uses the correct permutation size.

## See Also
- `docs/reference/api/wrappers/registry.md` - call site where these helpers are used to produce `CipherConfig`.
- `docs/reference/api/pipeline.md` - downstream consumer of the configs that pass through these helpers.

