# CipherSpec parameters

All public cipher constructors return an immutable `CipherSpec`.

## Vigenere

```python
api.CipherSpec.vigenere(alphabet_size=29)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Autokey

```python
api.CipherSpec.autokey(alphabet_size=29)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Columnar

```python
api.CipherSpec.columnar(columns=..., alphabet_size=29)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `columns` | `int` | **required** | At least `1`. |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Rail fence

```python
api.CipherSpec.rail_fence(
    minimum_rails=2,
    maximum_rails=8,
    alphabet_size=29,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `minimum_rails` | `int` | `2` | At least `2`. |
| `maximum_rails` | `int` | `8` | At least `2` and not below `minimum_rails`. |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Substitution

```python
api.CipherSpec.substitution(alphabet_size=29)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Periodic substitution

```python
api.CipherSpec.periodic_substitution(
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
api.CipherSpec.periodic_columnar(
    period=...,
    columns=...,
    order=api.advanced.PeriodicColumnarOrder.SUBSTITUTION_THEN_COLUMNAR,
    alphabet_size=29,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `period` | `int` | **required** | At least `1`. |
| `columns` | `int` | **required** | At least `1`. |
| `order` | `PeriodicColumnarOrder` | `SUBSTITUTION_THEN_COLUMNAR` | See [Common enums](enums.md). |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Two-period Vigenere

```python
api.CipherSpec.two_period_vigenere(
    first_period=13,
    second_period=31,
    schedule=api.advanced.ScheduledStreamSchedule.OVERLAY,
    mask=None,
    alphabet_size=29,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `first_period` | `int` | `13` | At least `1`. |
| `second_period` | `int` | `31` | At least `1`. |
| `schedule` | `ScheduledStreamSchedule` | `OVERLAY` | `OVERLAY`, `ALTERNATING`, or `MASK`. |
| `mask` | sequence of `int` or `None` | `None` | Required only for `MASK`. Values are `0..3`. |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Periodic with fixed stream

```python
api.CipherSpec.periodic_with_fixed_stream(
    fixed_stream,
    period=13,
    alphabet_size=29,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `fixed_stream` | sequence of `int` | **required** | Non-empty. Values must fit the alphabet. |
| `period` | `int` | `13` | At least `1`. |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Periodic with prime stream

```python
api.CipherSpec.periodic_with_prime_stream(
    period=13,
    prime_offset=0,
    alphabet_size=29,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `period` | `int` | `13` | At least `1`. |
| `prime_offset` | `int` | `0` | At least `0`. |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Two-period streams

```python
api.CipherSpec.two_period_streams(
    first_period=13,
    second_period=31,
    operation=api.advanced.ScheduledStreamOperation.ADD,
    schedule=api.advanced.ScheduledStreamSchedule.OVERLAY,
    mask=None,
    alphabet_size=29,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `first_period` | `int` | `13` | At least `1`. |
| `second_period` | `int` | `31` | At least `1`. |
| `operation` | `ScheduledStreamOperation` | `ADD` | See [Common enums](enums.md). |
| `schedule` | `ScheduledStreamSchedule` | `OVERLAY` | `OVERLAY`, `ALTERNATING`, or `MASK`. |
| `mask` | sequence of `int` or `None` | `None` | Required only for `MASK`. Values are `0..3`. |
| `alphabet_size` | `int` | `29` | At least `2`. |

## Serialized construction

`CipherSpec.from_name(name, parameters=None)` reconstructs one of the public
cipher specs from its serialized name and parameter mapping. Unsupported names
or parameter sets raise the public component/configuration errors.

For practical use, see [Defining a run](../../guides/anatomy_of_a_run.md).

## Typed identity

`kind` identifies the selected CipherSpec family. Constructor arguments are
exposed through its immutable `parameters` mapping. Use the typed constructors
for new requests and the existing parsers for serialized data.
