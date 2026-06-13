# Installation

This repo uses one cross-platform bootstrap entrypoint:

```bash
python install.py
```

Windows alternative:

```powershell
py -3.11 install.py
```

The bootstrap script handles:

1. Virtual environment creation/use.
2. Target dependency installation.
3. Editable package install (`pip install -e .`).
4. Setup + preflight for community benchmark readiness:
   - recombine packed assets,
   - rebuild missing split LM joint tables (`*_part*.npz` -> `.bin.zst`) when needed,
   - verify/build native extensions (`_fastlm`, `_hamming`).

## Prerequisites

1. Python 3.11 (64-bit).
2. Git (recommended).
3. C/C++ build tools if `_fastlm` must be rebuilt locally.

## Install Targets

- `runner`: run community benchmark shards.
- `organiser`: validate/combine/aggregate shared run bundles.
- `dev`: local development (tests/lint/hooks).
- `ci-smoke`: minimal smoke test stack.

Dependency files:

- `requirements/targets/runner.txt`
- `requirements/targets/organiser.txt`
- `requirements/targets/dev.txt`
- `requirements/targets/ci-smoke.txt`

## Typical Commands

### Runner node (default)

```bash
python install.py
```

Use this as the canonical operator path for clean-machine installs.

## Verify Installation

1. Check setup artefacts:
   - `output/tools/benchmarks/community/setup_preflight/latest/setup_report.json`
   - `output/tools/benchmarks/community/setup_preflight/latest/preflight_report.json`
   - `output/tools/benchmarks/community/setup_preflight/latest/benchmark_ready.json`
2. Run a quick tutorial if desired:
   - `python tutorials/v1/Start_Here.py`

## Clean VM / CI Smoke Validation

Use the no-argument smoke runner:

```bash
python tools/ci/install_smoke.py
```

What it verifies:

1. Bootstrap install succeeds from a clean environment.
2. Setup/preflight artefacts exist under `output/tools/benchmarks/community/setup_preflight/latest/`.
3. `benchmark_ready.json` reports `ready=true`.
4. `preflight_report.json` reports `success=true`.

GitHub workflow:

- `.github/workflows/install-smoke.yml` (manual `workflow_dispatch`, Windows + Ubuntu fresh runners).

## Notes

- Community benchmark v1.1 is CPU-only.
- Benchmark behaviour must not depend on environment variables.
- Use setup/preflight logs for troubleshooting when sharing failures.
- Scorer/backend routing and expected failures are documented in `docs/setup/scorer_backend_selection.md`.
