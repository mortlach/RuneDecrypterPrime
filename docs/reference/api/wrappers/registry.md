# `api/wrappers/registry.py`

> Purpose: translate `(CipherSpec, KeySpec)` pairs into `CipherConfig` objects understood by the solver engine. Handles both generic user maps (`user_map2/3/lookup`) and named wrappers (vigenere, columnar, substitution, hill).

## Main Helper
| Function | Description |
| --- | --- |
| `build_cipher_config(cipher, key, ciphertext, wli, device, encoding_dir, initial_text_permutation_indices, initial_keys)` | Entry point used by `api/pipeline.execute_run`. Detects the cipher kind and dispatches to the appropriate builder. |

### Generic builders
- `_build_generic_cipher_config(...)` - Applies `resolve_key_length`, stores ciphertext/WLI, encoding direction, permutation, and attaches the original `CipherSpec` via `cfg.spec`.
- `_build_wrapper_cipher_config(...)` - Validates single `KeySpec`, finds the wrapper core (e.g., `"vigenere"`, `"columnar"`), and calls the specialised builder below.

### Wrapper-specific builders
- `_build_vigenere_wrapper`, `_build_columnar_wrapper`, `_build_substitution_wrapper`, `_build_hill_wrapper` - enforce the expected key plan (repeat/permutation/matrix) and derive the effective key length for the solver.

## Usage
Normally this module is called by the pipeline; if you need to materialise a config manually (e.g., testing new wrappers), follow this pattern:
```python
from rune_decrypter_prime.api.wrappers.registry import build_cipher_config

cipher_cfg = build_cipher_config(
    cipher=by_name.cipher("vigenere", key_len=6),
    key=KeySpec.repeat(len=6),
    ciphertext=ct_idx,
    wli=wli_spans,
    device=Device.CPU,
    encoding_dir=Direction.LTR,
    initial_text_permutation_indices=None,
    initial_keys=None,
)
```

## Tests
- `tests/ciphers/test_by_name_future_wrappers.py` - ensures every wrapper's `CipherConfig` can encrypt/decrypt.
- `tests/ciphers/test_columnar_device_parity.py`, `tests/solvers/test_permutation_optimizers.py` - rely on the columnar/vigenere builders to enforce key length/device rules.
- `tests/pipeline/test_permutation_tracking.py` - checks that permutations injected into configs flow through to telemetry.

## See Also
- `docs/reference/api/pipeline.md` - shows where `build_cipher_config` is invoked inside the run pipeline.
- `docs/reference/api/wrappers/by_name.md` - explains how Hands-on callers obtain the `CipherSpec`/`KeySpec` pairs that eventually land here.

