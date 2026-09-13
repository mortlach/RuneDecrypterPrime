# CUDA setup

RDP does not require CUDA. CPU is the default.

On a supported NVIDIA system, the source installer checks whether the installed
Torch build can already use CUDA. If it can, that setup is kept.

If a supported GPU is present but the working Torch CUDA build is missing, the
installer installs the pinned build used by RDP and checks it on the visible
devices.

If no NVIDIA GPU is present, installation continues normally on CPU.

For the normal installation route, see
[Installation](../setup/installation.md).

## Supported automatic setup

Automatic setup currently covers Windows and Linux on x86-64 with NVIDIA
compute capability 7.5 or newer.

The pinned V1 setup uses Torch 2.13.0, with CUDA 12.6 for GPUs below compute
capability 10.0 and CUDA 13.0 for compute capability 10.0 and newer.

The installer uses these minimum driver versions:

| CUDA | Windows | Linux |
| --- | --- | --- |
| 12.6 | 560.76 | 560.28.03 |
| 13.0 | 580 | 580 |

These are RDP installer limits, not a general CUDA compatibility table.

## Check CUDA

The dedicated validation program is:

```text
python tools/run_gpu_validation.py
```

This checks whether the CUDA runtime used by RDP is actually available.

## Use CUDA in a solve

CUDA is selected in the run:

```python
request = api.RunSpec(
    ...,
    compute_device=api.ComputeDevice.CUDA,
)
```

The library default is `ComputeDevice.CPU`.

See [CPU, CUDA and scoring](../setup/scorer_backend_selection.md) and
[RunSpec parameters](../reference/parameters/run_spec.md).

When comparing CPU and CUDA runs, keep the cryptanalytic choices fixed first.
[Repeating a run](../guides/reproducibility.md) describes the other state that
matters for a fair comparison.
