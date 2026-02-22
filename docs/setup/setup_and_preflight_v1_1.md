# Setup + Preflight (v1.1)

This document defines the required setup/deploy and preflight behaviour for the community benchmark campaign.

## Goal
After a fresh clone, a contributor runs one setup/deploy step that:
- recombines assets from `assets_packed/` into `assets/`
- builds/verifies `_fastlm` (required for v1.1 compliance)
- runs preflight checks
- writes clear logs and reports
- writes a success marker only when fully ready

## Inputs (tracked)
- `assets_manifest_v1.json` at repo root (defines which packed parts form each final asset file)
- pinned dependency definition for benchmark CPU v1.1 (format decided by the project)
- community benchmark spec: `tools/benchmarks/community/campaign_spec_v1_1.md`

## Temporary Bridge Mode (current repo)
For the current transition branch, `assets_manifest_v1.json` may define `forward_links` so setup creates:
- `assets/language_model/lmp` -> `src/rune_decrypter_prime/data/language_model/lmp`

This keeps campaign paths stable while data move/packing is staged.

## Outputs
Setup must write:
- run directory under:
  - `output/tools/benchmarks/community/setup_preflight/<timestamp>__setup_preflight*/`
- and refresh latest pointer directory:
  - `output/tools/benchmarks/community/setup_preflight/latest/`
  - contains `setup.log`, `setup_report.json`, `preflight.log`, `preflight_report.json`, `benchmark_ready.json` (success marker only)

## What preflight must confirm
1) Required imports succeed (RDP core + scoring + benchmark pipeline entrypoints).
2) Required assets exist under `assets/` and match expected size/hash.
3) `_fastlm` import works and is usable for CPU scoring.
4) A tiny CPU scoring call succeeds (char + WLI 3/4-gram path available).
5) The report clearly states CPU-only compliance fields:
   - device = cpu
   - scoring_backend = numpy
   - fastlm_present = true

## Clean-room rules
- Recombine and build steps must be atomic (temp -> verify -> rename).
- Setup must be idempotent and safe to rerun.
- No half-built artefacts left behind in final locations.

## If setup or preflight fails
Contributors should share:
- `output/tools/benchmarks/community/setup_preflight/latest/setup_report.json` + `setup.log`
- `output/tools/benchmarks/community/setup_preflight/latest/preflight_report.json` + `preflight.log`
