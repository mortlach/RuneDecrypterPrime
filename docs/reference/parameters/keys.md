# KeySpec parameters

## Repeating

```python
api.KeySpec.repeating(length=...)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `length` | `int` | **required** | At least `1`. |

## Repeating range

```python
api.KeySpec.repeating_range(
    minimum_length=...,
    maximum_length=...,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `minimum_length` | `int` | **required** | At least `1`. |
| `maximum_length` | `int` | **required** | At least `1` and not below `minimum_length`. |

### Current V1 binding note

The constructor is part of the typed spec layer, but the current V1
cipher/key materialisation requires fixed `repeating` keys for the existing
Vigenere and Autokey solve bindings. Treat `repeating_range` as unbound for
ordinary V1 solves until a variable-length runtime binding is added.

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
