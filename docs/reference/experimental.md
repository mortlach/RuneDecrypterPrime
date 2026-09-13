# Experimental ciphers

`api.experimental` contains typed experimental map and lookup cipher
definitions.

It is separate from the stable built-in `CipherSpec` families.

Two constructors are public:

```python
api.experimental.define_cipher_map(...)
api.experimental.define_cipher_lookup(...)
```

Both return a `CipherSpec` that can be used by the normal run machinery.

## Map example

A small two-input relation can be defined as a Python function:

```python
def relation(plain, key):
    return (plain + key) % 29

cipher = api.experimental.define_cipher_map(
    relation,
)
```

The returned `cipher` can then be used with the ordinary `RunSpec`, key space,
solver and scoring components.

This makes the experiment unusual without making the execution path unusual.

## Lookup example

A prepared lookup table can be exposed in the same way:

```python
cipher = api.experimental.define_cipher_lookup(
    table,
)
```

The namespace also exports `DegeneracyPolicy` and `ResolverMode`.

The complete options and defaults are listed in
[Experimental parameters](parameters/experimental.md).

For deciding when an experiment should become a production cipher, see
[Extending RDP](../guides/extending_rdp.md),
[Cipher development](../development/cipher_development.md) and
[Add a cipher](../howto/add_cipher.md).
