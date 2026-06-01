# Setup and Preflight Spec (v1.1)

Status: Active implementation contract.

Companion docs:

- campaign contract: `10_contracts/campaign_spec_v1_1.md`
- execution plan: `20_active_plans/community_benchmark_unified_plan_v1_1.md`
- scoring gates: `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`

## Progress Update (2026-02-25)

Setup/preflight contract remains unchanged in this runner-harmonization wave.

Related implementation progress:

- periodic benchmark runners now share common output snapshot writing and flavor-scoped output roots, which reduces integration ambiguity after successful setup/preflight.

No changes to required setup/preflight files, ready-marker rules, or compliance checks in this update.

## Goal

For a fresh clone, one setup flow must:

1. install pinned benchmark dependencies
2. recombine assets from `assets_packed/` into `assets/`
3. build or verify `_fastlm`
4. run preflight checks
5. write a success marker only on full success

## Required Inputs

- `assets_manifest_v1.json`
- pinned requirements files under `requirements/targets/`
- source needed to build or validate `_fastlm` for current platform

## Required Outputs

Setup/preflight run root:

- `output/tools/benchmarks/community/setup_preflight/<timestamp>__setup_preflight*/`

Latest pointer:

- `output/tools/benchmarks/community/setup_preflight/latest/`

Latest pointer must contain:

- `setup.log`
- `setup_report.json`
- `preflight.log`
- `preflight_report.json`
- `benchmark_ready.json` (write only on success)

## Recombine Requirements

1. Recombine via temp path then verify then atomic rename.
2. Verify both `sha256` and `size_bytes` against manifest.
3. Fail clearly on missing parts or mismatch.
4. Leave `assets_packed/` unchanged.
5. Be idempotent and safe to rerun.

## `_fastlm` Requirements

1. Prefer verified platform-compatible build/artifact when present.
2. If build path is required, emit explicit diagnostics on failure.
3. Preflight must verify import and tiny scoring probe success.
4. Compliance report must include `fastlm_present` flag.

## Preflight Checks

1. Required imports succeed.
2. Required assets exist and pass manifest hash/size checks.
3. `_fastlm` import succeeds.
4. Tiny CPU scoring probe succeeds.
5. Compliance fields are set and reportable:
   - `device=cpu`
   - `scoring_backend=numpy`
   - `fastlm_present=true`

## Failure Behaviour

1. No `benchmark_ready.json` on any failure.
2. Preflight/setup logs must include actionable reason categories:
   - missing assets
   - hash/size mismatch
   - dependency import failures
   - fastlm unavailable
   - probe failure
3. No half-built final files in target locations.
