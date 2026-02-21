# RDP Community Benchmark (v1.1)

This folder defines a small community benchmark campaign workflow for RuneDecrypterPrime (RDP).

Key goals:
- Self-contained repo: benchmark assets are included in this repository as split parts.
- One setup/deploy step prepares a fresh clone for benchmarking (recombine assets, build required components, run preflight).
- CPU-only benchmark submissions (for comparability).
- Deterministic manifests, shards, and results (no environment variables).
- Compact outputs that are easy to share and collate (no SQL).
- Clear, human-facing tuning layer (`config/`) separated from runner and pipeline execution logic.

## What contributors do (the “clear flow”)

1) Download / checkout the repo at the campaign git SHA.

2) Run the setup/deploy step:
   - Recombine split assets from `assets_packed/` into `assets/`
   - Build/verify `_fastlm` (required for v1.1 benchmark compliance)
   - Run preflight and produce a report
   - Write a `benchmark_ready.json` marker only if everything succeeded

   See: `docs/setup/setup_and_preflight_v1_1.md`

3) Run the canary campaign first (recommended):
   - A tiny end-to-end run (minutes) to catch setup problems early
   See: `tools/benchmarks/community/README_canary.md`

4) Run your assigned shard:
   - Use the simple runner config template
   - The runner will resume safely and will not silently autoskip jobs
   See: `tools/benchmarks/community/README_runner.md`

5) Share the output `run_bundle/` folder (zip it if needed).
   - Organisers validate bundles, combine results, and generate summary tables + heatmaps.
   See: `tools/benchmarks/community/README_organiser.md`

## Files of record (v1.1)
- Spec: `tools/benchmarks/community/campaign_spec_v1_1.md`
- Tuning layer:
  - `tools/benchmarks/community/config/README.md`
  - `tools/benchmarks/community/config/ranges_v1_1.json`
  - `tools/benchmarks/community/config/knob_reference_v1_1.md`
  - `tools/benchmarks/community/config/profile_config.py`
  - `tools/benchmarks/community/config/sampler.py`
- Schemas:
  - `tools/benchmarks/community/schemas/manifest_schema_v1_1.json`
  - `tools/benchmarks/community/schemas/result_schema_v1_1.json`
- Profile catalogue: `tools/benchmarks/community/profile_catalog_v1_1.json`
- Example campaign configs:
  - `tools/benchmarks/community/examples/campaign_config_v1_1.json`
  - `tools/benchmarks/community/examples/canary_campaign_config_v1_1.json`
- Runner config template:
  - `tools/benchmarks/community/examples/runner_config_local.template.json`

## Deterministic manifest + sharding
Generate a campaign manifest:

```powershell
python tools/benchmarks/community/generate_manifest.py `
  --campaign-config tools/benchmarks/community/examples/campaign_config_v1_1.json `
  --profile-catalog tools/benchmarks/community/profile_catalog_v1_1.json `
  --output output/tools/benchmarks/community/manifest.jsonl
```

Split that manifest into deterministic shards:

```powershell
python tools/benchmarks/community/shard_manifest.py `
  --manifest output/tools/benchmarks/community/manifest.jsonl `
  --output-dir output/tools/benchmarks/community/shards `
  --num-shards 4
```

## Important rules (summary)
- No environment variables for benchmark behaviour.
- CPU-only runs for v1.1.
- `_fastlm` required for v1.1 benchmark compliance.
- Every result row must include `status` AND `stop_reason`.
- Resume is the only allowed skip (and must be logged explicitly).
