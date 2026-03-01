# Rune Decrypter Prime

Rune Decrypter Prime (RDP) is a deterministic cryptanalysis toolkit focused on a 29-rune alphabet.
The repository now treats the community benchmark flow as a first-class path, with one cross-platform
bootstrap entrypoint.

## Quick Start (Community Benchmark)

Use one command from repo root:

```bash
python install.py
```

Windows (if `python` alias is unavailable):

```powershell
py -3.11 install.py
```

What this does:

1. Creates/uses a local virtual environment.
2. Installs target-specific dependencies.
3. Installs the repo in editable mode.
4. Runs setup + preflight:
   - recombine manifest assets from `assets_packed/` into `assets/`
   - rebuild missing split LM joint tables (`*_part*.npz` -> `.bin.zst`) when available
   - build/verify `_fastlm`
   - build/verify `_hamming`
   - run CPU preflight checks
   - write `benchmark_ready.json` on success

Output artefacts:

- `output/tools/benchmarks/community/setup_preflight/latest/`

Optional: run install smoke immediately after setup.

```bash
python tools/ci/install_smoke.py
```

## Install Targets

- `runner`: run community benchmark shards.
- `organiser`: validate/combine/aggregate run bundles.
- `dev`: local development (tests/lint/hooks).
- `ci-smoke`: minimal CI smoke stack.

Target requirement files live under `requirements/targets/`.

## Wrapper Scripts

Use any of the thin wrappers if preferred:

- `install.ps1`
- `install.sh`
- `install.bat`

Each wrapper launches `install.py` for your platform.

## Clean Install Smoke (VM/CI)

For a no-argument, fresh-environment validation run:

```bash
python tools/ci/install_smoke.py
```

This runs the bootstrap install and verifies the expected setup/preflight artefacts and ready markers.

## Community Benchmark Flow

Primary docs:

- `tools/benchmarks/community/README.md`
- `docs/setup/setup_and_preflight_v1_1.md`
- `docs/setup/installation.md`

High-level flow:

1. `python install.py`
2. Generate manifest + shards.
3. Run assigned shard.
4. Share `run_bundle`.
5. Organiser validates, combines, and aggregates.

## Development Notes

- Python: 3.11+
- Determinism is required for benchmark mode.
- CPU-only scoring is required for v1.1 campaign compliance.
- `setup_report.json` and `preflight_report.json` are the source of truth for install readiness.

## License

MIT (see `LICENSE_MIT.txt`).
