# InterruptorConfig parameters

`RunSpec.interruptors` defaults to `None`.

## Disabled

```python
api.InterruptorConfig.disabled()
```

No parameters.

## Exact positions

```python
api.InterruptorConfig.exact(positions)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `positions` | sequence of `int` | **required** | Non-empty, unique, non-negative positions. |

Positions are stored in sorted order.

## Search positions

```python
api.InterruptorConfig.search(
    candidate_positions,
    minimum_count=0,
    maximum_count=None,
    strategy=api.advanced.InterruptorSearchStrategy.AUTO,
    maximum_combinations=5000,
)
```

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `candidate_positions` | sequence of `int` | **required** | Non-empty, unique, non-negative positions. |
| `minimum_count` | `int` | `0` | At least `0`. |
| `maximum_count` | `int | None` | `None` | `None` means all candidate positions. Cannot exceed candidate count. |
| `strategy` | `InterruptorSearchStrategy` | `AUTO` | `AUTO`, `BRUTE_FORCE`, or `KEY_OPERATIONS`. |
| `maximum_combinations` | `int` | `5000` | At least `1`. |

`minimum_count` must not exceed the effective maximum count.

## Serialized construction

`InterruptorConfig.from_dict(values)` accepts serialized `mode` and
`parameters` fields for the three modes above.

For practical use, see [Interruptors](../../guides/interruptors.md).

See also [Parameter reference](README.md) and [Defaults at a glance](../defaults.md).
