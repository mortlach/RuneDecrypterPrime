# `ciphers/vigenere_cipher.py`

> Purpose: production Vigenère cipher implementation (mod 29) with optional Torch acceleration. Registered under `"vigenere"`/`"vig"` so `by_name` can materialise it.

## Helper Functions
- `_str_has_digits`, `_parse_int_tokens`, `_letters_to_indices` - Parse user keys provided as strings/numbers.
- `_to_key_u8(key)` - Normalises keys into `np.uint8` arrays modulo 29.
- `encrypt(pt, key)` - Convenience helper for tests (operates on index arrays).

## `RuneVigenereCipher`
- Inherits from `CipherPipelineMixin` and `KeyedCipherBase`.
- Supports both NumPy and Torch backends (`select_backend` chooses based on device).
- Implements `_core_encrypt_batch` / `_core_decrypt_batch` for vectorised operations, respecting direction and key transposition metadata.

## Tests
- `tests/ciphers/test_columnar_device_parity.py` and GA/SA tutorial regressions call this cipher via `by_name`, verifying both CPU and CUDA paths.
- Fast-path encryption (`encrypt`) is used in cipher-specific unit tests.

## Related Docs
- `docs/reference/api/wrappers/by_name.md` - explains how Hands-on users request this cipher.
- `docs/howto/add_cipher.md` - describes the promotion path for additional ciphers.

