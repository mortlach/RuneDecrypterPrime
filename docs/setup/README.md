# Installation and runtime setup

Start with [installation](installation.md). It covers the supported Python
version, the normal source-install route, full assets and the first runnable
proof.

Use the other pages when the question is more specific:

- [Scorer backend selection](scorer_backend_selection.md) — choose CPU/CUDA and
  the scoring backend without confusing availability with selection.
- [Install validation](install_validation.md) — CI-light, full release proof and
  the boundary between ordinary validation and long qualification work.
- [Build and packaging notes](building.md) — manual wheel and native-extension
  packaging checks.
- [CUDA provisioning](../development/cuda_installation.md) — how the source
  installer detects, provisions and verifies supported NVIDIA hardware.
- [Outputs and artefacts](../guides/outputs.md) — what `api.run` returns, when a
  run writes files, and where those files go.

Once the installation is working, continue with the
[quickstart](../guides/quickstart.md).
