# Phase 0 Review Gate (v1.1)

Date: 2026-02-19

## Objective
Freeze a code-backed baseline before implementation of Phases 1-5:
- confirm required spec inputs
- confirm what exists vs missing in this repo
- identify determinism/compliance risks
- define a no-surprises execution order

## Inputs Verified
- Spec prompt: `planning/rdp_community_benchmark_v1_1_spec/prompt.txt`
- Spec files root: `planning/rdp_community_benchmark_v1_1_spec/`
- Community spec: `planning/rdp_community_benchmark_v1_1_spec/tools/benchmarks/community/campaign_spec_v1_1.md`
- Schemas:
  - `planning/rdp_community_benchmark_v1_1_spec/tools/benchmarks/community/schemas/manifest_schema_v1_1.json`
  - `planning/rdp_community_benchmark_v1_1_spec/tools/benchmarks/community/schemas/result_schema_v1_1.json`
- Profile catalogue:
  - `planning/rdp_community_benchmark_v1_1_spec/tools/benchmarks/community/profile_catalog_v1_1.json`
- Repo inventory source available at:
  - `tools/git_link_scrape/repo_links.csv`

## Current Repo State (Cross-check)
- Missing required target folder:
  - `tools/benchmarks/community` (not present)
- Missing required root asset files/folders:
  - `assets_manifest_v1.json` (missing)
  - `assets_packed/` (missing)
  - `assets/` (missing/generated target absent)
- Existing pipeline has non-campaign defaults:
  - Proven autoskip enabled in local pipeline:
    - `tools/benchmarks/bench_solve_periodic_columnar_pipeline.py:74`
  - Campaign-disallowed status/stop strings are currently used:
    - `tools/benchmarks/bench_solve_periodic_columnar_pipeline.py:1165`
    - `tools/benchmarks/bench_solve_periodic_columnar_pipeline.py:1805`
    - `tools/benchmarks/bench_solve_periodic_columnar_pipeline.py:1965`
    - `tools/benchmarks/bench_solve_periodic_columnar_pipeline.py:1967`
- Env-var driven runtime behaviour exists in sub-then-col script:
  - `tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py:60`
  - `tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py:69`
  - `tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py:78`
  - `tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py:79`
  - `tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py:82`

## Determinism / Compliance Risks
- Risk: campaign mode accidentally inherits local autoskip/proven logic.
- Risk: non-schema status/stop_reason values leak into campaign results.
- Risk: per-machine behaviour divergence from env vars (sub-then-col path).
- Risk: repeat-fail seed mutation based on local history changes job trajectory.
- Risk: missing asset recombination pipeline blocks reproducible setup.

## Phase 0 Decisions (Locked)
- Do not do broad repo moves in Phases 3-5.
- Do only targeted asset-layout work in Phase 2:
  - add root `assets_packed/`
  - add root `assets_manifest_v1.json`
  - generate root `assets/` via setup
- Keep existing local benchmark scripts functioning.
- Add campaign-specific entrypoints under `tools/benchmarks/community/`.
- Campaign mode must never use proven autoskip; resume-skip only, explicitly logged.

## Implementation Order (No Code Drift)
- Phase 1: copy v1.1 spec/docs/schemas/examples into `tools/benchmarks/community/` and `docs/setup/`; add schema load/validate tests.
- Phase 2: implement setup+preflight with atomic recombine and fastlm verify/build; write setup/preflight/ready reports.
- Phase 3: deterministic manifest generator + sharder from campaign config/profile catalogue.
- Phase 4: shard runner in campaign mode with strict status/stop_reason enums and cap precedence.
- Phase 5: organiser validate/combine/aggregate with deterministic tie-break rules.

## Exit Criteria for Phase 0
- This review gate document exists and is accepted.
- File-path and line-pointer evidence is recorded for all major risks.
- No implementation starts without test targets defined per phase.
