# api.experimental parameters

The experimental namespace defines typed two-input map ciphers and lookup
ciphers. These are explicitly outside the stable core cipher set.

## define_cipher_map

```python
api.experimental.define_cipher_map(
    function,
    alphabet_size=29,
    degeneracy=api.experimental.DegeneracyPolicy.FORBID,
    resolver=api.experimental.ResolverMode.FIRST,
    per_position_limit=29,
    resolver_limit=8193,
    name=None,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `function` | callable `(int, int) -> int` | **required** | Must pass the experimental map validator. |
| `alphabet_size` | `int` | `29` | At least `2`. |
| `degeneracy` | `DegeneracyPolicy` | `FORBID` | `ALLOW` or `FORBID`. |
| `resolver` | `ResolverMode` | `FIRST` | `EXPAND_BEAM` or `FIRST`. |
| `per_position_limit` | `int` | `29` | At least `1`. |
| `resolver_limit` | `int` | `8193` | At least `1`. |
| `name` | `str | None` | `None` | Non-empty when supplied. |

## define_cipher_lookup

```python
api.experimental.define_cipher_lookup(
    table,
    alphabet_size=29,
    degeneracy=api.experimental.DegeneracyPolicy.FORBID,
    resolver=api.experimental.ResolverMode.FIRST,
    per_position_limit=29,
    resolver_limit=8193,
    name=None,
)
```

The option parameters and defaults are the same as `define_cipher_map`.
`table` is the required lookup table and is validated against `alphabet_size`.

For practical use, see [Extending RDP](../../guides/extending_rdp.md).
