# Add A Cipher

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/ciphers/`
- `src/rune_decrypter_prime/ciphers/registry.py`
- `src/rune_decrypter_prime/ciphers/base_keyed_cipher.py`
- `src/rune_decrypter_prime/ciphers/ciphers_pipeline.py`
- `src/rune_decrypter_prime/api/wrappers/by_name.py`
- `tests/`

Related coder pages:
- `coder/cipher_pipeline.md`
- `coder/key_pipeline.md`
- `coder/extension_points.md`

## Goal

Add a cipher implementation that can be materialised by the runtime and tested
without changing unrelated solver or scorer behavior.

## Steps

1. Create the cipher module under `src/rune_decrypter_prime/ciphers/`.
2. Subclass `KeyedCipherBase` when the cipher has a normal keyed batch model.
3. Include `CipherPipelineMixin` when the cipher should respect text or key
   transposition pipeline handling.
4. Decorate the concrete class with `register_cipher("name")`.
5. Set `keyops_family` and `key_length` so the problem can build compatible
   KeyOps.
6. Implement `_core_decrypt_batch(ct_tr, keys_tr)`.
7. Implement `_core_encrypt_batch(pt_tr, keys_tr)` when tests or tutorials need
   encryption.
8. Import or expose the class where the package expects it.
9. Add a public wrapper in `api/wrappers/by_name.py` only when the cipher is
   meant to be user-facing.
10. Add focused tests.

## Cipher Contract

The hot path expects arrays in core order:

| Method | Input | Output |
| --- | --- | --- |
| `_core_decrypt_batch` | `ct_tr` shaped `[L]`, `keys_tr` shaped `[B,K]` | plaintext batch shaped `[B,L]` |
| `_core_encrypt_batch` | `pt_tr` shaped `[L]`, `keys_tr` shaped `[B,K]` | ciphertext batch shaped `[B,L]` |

Use `uint8` index arrays at the boundary. If arithmetic needs a wider type,
cast back before returning.

Do not normalize keys inside the decrypt hot path. KeyOps owns repair,
normalization, random population, mutation, and local improvement.

## Registry Wiring

Use:

```python
from rune_decrypter_prime.ciphers.registry import register_cipher

@register_cipher("example")
class ExampleCipher(CipherPipelineMixin, KeyedCipherBase):
    ...
```

The registry rejects duplicate names. Short aliases are allowed when useful, but
each alias is a support commitment.

## Public Wrapper Decision

Add `by_name` support only when the cipher should be part of the user-facing API.

Public wrapper work usually touches:

- `src/rune_decrypter_prime/api/wrappers/by_name.py`
- `src/rune_decrypter_prime/api/wrappers/registry.py`
- `v1_docs/coder/public_api.md`
- `v1_docs/reference/public_api_allowlist.md`

If the cipher is experimental, keep it out of the public wrapper and document it
as internal or experimental.

## Tests

At minimum, cover:

- encrypt/decrypt round trip where applicable
- batch decrypt shape
- key length validation
- keyops family compatibility
- `by_name` wrapper behavior if public
- deterministic behavior for the same input and key

Use focused tests near the changed package first. Add docs-contract tests only
when public docs or allowlists change.

## Do Not Do

- Do not copy assets into the release tree without asset approval.
- Do not make solver ranking depend on cipher diagnostics.
- Do not use absolute local paths.
- Do not add generated examples, logs, caches, or benchmark output.
