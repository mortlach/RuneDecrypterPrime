# RDP Community Benchmark (v1.1)

This folder defines a small community benchmark campaign workflow for RuneDecrypterPrime (RDP).

Rollout checklist:
- `../../../COMMUNITY_TO_V1_TODO.md`

Key goals:
- Self-contained repo: benchmark assets are included in this repository as split parts.
- One setup/deploy step prepares a fresh clone for benchmarking (recombine assets, build required components, run preflight).
- CPU-only benchmark submissions (for comparability).
- Deterministic manifests, shards, and results (no environment variables).
- Compact outputs that are easy to share and collate (no SQL).

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
- Schemas:
  - `tools/benchmarks/community/schemas/manifest_schema_v1_1.json`
  - `tools/benchmarks/community/schemas/result_schema_v1_1.json`
- Profile catalogue: `tools/benchmarks/community/profile_catalog_v1_1.json`
- Example campaign configs:
  - `tools/benchmarks/community/examples/campaign_config_v1_1.json`
  - `tools/benchmarks/community/examples/canary_campaign_config_v1_1.json`
- Runner config template:
  - `tools/benchmarks/community/examples/runner_config_local.template.json`

## Important rules (summary)
- No environment variables for benchmark behaviour.
- CPU-only runs for v1.1.
- `_fastlm` required for v1.1 benchmark compliance.
- Every result row must include `status` AND `stop_reason`.
- Resume is the only allowed skip (and must be logged explicitly).
