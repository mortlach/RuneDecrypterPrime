# CPU, CUDA and scoring

RDP separates two choices:

- the device used by the run
- the scoring backend used to calculate scores

They are related execution choices, but they are not the same setting.

## Compute device

CPU is the default:

```python
request = api.RunSpec(
    ...,
    compute_device=api.ComputeDevice.CPU,
)
```

To use CUDA on a supported machine:

```python
request = api.RunSpec(
    ...,
    compute_device=api.ComputeDevice.CUDA,
)
```

See [CUDA setup](../development/cuda_installation.md).

## Scoring backend

`ScoringConfig.backend` defaults to automatic selection.

For most runs, leave the scoring backend at its default and change the device
only when the run requires a different choice.

See [Scoring](../guides/scoring.md) and
[Scoring parameters](../reference/parameters/scoring.md).

## Comparing execution choices

When measuring CPU against CUDA, or one backend against another, keep the
cipher, key space, solver and scoring evidence fixed first.

That makes it possible to separate execution performance from a change in the
cryptanalytic method.

See [Repeating a run](../guides/reproducibility.md) and
[Telemetry](../guides/telemetry.md).
