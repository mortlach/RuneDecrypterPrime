# Installation

This repo uses one cross-platform bootstrap entrypoint:

```bash
python install.py --target runner
```

Windows alternative:

```powershell
py -3.11 install.py --target runner
```

The bootstrap script handles:

1. Virtual environment creation/use.
2. Target dependency installation.
3. Editable package install (`pip install -e .`).
4. Setup + preflight for community benchmark readiness.

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

### Runner node

```bash
python install.py --target runner
```

### Organiser node

```bash
python install.py --target organiser
```

### Development environment

```bash
python install.py --target dev
```

### Run canary after setup/preflight

```bash
python install.py --target runner --run-canary
```

## Optional Flags

- `--no-venv`: use current interpreter directly.
- `--venv .venv_custom`: set venv location.
- `--recreate-venv`: recreate environment from scratch.
- `--skip-fastlm-build`: verify `_fastlm` import only.
- `--skip-preflight`: skip setup/preflight (not recommended for benchmark work).
- `--requirements <path>`: use custom requirements file.

See full options:

```bash
python install.py --help
```

## Verify Installation

1. Check setup artefacts:
   - `output/tools/benchmarks/community/setup_preflight/latest/setup_report.json`
   - `output/tools/benchmarks/community/setup_preflight/latest/preflight_report.json`
   - `output/tools/benchmarks/community/setup_preflight/latest/benchmark_ready.json`
2. Run a quick tutorial if desired:
   - `python tutorials/v1/Start_Here.py`

## Notes

- Community benchmark v1.1 is CPU-only.
- Benchmark behaviour must not depend on environment variables.
- Use setup/preflight logs for troubleshooting when sharing failures.
