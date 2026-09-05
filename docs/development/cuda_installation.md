# Automatic CUDA installation

`python install.py` installs the normal package and full language assets. It
also reuses a working Torch CUDA runtime or provisions one when `nvidia-smi`
detects NVIDIA hardware. CPU-only Torch is replaced on a supported GPU machine.
A missing GPU is reported as `not_selected`; it is never reported as GPU verified.
A failed NVIDIA query, incompatible driver, unavailable wheel or failed CUDA
arithmetic blocks installation with command logs preserved.

Automatic wheel selection currently supports Windows/Linux x86-64 with NVIDIA
compute capability 7.5 or newer. It selects Torch 2.13.0 with CUDA 12.6 for
capabilities below 10.0, or CUDA 13.0 for newer hardware. Conservative driver
floors are 560.76 on Windows and 560.28.03 on Linux for CUDA 12.6, and 580 for
CUDA 13.0. Older architectures need a manually selected compatible build; an
already working build is verified and reused. Wheel availability also depends
on the Python version. Unsupported combinations fail clearly.

This policy uses [official Torch wheels](https://pytorch.org/get-started/previous-versions/)
and [NVIDIA's driver requirements](https://docs.nvidia.com/cuda/archive/12.6.0/cuda-toolkit-release-notes/index.html).
Torch supplies its CUDA runtime dependencies; the installer does not install
system drivers or a development CUDA toolkit. It does not change a solver's
requested CPU/GPU setting.

For an existing source installation, run:

```text
python tools/run_gpu_validation.py
```

This provisions and verifies GPU arithmetic, then runs the dedicated test
selection. Every visible CUDA device must pass the arithmetic probe. JUnit
skips make this verification fail, so missing GPU execution cannot look like a
pass. See [validation](../../tools/run_validation.md) for its scope and evidence.

A plain `pip install` does not execute hardware provisioning. The optional
`torch` extra remains available for manual installations. Use `install.py` for
the automatic source-install route.
