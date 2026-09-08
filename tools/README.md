# Repository tools

`tools/` contains repository utilities rather than installed public API.

## Validation

`run_validation.py` is the main repository validation entry point. It can run
ordinary tests, tutorials/examples and solved-LP workbook checks from one
place.

Visible-terminal launchers and their output-mirroring instructions are kept in
[`validation/`](validation/README.md). Generated evidence belongs outside the
repository.

Use the smallest selection that answers the current question.

CUDA provisioning has its own check:

```text
python tools/run_gpu_validation.py
```

See [CUDA setup](../docs/development/cuda_installation.md).

## Main tool areas

- `assets/` prepares and checks asset profiles and bundles
- `ci/` contains installed-package and CI checks
- `data/` prepares retained corpus/data fixtures
- `get_src_zip/` prepares source archives
- `robustness/` runs explicit multi-case campaigns

Release and fixture-maintenance utilities also live here when they are
repository-only operations.

## Robustness

Robustness tools are kept separate from ordinary tutorials and focused tests.

See [Robustness campaigns](robustness/README.md).

For the wider development path, see [Development](../docs/development/README.md).
