# Cipher runtime and registration

A public `CipherSpec` and a runtime cipher class are different layers.

`CipherSpec` describes the cipher family and durable parameters.

The runtime class performs the transform for concrete keys.

## Public cipher

Normal callers use:

```python
cipher = api.CipherSpec.vigenere()
```

See [Cipher parameters](../reference/parameters/ciphers.md).

## Cipher and key binding

The cipher and `KeySpec` are validated together.

Current V1 bindings include:

| Cipher | Key model |
| --- | --- |
| Vigenere | repeating |
| Autokey | repeating |
| columnar | permutation matching column count |
| rail fence | scalar bounds matching rail bounds |
| substitution | permutation matching alphabet size |
| periodic substitution | structured periodic key |
| periodic columnar | structured periodic-columnar key |
| scheduled/two-period stream families | derived fixed-length repeating key |
| experimental map/lookup | repeating |

The binding also determines the flattened concrete-key length.

See [Key models and search operations](key_model_and_search.md).

## Runtime materialisation

The public request is converted into `CipherConfig`.

That step resolves the runtime identity, key length, KeyOps family, KeyOps
hints, device, direction, interruptors, initial keys and any cipher-specific
parameters.

`CipherConfig` is the runtime form of the public request, not a second public
configuration surface.

## Registry

`build_cipher(...)` resolves the runtime identity through the cipher registry.

Current identities include:

```text
vigenere
autokey
columnar
rail_fence
substitution
periodic_substitution
periodic_columnar
scheduled_stream_lookup
generic_map
```

Registration is strict. Duplicate identities fail.

## Experimental route

Small two-input maps and lookup-table ciphers can use:

```python
api.experimental.define_cipher_map(...)
api.experimental.define_cipher_lookup(...)
```

These reuse the normal run, KeyOps and scoring machinery.

See [Experimental ciphers](../reference/experimental.md).

## Production cipher

A production family normally needs:

1. cipher relation and concrete key layout
2. compatible KeyOps
3. runtime implementation under `src/rdp/ciphers/`
4. runtime registration
5. public `CipherKind` and `CipherSpec` binding when intended
6. cipher/key compatibility and concrete-key validation
7. known-key support where the family is invertible
8. focused tests
9. public parameter documentation and an example where useful

Runtime registration alone does not create a public cipher.

See [Add a cipher](../howto/add_cipher.md).
