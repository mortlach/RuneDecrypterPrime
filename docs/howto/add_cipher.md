# Add a cipher

There are two common extension jobs in RDP:

1. add a cipher relation
2. define or select the key operations that let solvers search its key

They should be designed together.

For the runtime architecture, read
[Cipher runtime and registration](../architecture/cipher_runtime_and_registration.md)
and [Key models and search operations](../architecture/key_model_and_search.md).

## 1. Decide whether this needs a production cipher

For a small two-input map or lookup experiment, use the public experimental
route first:

```python
api.experimental.define_cipher_map(...)
api.experimental.define_cipher_lookup(...)
```

This reuses the generic-map runtime and the same search/scoring path.

A production cipher family is appropriate when the behaviour has a stable
identity, key model and testable runtime contract.

## 2. Define the cipher relation and key layout

Before registration, specify:

```text
plaintext -> ciphertext relation
concrete key layout
valid key domain
key length or dimensions
whether encrypt and decrypt are both defined
position, direction or schedule conventions
```

Then choose the KeyOps family that matches the real key structure.

See [Build key operations](build_keyops.md).

## 3. Implement the runtime owner

Production cipher code belongs under:

```text
src/rdp/ciphers/
```

The runtime cipher performs the actual transform for concrete keys.

Candidate generation belongs to KeyOps.

Search belongs to solvers.

Scoring belongs to the scorer.

Keeping those responsibilities separate is what allows the new cipher to reuse
the rest of RDP.

## 4. Register the runtime identity

The runtime registry maps a canonical identity to its implementation class.

Contributor code uses the existing registry rather than adding another
selection mechanism.

A duplicate identity is an error.

Runtime registration is only the internal implementation binding. It does not
automatically create a public `CipherSpec`.

## 5. Add the typed public binding

A supported public family normally needs:

- a `CipherKind`
- a `CipherSpec` constructor and serialization path
- a compatible `KeySpec`
- cipher/key compatibility validation
- concrete-key validation
- runtime materialisation for cipher-specific parameters and KeyOps hints
- known-key encrypt/decrypt support when applicable
- public result/contract tests
- parameter documentation and at least one appropriate example

A public cipher therefore needs more than a registry entry.

## 6. Test known-key behaviour first

Where the cipher is invertible, test:

```text
plaintext
-> encrypt with known key
-> ciphertext
-> decrypt with same key
-> original plaintext
```

Also test invalid keys and incompatible key spaces.

This checks cipher correctness before a solver is involved.

See [Known-key encrypt and decrypt](../reference/known_key.md).

## 7. Test solver integration

Once known-key behaviour is correct, run a small deterministic recovery problem.

Then check the integrated path:

```text
CipherSpec + KeySpec
-> runtime cipher + KeyOps
-> solver
-> scorer
-> recovered result
```

Use a fixed seed and a small enough case to remain a focused test.

Longer robustness work belongs later.

## 8. Move to wider evidence only when needed

A smoke solve shows the integrated path works.

A robustness or qualification campaign tests a wider scientific claim.

Keep those jobs separate.

See [Cipher development](../development/cipher_development.md) and
[Extending RDP](../guides/extending_rdp.md).
