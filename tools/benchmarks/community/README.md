# RDP Community Benchmark (v1.1)

This folder defines the community benchmark workflow for Rune Decrypter Prime.

## Core goals

- One setup command for fresh clones.
- CPU-only benchmark submissions.
- Deterministic manifests, shards, and result rows.
- Tamper-evident result bundles (row hash-chain validation).
- Compact shareable run bundles.
- Clear tuning layer under `config/`.

## Contributor flow

1. Check out the campaign git SHA.
2. Run setup and preflight:
   - `python install.py`
3. Optionally run install smoke:
   - `python tools/ci/install_smoke.py`
4. Generate manifest and shard files.
5. Run assigned shard and share the produced `run_bundle`.

Run bundles now include:
- `results.jsonl`
- `results_integrity.jsonl`
- `run_meta.json` integrity summary block (`results_integrity`)

Setup artefacts are written to:

- `output/tools/benchmarks/community/setup_preflight/latest/`

## Files of record

- Setup runbook: `docs/setup/setup_and_preflight_v1_1.md`
- Tuning config docs: `tools/benchmarks/community/config/README.md`
- Manifest schema: `tools/benchmarks/community/schemas/manifest_schema_v1_1.json`
- Result schema: `tools/benchmarks/community/schemas/result_schema_v1_1.json`
- Profile catalog: `tools/benchmarks/community/profile_catalog_v1_1.json`

## Deterministic manifest + sharding

Generate manifest:

```powershell
python tools/benchmarks/community/generate_manifest.py `
  --campaign-config tools/benchmarks/community/examples/campaign_config_v1_1.json `
  --profile-catalog tools/benchmarks/community/profile_catalog_v1_1.json `
  --output output/tools/benchmarks/community/manifest.jsonl
```

Shard manifest:

```powershell
python tools/benchmarks/community/shard_manifest.py `
  --manifest output/tools/benchmarks/community/manifest.jsonl `
  --output-dir output/tools/benchmarks/community/shards `
  --num-shards 4
```

## Guides

- `tools/benchmarks/community/README_runner.md`
- `tools/benchmarks/community/README_canary.md`
- `tools/benchmarks/community/README_organiser.md`
