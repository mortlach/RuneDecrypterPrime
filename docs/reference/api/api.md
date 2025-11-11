# `api/api.py`

> Purpose: keep the historical `rune_decrypter_prime.api` surface stable by re-exporting the UX helpers that live in `api/maps_api.py`. Tutorials/users can still call `define_map`, `define_cipher`, and `preview` without importing the newer modules directly.

## Exports
| Symbol | Description | Implementation |
| --- | --- | --- |
| `define_map(*, function=None, table=None, **opts)` | Build a `CipherSpec` for user-defined lookup maps or callables (see `api/maps_api.py::define_map`). Exactly one of `function`/`table` is required. | Delegates to `maps_api.define_map` |
| `define_cipher(spec=None, name=None, key=None, key_len=None, **kwargs)` | Convenience helper returning `(CipherSpec, KeySpec)` for either an explicit spec or a registered wrapper name. | Delegates to `maps_api.define_cipher` |
| `preview(text, *, cipher, key, direction="decrypt", text_encoding_direction="ltr", device="cpu")` | Run a one-off encrypt/decrypt against a fully specified cipher + key (OTP/const) without invoking the solver engine. | Delegates to `maps_api.preview` |

All three helpers are also re-exported from `rune_decrypter_prime.api.__init__`, so `from rune_decrypter_prime.api import define_map` continues to work.

## Usage
```python
from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, define_map, define_cipher

# 1. Author a custom XOR map (user_map2) and solve it end-to-end.
xor_spec = define_map(
    function=lambda pt, key: (pt + key) % 29,
    degeneracy="forbid",
    name="xor29",
)
cipher_spec, key_spec = define_cipher(spec=xor_spec, key=KeySpec.repeat(len=1))

solution = RunAPI.run(
    text="ᛗᛖᛏᚻᚩᚾ",
    cipher=cipher_spec,
    key=key_spec,
    solver=SolverSpec.ga(pop_size=64, generations=40, seed=1234, progress_pct=1),
    telemetry_on=True,
)
print(solution.score)

# 2. Quickly preview a lookup cipher without running a solver.
preview_ct = preview(
    text=[19, 10, 3, 9],
    cipher=cipher_spec,
    key=KeySpec.const(value=5),
    direction="decrypt",
)
```

## Related Tests
- `tests/ciphers/test_custom_define_map.py` - round-trip + telemetry coverage for `define_map`/`define_cipher`.
- `tests/ciphers/test_generic_map_degeneracy.py` - degeneracy/per-position guardrails for user maps.
- `tests/tutorials/test_crib_drag_api.py` - integration path that mixes standard wrappers with custom specs.

## See Also
- `docs/howto/add_cipher.md` - promoting tutorial experiments into core ciphers.
- `docs/guides/outputs.md` - explains where the preview/solver runs deposit logs.

