# RDP Community Benchmark Campaign Spec (v1.1)

## 0) Purpose
Run a small (≤5 people) community benchmark campaign to measure solver robustness across:
- period: 7..13
- columns: 1..13
- order: col_then_sub, sub_then_col
- fixed profile catalogue
- replicate seeds per sampled cell

v1.1 is designed to be:
- self-contained (assets in-repo as split parts + recombined by setup)
- CPU-only (GPU out of scope)
- deterministic and reproducible (no env vars, stable hashing)
- small-output (JSONL + CSV summaries; no SQL)

## 1) Scope
### In scope
- Portable packaging requirements for RDP
- Setup/deploy + preflight workflow
- Campaign bundle format (config, profiles, schemas, manifest, shards)
- Runner flow (run shard, resume, logging, run bundle output)
- Organiser flow (validate run bundles, combine, aggregate)
- Canary run definition

### Out of scope
- Solver rewrite / algorithm changes
- GPU/Torch scoring submissions
- SQL databases
- Large per-job artefact uploads (keep run bundles compact)

## 2) Determinism rules (mandatory)

### 2.1 Stable hashing only
- Do not use Python `hash()` for ids, fingerprints, sharding, or determinism checks.
- Use SHA-256 over canonical JSON bytes.

### 2.2 Canonical JSON serialisation
For any hash/fingerprint:
- sorted keys
- fixed separators
- allow_nan = false
- floats normalised consistently before serialisation (choose one fixed rule; do not change within v1.1)

### 2.3 Randomness is local and seeded
- All randomness must come from a local PRNG seeded from `run_seed`.
- Do not use global RNG state.
- Do not seed from wall-clock time.

### 2.4 Deterministic ordering
- Manifest generation must be reproducible from: git_sha + campaign_seed + campaign config + profile catalogue.
- Sharding must be reproducible from: campaign_seed + full manifest.
- Resume skip is deterministic: skip only if `job_id` already exists in local results.

## 3) Assets (split + recombine)

### 3.1 Canonical asset layout
- `assets_packed/` (tracked): split parts (GitHub-friendly sizes)
- `assets/` (generated locally, gitignored): recombined assets

### 3.2 Asset manifest
Tracked file: `assets_manifest_v1.json`
For each final file under `assets/`, include:
- final_relpath
- sha256
- size_bytes
- ordered list of part files under `assets_packed/`

### 3.3 Recombine requirements
Setup must:
- recombine atomically (temp file -> verify -> rename)
- verify final sha256 and size
- fail clearly on missing parts or hash mismatch
- leave packed parts unchanged

## 4) Setup/deploy step (mandatory for contributors)

### 4.1 One entrypoint
A single setup/deploy step must:
- install/check dependencies (pinned for benchmark)
- recombine assets
- build/verify required components (including `_fastlm`)
- run preflight
- write `benchmark_ready.json` only when complete

### 4.2 Outputs
Setup must write:
- run directory under:
  - `output/tools/benchmarks/community/setup_preflight/<timestamp>__setup_preflight*/`
- latest pointer directory:
  - `output/tools/benchmarks/community/setup_preflight/latest/`
  - contains `setup.log`, `setup_report.json`, `preflight.log`, `preflight_report.json`, `benchmark_ready.json` (success marker only)

### 4.3 Clean-room / idempotence
- safe to rerun
- no half-built artefacts left in final locations
- “ready marker” only on full success

## 5) CPU-only rule (v1.1)
Benchmark submissions must run CPU scoring. GPU/Torch scoring is out of scope for v1.1.

Compliance requires:
- device = "cpu"
- scoring_backend = "numpy"
- `_fastlm_present = true`

If a submission is non-compliant, it must be rejected by bundle validation.

## 6) Campaign inputs

### 6.1 Universe per fixture
periods 7..13, columns 1..13, orders 2 => 182 cells per fixture.

### 6.2 Sampling
v1.1 supports:
- full_grid (default)
- stratified_subset (if used, must be explicitly described in campaign config)

### 6.3 Profiles
Profiles are defined in `profile_catalog_v1_1.json`.
Runners do not edit solver parameters.

## 7) Canary run (mandatory addition)

### 7.1 Purpose
A short end-to-end smoke run (minutes) to catch:
- setup mistakes
- missing assets
- `_fastlm` issues
- runner logging/resume issues
- schema drift

### 7.2 Canary config
A canary campaign must be provided, containing:
- 6–12 jobs total
- spans both orders
- includes at least one small column case (e.g. c=3)
- one profile (baseline)
- 1 replicate per job

## 8) Data contracts

### 8.1 Manifest row (JSONL)
Each row must include:
- campaign_id
- job_id
- git_sha
- text_fixture_id
- period
- columns
- order
- profile_id
- run_seed
- replicate_idx
- config_fingerprint

job_id must be deterministic from the row content (excluding job_id itself).

### 8.2 Result row (JSONL)
Each row must include all manifest fields plus:
- status (enum)
- stop_reason (enum)
- best_match_ratio
- best_stage
- total_seconds
- total_evals
- stage1_best_score
- stage2_best_score
- stage3_best_score
- output_run_dir (optional, may be empty)

Backend provenance fields (required):
- device = "cpu"
- scoring_backend = "numpy"
- fastlm_present = true/false

## 9) Caps, status, and stop reasons (mandatory)

### 9.1 Per-job caps (enforced)
Campaign config must include:
- max_seconds_per_job (hard cap)
Optional:
- max_total_evals_per_job

Caps must be enforced by the runner and interpreted consistently.

### 9.2 status enum
- solved
- unsolved
- stalled
- error

### 9.3 stop_reason enum (stable strings)
Every job must have a stop_reason, including solved jobs.

Required stop reasons (v1.1):
- solved_threshold_met
- time_cap_reached
- eval_cap_reached
- stage1_budget_exhausted
- stage2_budget_exhausted
- stage3_budget_exhausted
- plateau_detected
- no_candidates_to_promote
- invalid_config
- missing_assets
- fastlm_unavailable
- exception_raised

### 9.4 Stop precedence (to avoid ambiguity)
When multiple stop conditions apply, record the highest-precedence reason:

1) exception_raised / invalid_config / missing_assets / fastlm_unavailable
2) time_cap_reached
3) eval_cap_reached
4) solved_threshold_met
5) stage*_budget_exhausted
6) no_candidates_to_promote
7) plateau_detected
8) unspecified (should not happen; treat as a bug)

## 10) Runner semantics

### 10.1 No silent autoskip
Campaign mode must not use “proven autoskip”.
The only allowed skip is resume-skip when job_id is already recorded locally.

### 10.2 Resume rules
- If job_id exists in local results.jsonl, the runner may skip it.
- Every resume skip must be logged explicitly as RESUME_SKIP_ALREADY_RECORDED.

## 11) Run bundle output

Each contributor shares a run bundle folder:

run_bundle/
- run_meta.json
- setup_report.json
- setup.log
- preflight_report.json
- preflight.log
- campaign_config_v1_1.json (copy)
- profile_catalog_v1_1.json (copy)
- shard_manifest.jsonl (copy)
- results.jsonl
- run.log

Bundles should remain small.

## 12) Bundle validation (mandatory addition)

Before combining, organisers validate each run_bundle:
- required files present
- results.jsonl validates against schema
- campaign_id and git_sha match
- no duplicate job_id within a bundle
- CPU compliance fields present
- status and stop_reason are valid enums

Bundles that fail validation are rejected.

## 13) Combining and aggregation (no SQL)

### 13.1 Combine
Produce:
- combined_results.jsonl (deduped by job_id)
- collisions.jsonl (duplicates recorded)

### 13.2 Deterministic dedupe policy
If duplicates exist for a job_id:
1) prefer status=solved
2) else prefer higher best_match_ratio
3) else prefer lower total_seconds
4) else stable tie-break (runner_id then timestamp)

### 13.3 Aggregate outputs
Produce:
- summary_by_cell.csv
- summary_by_profile.csv
- solve_rate_heatmap_order_col_then_sub.csv
- solve_rate_heatmap_order_sub_then_col.csv
- stop_reason_counts_by_cell.csv
- stop_reason_counts_by_profile.csv

## 14) Acceptance criteria (v1.1)
1) Fresh clone -> setup recombines assets and builds/verifies `_fastlm`.
2) Preflight produces clear pass/fail reports.
3) Canary run succeeds end-to-end (or fails with actionable logs).
4) Runner produces a complete run_bundle.
5) Validator rejects malformed bundles clearly.
6) Combine produces combined_results.jsonl deterministically.
7) Aggregation produces summary + heatmaps + stop reason summaries.
8) Every job has both status and stop_reason.
