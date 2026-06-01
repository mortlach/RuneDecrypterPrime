# RDP Community Benchmark Campaign Spec (v1.1)

Status: Active contract spec.

This file defines campaign data and runtime rules. It is the contract companion to:

- execution plan: `20_active_plans/community_benchmark_unified_plan_v1_1.md`
- setup spec: `30_validation_and_setup/setup_and_preflight_v1_1_spec.md`
- scoring/Torch gates: `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`

## Progress Update (2026-02-25)

Contract-relevant implementation updates:

- campaign single-job execution now resolves run outputs from flavor-specific directories under:
  - `output/tools/benchmarks/periodic_sub_trans/<flavor>/...`
- periodic runner artifact persistence paths (`instances/stages/summary`) are now harmonized through shared helper logic.

No contract enum changes were made in this wave:

- `order` remains `col_then_sub | sub_then_col` for public v1.1
- compliance remains `device=cpu`, `scoring_backend=numpy`, `fastlm_present=true`

Open contract follow-up:

- if internal no-WLI campaign mode is enabled, add explicit flavor/schema extension rather than overloading current public `order` contract.

## 0) Purpose

Run a small community benchmark campaign that measures robustness across:

- period: 7..13
- columns: 1..13
- order: `col_then_sub`, `sub_then_col`
- fixed profile catalogue
- replicate seeds per sampled cell

## 1) Scope

In scope:

- setup/preflight workflow
- campaign manifest, sharding, runner, bundle output
- organiser validation, combine, and aggregate
- deterministic reproducibility rules

Out of scope:

- solver algorithm rewrites
- GPU/Torch submissions for public v1.1 leaderboard
- SQL or large database-backed outputs

## 2) Determinism Rules (Mandatory)

1. Use SHA-256 over canonical JSON bytes for IDs and fingerprints.
2. Never use Python `hash()` for campaign determinism.
3. Canonical JSON uses sorted keys, fixed separators, and disallows NaN.
4. Randomness is local and seeded from run/job seed only.
5. Manifest and shard ordering must be deterministic and reproducible.
6. Resume skip is deterministic and based only on existing recorded `job_id`.

## 3) Asset Contract

1. `assets_packed/` contains split source parts.
2. `assets/` is generated locally from `assets_manifest_v1.json`.
3. Setup must recombine atomically and verify hash/size before final write.
4. On failure, setup must fail clearly and leave no half-written final assets.

## 4) Setup and Preflight Contract

A single setup entrypoint must:

1. install pinned benchmark requirements
2. recombine assets
3. build or verify `_fastlm`
4. run preflight
5. write success marker only on full success

Output contract:

- run folder under `output/tools/benchmarks/community/setup_preflight/...`
- latest pointer folder containing:
  - `setup.log`
  - `setup_report.json`
  - `preflight.log`
  - `preflight_report.json`
  - `benchmark_ready.json` (success only)

## 5) v1.1 Submission Compliance

Public campaign submissions must include:

- `device="cpu"`
- `scoring_backend="numpy"`
- `fastlm_present=true`

Non-compliant bundles are rejected for leaderboard integration.

## 6) Campaign Input Universe

Per text fixture:

- periods 7..13
- columns 1..13
- both orders

Sampling modes:

- `full_grid`
- `stratified_subset` (must be explicitly declared in config)

## 7) Canary Run

Mandatory campaign smoke path:

- 6 to 12 jobs
- both orders represented
- at least one small-column case
- one profile baseline
- one replicate per job

## 8) Manifest and Result Data Contracts

Manifest row required fields:

- `campaign_id`
- `job_id`
- `git_sha`
- `text_fixture_id`
- `period`
- `columns`
- `order`
- `profile_id`
- `run_seed`
- `replicate_idx`
- `config_fingerprint`

Result row required fields:

- all manifest fields, plus:
- `status`
- `stop_reason`
- `best_match_ratio`
- `best_stage`
- `total_seconds`
- `total_evals`
- `stage1_best_score`
- `stage2_best_score`
- `stage3_best_score`
- `output_run_dir` (optional empty allowed)
- `device`
- `scoring_backend`
- `fastlm_present`

## 9) Status and Stop-Reason Enums

Status enum:

- `solved`
- `unsolved`
- `stalled`
- `error`

Required stop_reason enum values:

- `solved_threshold_met`
- `time_cap_reached`
- `eval_cap_reached`
- `stage1_budget_exhausted`
- `stage2_budget_exhausted`
- `stage3_budget_exhausted`
- `plateau_detected`
- `no_candidates_to_promote`
- `invalid_config`
- `missing_assets`
- `fastlm_unavailable`
- `exception_raised`

Stop precedence (highest to lowest):

1. `exception_raised`, `invalid_config`, `missing_assets`, `fastlm_unavailable`
2. `time_cap_reached`
3. `eval_cap_reached`
4. `solved_threshold_met`
5. `stage*_budget_exhausted`
6. `no_candidates_to_promote`
7. `plateau_detected`

## 10) Runner Semantics

1. Campaign mode must not use proven/autoskip.
2. Resume skip is allowed only when `job_id` already exists in local results.
3. Each resume skip must be logged explicitly as `RESUME_SKIP_ALREADY_RECORDED`.
4. Caps must be enforced consistently per job.

## 11) Run Bundle Contract

Each contributor bundle must include:

- `run_meta.json`
- `setup_report.json`
- `setup.log`
- `preflight_report.json`
- `preflight.log`
- `campaign_config_v1_1.json`
- `profile_catalog_v1_1.json`
- `shard_manifest.jsonl`
- `results.jsonl`
- `run.log`

## 12) Bundle Validation Rules

Before combine, validator must enforce:

1. required files present
2. schema validation passes
3. campaign_id and git_sha match expected
4. no duplicate `job_id` within a bundle
5. compliance fields present and valid
6. status and stop_reason enums valid
7. (strict integration mode) result set completeness vs manifest unless explicitly marked partial

## 13) Combine and Aggregate Rules

Combine output:

- `combined_results.jsonl`
- `collisions.jsonl`

Deterministic dedupe order:

1. prefer `status=solved`
2. else prefer higher `best_match_ratio`
3. else prefer lower `total_seconds`
4. else stable tie-break (`runner_id`, then timestamp)

Aggregate outputs include:

- summary by cell/profile
- order-specific solve-rate heatmaps
- stop-reason summaries

## 14) Acceptance Criteria

1. Fresh clone can complete setup + preflight successfully.
2. Canary run works end-to-end with clear logs.
3. Runner outputs complete and schema-valid rows.
4. Validator rejects malformed or non-compliant bundles clearly.
5. Combine and aggregate are deterministic on repeated input.
6. Every job has both valid `status` and `stop_reason`.
