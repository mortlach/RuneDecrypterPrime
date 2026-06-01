# Community Benchmark Unified Plan (v1.1)

Status: Active execution plan.

This file controls phase sequencing and integration gates for the V1.1 community benchmark campaign.

Companion canonical docs:

- contract: `10_contracts/campaign_spec_v1_1.md`
- setup/preflight: `30_validation_and_setup/setup_and_preflight_v1_1_spec.md`
- scoring/Torch gates: `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`

## Progress Update (2026-02-27)

Implementation progress from runner harmonization and bundle-integrity hardening:

- Completed: shared periodic runner pathing now in place for all three flavors (`no_wli`, `col_then_sub`, `sub_then_col`) for:
  - shared `Tier` type
  - shared checkpoint/snapshot writer path
  - shared CSV append/write logic (via common helper layer)
- Completed: campaign single-job adapter now resolves run directories from flavor-specific output roots (reduced ambiguity).
- Completed: campaign single-job adapter now requires explicit runner entrypoint `configure_campaign_run(...)` (legacy mutation fallback removed).
- Completed: run bundles now include tamper-evident result integrity chain:
  - `results_integrity.jsonl` written by `run_shard.py`
  - integrity summary persisted under `run_meta.json/results_integrity`
  - `validate_run_bundle.py` verifies chain and rejects tampered rows
- Validated: targeted runner/community tests passed after this harmonization wave.

Still open in this plan:

- full runner-config dataclass migration (beyond shared `Tier`)
- scorer provenance expansion in result rows (requested vs effective objective/window labels)
- schema/policy decisions for any internal no-WLI campaign extension

Execution detail remains in:

- `40_supporting_reference/runner_cleanup_and_refactor/34_runner_cleanup_and_refactor_history/BENCH_CAMPAIGN_CLEANUP_PLAN_2026-02-25.md`
- `40_supporting_reference/runner_cleanup_and_refactor/34_runner_cleanup_and_refactor_history/benchmarks_periodic_sub_trans_refactor_plan.md`

## Goal

Deliver one reproducible community benchmark workflow that contributors can run on Windows, macOS, or Linux from a single setup entrypoint, with deterministic outputs that can be validated and merged reliably.

## Locked Decisions

1. No release tag until additional benchmark coverage and testing is complete.
2. V1.1 community submissions are CPU-only and NumPy-scored.
3. Campaign runtime behaviour is config-driven; no environment-variable switches.
4. Campaign mode allows only resume-skip by existing `job_id`; no proven/autoskip behaviour.
5. Planning is local to `planning/`; user-facing operational docs belong under `docs/` and `tools/`.

## Phase Plan

## Phase 0: Docset Freeze and Contract Alignment

Deliverables:

- canonical document map maintained in `03_DOCUMENT_MAP.md`
- benchmark contract and setup specs aligned
- scoring-path gating plan linked into campaign rollout

Exit gate:

- no conflicting definitions for status/stop_reason/schema fields across active planning docs

## Phase 1: Setup and Preflight Reliability

Deliverables:

- single install/setup flow that installs requirements, recombines split assets, builds or verifies `_fastlm`, and runs preflight
- deterministic setup report path and latest pointer with success marker

Exit gate:

- fresh-clone setup produces `benchmark_ready.json`
- setup/preflight reports are deterministic and actionable on failure

## Phase 2: Campaign Runner Surface

Deliverables:

- stable entrypoint and config surface for campaign jobs
- explicit visibility of scanned options per run (order, period, columns, profile, seed)
- strict status/stop_reason output compliance per job

Exit gate:

- canary and shard runs produce schema-valid run bundles with no missing required tags

Phase status note (2026-02-27):

- complete: runner output plumbing harmonized and run-dir resolution is flavor-scoped/deterministic
- complete: explicit runner campaign entrypoint contract (`configure_campaign_run(...)`) enforced
- pending: explicit runner config object boundary and scorer provenance expansion

## Phase 3: Data Integrity and Integration

Deliverables:

- deterministic manifest generation and sharding
- strict run-bundle validation
- deterministic combine and aggregation outputs (including collision reporting)

Exit gate:

- same input bundles produce identical integrated outputs on repeated runs

Phase status note (2026-02-27):

- complete: deterministic combine/aggregate path and collision reporting
- complete: strict run-bundle integrity-chain checks in validator
- pending: policy decision for partial bundle acceptance vs strict full-shard completeness

## Phase 4: Scoring Path Gate for no-WLI and Future Mixed Flavours

Deliverables:

- AVG path correctness fixes and tests (ECDF separation, parity, crash gating) completed per scoring plan
- campaign-level rules for when no-WLI or mixed flavours can be enabled

Exit gate:

- no-WLI promotion is blocked until scoring contract tests and crash/stability gates pass

## Phase 5: V1 Readiness Gate (No Tag Yet)

Deliverables:

- docs consistency check (commands, paths, outputs)
- setup/preflight smoke checks
- campaign schema and integration integrity checks
- benchmark regression checks for selected baseline profiles

Exit gate:

- V1 is considered "ready for extended benchmark/testing cycle"
- tag remains deferred until coverage target is met

## Campaign Readiness Criteria

1. User entrypoint is obvious: setup, canary, shard run, bundle submit.
2. Runner clearly reports what is being scanned and under which caps/profile.
3. Manifest/result schemas and validator rules detect missing tags, bad enums, duplicates, and partial bundles.
4. Integration stage logs deterministic conflict handling and aggregate summaries.
5. Privacy-safe defaults are enforced for shared outputs.

Current criteria snapshot (2026-02-27):
- (1) Mostly met
- (2) Mostly met
- (3) Partially met (tags/enums/duplicates and integrity chain are covered; strict full-shard completeness policy is pending)
- (4) Met
- (5) Open
