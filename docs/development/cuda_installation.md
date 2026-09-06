# CUDA provisioning

RDP runs on CPU by default. The source installer can also prepare and verify a
Torch CUDA runtime on a supported NVIDIA machine, but these are separate
decisions:

1. installation determines whether CUDA execution is available;
2. `RunSpec.compute_device` determines whether a particular run requests it.

Installing CUDA support does not silently move a run to the GPU. The public
default remains `api.ComputeDevice.CPU`; request `api.ComputeDevice.CUDA` when
GPU execution is wanted.

## What `install.py` does

`python install.py` first probes the current Torch installation. If CUDA
arithmetic already works, it reuses that installation. Otherwise, if
`nvidia-smi` reports supported NVIDIA hardware, the installer selects and
installs the matching pinned Torch CUDA wheel and verifies arithmetic on every
visible device.

If no NVIDIA GPU is detected, CUDA is reported as `not_selected` and the normal
installation continues. If NVIDIA hardware is detected but the driver query,
wheel selection, installation or arithmetic verification fails, installation
fails clearly and preserves the command logs.

Automatic provisioning currently supports Windows/Linux x86-64 with NVIDIA
compute capability 7.5 or newer. The current policy pins Torch 2.13.0 and
selects CUDA 12.6 below compute capability 10.0 or CUDA 13.0 for newer hardware.
The conservative driver floors are 560.76 on Windows and 560.28.03 on Linux for
CUDA 12.6, and 580 for CUDA 13.0.

Older architectures or otherwise unsupported combinations require a manually
selected compatible Torch build. An already working build is still verified and
reused.

The policy follows the official
[Torch wheels](https://pytorch.org/get-started/previous-versions/) and
[NVIDIA driver requirements](https://docs.nvidia.com/cuda/archive/12.6.0/cuda-toolkit-release-notes/index.html).
Torch supplies its CUDA runtime dependencies; RDP does not install a system
NVIDIA driver or development CUDA toolkit.

## Verify an existing installation

Run:

```text
python tools/run_gpu_validation.py
```

This requires CUDA, provisions it if necessary, verifies arithmetic on every
visible device, and runs the dedicated GPU validation selection. Missing GPU
execution cannot pass by being reported as a skipped test.

See [validation](../../tools/run_validation.md) for the wider validation
runner.

## Select CUDA in a run

Availability is not selection. A run requests CUDA explicitly:

```python
from rdp import api

request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=api.CipherSpec.vigenere(),
    key_space=api.KeySpec.repeating(length=3),
    solver=api.SolverSpec.beam_search(width=8, rounds=2, seed=7),
    compute_device=api.ComputeDevice.CUDA,
)
```

Backend choice is separate again; see
[scorer backend selection](../setup/scorer_backend_selection.md).

A plain `pip install` does not run RDP's hardware provisioning. Use
`python install.py` for the automatic source-install route, or manage the
compatible Torch installation yourself.
