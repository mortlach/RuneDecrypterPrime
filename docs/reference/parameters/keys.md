# KeySpec parameters

## Repeating

```python
api.KeySpec.repeating(length=...)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `length` | `int` | **required** | At least `1`. |

## Variable-length repeating keys

V1 does not expose a variable-length repeating-key constructor. Vigenere and
Autokey require a fixed repeating-key length. Compare separate, explicitly
configured runs when testing different lengths. The serialized key-kind enum
retains its existing values, but `repeating_range` is not a supported public
constructor or parser route.

## Permutation

```python
api.KeySpec.permutation(length=...)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `length` | `int` | **required** | At least `1`. |

## Scalar

```python
api.KeySpec.scalar(
    minimum=...,
    maximum=...,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `minimum` | `int` | **required** | Not above `maximum`. |
| `maximum` | `int` | **required** | Not below `minimum`. |

## Periodic substitution

```python
api.KeySpec.periodic_substitution(
    period=...,
    alphabet_size=29,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `period` | `int` | **required** | At least `1`. |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Periodic columnar

```python
api.KeySpec.periodic_columnar(
    period=...,
    columns=...,
    alphabet_size=29,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `period` | `int` | **required** | At least `1`. |
| `columns` | `int` | **required** | At least `1`. |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Alignment

Repeating and repeating-range key spaces support alignment controls.

```python
key_space = key_space.with_fixed_alignment(
    offset=...,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `offset` | `int` | **required** | Available only for repeating key kinds. |

Or search an offset range:

```python
key_space = key_space.with_alignment_search(
    minimum_offset=...,
    maximum_offset=...,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `minimum_offset` | `int` | **required** | Not above `maximum_offset`. |
| `maximum_offset` | `int` | **required** | Not below `minimum_offset`. |

## Serialized construction

`KeySpec.from_name(name, parameters=None)` reconstructs a public key spec from
its serialized form, including supported alignment information.

For practical use, see [Keys and key spaces](../../guides/keyops.md).

See also [Parameter reference](README.md) and [Defaults at a glance](../defaults.md).

## Typed identity

`kind` identifies the selected KeySpec family. Constructor arguments are
exposed through its immutable `parameters` mapping. Use the typed constructors
for new requests and the existing parsers for serialized data.
