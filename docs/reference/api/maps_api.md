# `api/maps_api.py`

> Purpose: UX helpers for creating custom lookup/map ciphers that still plug into `RunAPI`. Tutorials use these helpers so Hands-on solvers can define tables/functions without touching core registration.

## Key Helpers
| Function | Description | Notes |
| --- | --- | --- |
| `define_map(*, function=None, table=None, degeneracy="forbid", resolver="first", per_pos_limit=1, name=None)` | Build a `CipherSpec` for either a callable map (`function(pt, key)` or `function(pt, k1, k2)`) or a lookup table. | Exactly one of `function`/`table` is required. Picks `user_map2`, `user_map3`, or `lookup` under the hood. |
| `define_cipher(spec=None, name=None, key=None, key_len=None, **kwargs)` | Return `(CipherSpec, KeySpec)` by either wrapping an explicit spec or reusing a registered by-name cipher (e.g., `"columnar"`). | Mirrors the defaults exposed via `api/wrappers/by_name.py`. |
| `preview(text, *, cipher, key, direction="decrypt", text_encoding_direction="ltr", device="cpu")` | Perform a single encrypt/decrypt against a fully specified cipher + key without invoking a solver. | Accepts rune indices, rune strings, or English strings; key must be `KeySpec.otp(...)` or `KeySpec.const(...)`. |

## Usage
```python
from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec
from rune_decrypter_prime.api.maps_api import define_map, define_cipher, preview

# Define a user_map2 cipher (pt XOR key mod 29) and obtain solver-ready specs.
xor_spec = define_map(
    function=lambda pt, key: (pt + key) % 29,
    degeneracy="forbid",
    name="xor29",
)
cipher_spec, key_spec = define_cipher(spec=xor_spec, key=KeySpec.repeat(len=1))

# Solve the cipher through RunAPI.
solution = RunAPI.run(
    text="ᛗᛖᛏᚻᚩᚾ",
    cipher=cipher_spec,
    key=key_spec,
    solver=SolverSpec.ga(pop_size=40, generations=30, seed=4321, progress_pct=1),
    telemetry_on=True,
)

# Preview the same cipher without running a solver (OTP key example).
preview_indices = preview(
    text=[19, 10, 3, 9],
    cipher=cipher_spec,
    key=KeySpec.otp(stream=[1, 2, 3, 4]),
    direction="decrypt",
)
print(preview_indices.tolist())
```

## Validation & Tests
- `tests/ciphers/test_custom_define_map.py` - round-trip + telemetry expectations for `define_map`/`define_cipher`.
- `tests/ciphers/test_generic_map_degeneracy.py` - degeneracy/per-position guardrails when supplying tables/functions.
- `tests/tutorials/test_crib_drag_api.py` - uses `define_cipher` to mix custom specs with standard tutorials.

## Related Docs
- `docs/howto/add_cipher.md` - when to promote a tutorial experiment into a reusable cipher.
- `docs/reference/api/api.md` - describes the legacy re-export surface that forwards to this module.
- `docs/guides/outputs.md` - explains where preview/RunAPI runs log their results.

