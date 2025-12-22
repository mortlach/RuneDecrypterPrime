rune_decrypter_prime/ciphers
============================

Concrete cipher implementations used by the solver. A cipher’s only job is to
map between ciphertext and plaintext given a fully-formed key; key generation,
mutation, and validation belong to the KeyOps layer.

Key files
---------
- `vigenere_cipher.py`, `substitution_cipher.py`, `columnar_transposition_cipher.py`,
  `railfence_cipher.py`, `autokey_cipher.py`, etc.: batch decrypt/encrypt implementations.
- `generic_map_cipher.py`: runtime for user-defined map/lookup specs coming from
  the API.
- `base_keyed_cipher.py`: shared helpers (`_as_u8`, dtype guards).
- `ciphers_pipeline.py`: mixin that handles text/key transposition stages and
  keeps public `encrypt()/decrypt()` signatures uniform.
- `registry.py`: lightweight decorator-based registry so Stage-2 can build
  ciphers by name.

Design notes
------------
- Every cipher exposes `keyops_family` (e.g., `"vector"` or `"perm"`) and a
  fixed `key_length`. `core.problem.DecryptionProblem` uses those to construct
  the correct KeyOps instance once.
- Batch-first: `_core_decrypt_batch(ct_tr, keys_tr)` must accept `[B, K]` keys
  and return `[B, L]` plaintexts. Single keys are promoted to batch size 1.
- Keep decrypt pure and deterministic. Assume keys are already normalised by
  KeyOps; avoid secret repairs inside the cipher itself.
- Register new ciphers via `@register_cipher("name")` so API wrappers and
  RunAPI can discover them automatically.
