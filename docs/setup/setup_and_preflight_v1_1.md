# Setup + Preflight (v1.1)

This is the shared operator runbook for community benchmark setup.

## Run

```bash
python install.py
```

Windows alternative:

```powershell
py -3.11 install.py
```

## What success looks like

`python install.py` should produce:

- `output/tools/benchmarks/community/setup_preflight/latest/setup_report.json`
- `output/tools/benchmarks/community/setup_preflight/latest/preflight_report.json`
- `output/tools/benchmarks/community/setup_preflight/latest/benchmark_ready.json`

During setup/preflight the pipeline now:

- recombines manifest-declared packed assets,
- rebuilds missing LM joint `.bin.zst` tables from local split `*_part*.npz` shards when present,
- verifies/builds `_fastlm`,
- verifies/builds `_hamming`.

## If setup fails

Share:

- `output/tools/benchmarks/community/setup_preflight/latest/setup.log`
- `output/tools/benchmarks/community/setup_preflight/latest/setup_report.json`
- `output/tools/benchmarks/community/setup_preflight/latest/preflight.log`
- `output/tools/benchmarks/community/setup_preflight/latest/preflight_report.json`

## Notes

- Use `--skip-fastlm-build` only for debugging.
- Benchmark submissions remain CPU-only for v1.1.
- Install validation workflow/checklist: `docs/setup/install_validation.md`.
