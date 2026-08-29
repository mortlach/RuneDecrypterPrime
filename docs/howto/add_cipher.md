# Add a cipher

Audience: contributors

1. Prototype in the cipher-development workspace.
2. Implement or repair the exact runtime cipher owner under
   `src/rune_decrypter_prime/ciphers/`.
3. Define the semantic concrete-key layout and compatible key-space operations.
4. Register the implementation with its existing runtime registry.
5. Add round-trip, invalid-key, device-parity and solver integration tests as
   appropriate.
6. If the family is approved for V1, add or update its typed
   `api.CipherSpec`/`api.KeySpec` constructors and public contract tests.

Normal public examples use `from rdp import api`. Experimental map tutorials use
`api.experimental.define_cipher_map`. Contributor-only internals import their
exact owning modules; they are never routed through another facade.

Do not add a name alias, compatibility wrapper, generic transform or public
runtime cipher object.
