# Add a Cipher

Status: implemented V1 boundary

Owner paths:

- `src/rune_decrypter_prime/ciphers/`
- `src/rune_decrypter_prime/ciphers/cipher_runtime_registry.py`
- `src/rdp/api/experimental.py`
- `tests/`

## Goal

Choose the correct extension boundary and add a tested cipher without creating
a public runtime-object API or an alias.

## Steps

1. For a two-input experimental function or lookup table, use
   `api.experimental.define_cipher_map` or `define_cipher_lookup` and add an
   experimental tutorial/test.
2. For an engine cipher, implement the runtime under
   `src/rune_decrypter_prime/ciphers/` and register its one canonical
   snake-case identity with the exact runtime registry.
3. Define key length, semantic concrete-key layout, compatible key-space kind,
   conflict validation, encrypt/decrypt validation, and replay identity.
4. Reuse existing key operations and materialization owners.
5. Promotion into the 141-path V1 contract requires an explicit later public
   contract decision; do not create a convenience wrapper meanwhile.

Experimental example:

```python
from rdp import api

def add_modulo(plaintext: int, key: int) -> int:
    return (plaintext + key) % 29

cipher = api.experimental.define_cipher_map(
    add_modulo,
    name="add_modulo",
    alphabet_size=29,
)
```

## Tests

Cover typed definition validation, concrete-key validation, known-key vectors,
round trips where invertible, runtime identity, replay identity, and duplicate
registration failure. Add tutorial tests if the extension is taught publicly.

## Do Not Do

- Do not add a generic internal or public facade.
- Do not add forwarding imports, aliases, automatic fallbacks, or a runtime
  cipher-returning helper.
- Do not pass offset-encoded keys across the public boundary.
- Do not make diagnostic signals affect ranking.
- Do not add generated outputs or local assets to the repository.
