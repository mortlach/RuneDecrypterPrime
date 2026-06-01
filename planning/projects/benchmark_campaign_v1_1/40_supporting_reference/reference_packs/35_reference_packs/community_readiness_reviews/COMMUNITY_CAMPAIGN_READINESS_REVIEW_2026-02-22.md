# Community Benchmark Campaign Readiness Check

Date: 2026-02-22
Scope: planning-only review of the community benchmark campaign scripts and operator flow.

## Executive summary

Status: core campaign tooling is usable for controlled runs, but not yet "friction-free" for broad community rollout.

What is strong now:
- End-to-end campaign script chain exists and is coherent: setup/preflight -> manifest -> shard -> run_shard -> validate -> combine -> aggregate.
- Deterministic manifest and sharding logic are implemented.
- Result schema and bundle validation are strict.
- Data integration path includes deterministic collision handling.
- Dedicated community tests are healthy (`33 passed` on 2026-02-22 via `py -3.11 -m pytest -q tests/community`).

Main risks before larger campaign scale:
- Runner coupling risk: campaign job injection depends on module-global names in each runner.
- User guidance is split across multiple docs; the "what am I scanning" view is not a single obvious page.
- Community campaign currently covers only `col_then_sub` and `sub_then_col`; `no_wli` is not part of campaign execution.
- No-WLI V1 scorer gate now tracked separately: AVG must be runtime-ECDF-free and NumPy/Torch parity-tested before no-WLI is promoted into shared campaign mode.

## Current linkage map (how paths connect)

Campaign job dimensions are produced from:
- fixtures
- period range
- columns range
- order
- profile
- replicate index

Current order linkage in campaign execution:
- `col_then_sub` -> `tools.benchmarks.periodic_sub_trans.col_then_sub.runner`
- `sub_then_col` -> `tools.benchmarks.periodic_sub_trans.sub_then_col.runner`

Campaign mode behavior applied per job:
- disables proven autoskip
- forces rerun semantics for campaign correctness
- sets seed/tier for the single assigned manifest row
- applies profile catalog overrides through `profile_config.py`

Important separation reality:
- Community campaign orchestrator is centralized.
- The two path runners still own their own internal solver knobs and run-mode internals.
- `no_wli` flavor has its own runner and launchers but is not wired into community campaign schema/order mapping.

## User-entrypoint simplicity assessment

What is good:
- One bootstrap command: `python install.py --target runner`
- Optional canary command is documented.
- Runner config template is small and editable (`runner_id`, `shard_path`, `output_root`, `resume`, optional `max_jobs`).

What is still hard for new contributors:
- Instructions are distributed across multiple files (`README.md`, `README_runner.md`, `README_canary.md`, `README_organiser.md`).
- There is no single "scan matrix" page that explains, in one place, the exact axes users are scanning (period/columns/order/profile/replicate) and why.
- The difference between campaign paths and non-campaign flavor scripts is easy to misunderstand.

## Shared resources vs duplicated implementation

Centralized/shared (good):
- schema contracts (`schemas/*.json`)
- deterministic hashing/JSONL IO helpers (`_campaign_common.py`)
- profile validation and override application (`config/profile_config.py`)
- run bundle validation/combine/aggregate toolchain

Duplicated/tightly-coupled (risk):
- runner-specific global config surfaces in each path runner
- campaign adaptor mutates runner module attributes if present
- if a runner renames/removes expected globals, campaign behavior can silently drift

Planning implication:
- keep a compatibility contract for runner modules as explicit campaign requirements (document + tests), even before any refactor.

## Campaign readiness checks for scripts people actually run

### A. Operator usability checks
- Fresh clone bootstrap: `python install.py --target runner` succeeds and writes setup/preflight artifacts.
- Canary run succeeds on same environment.
- `run_shard.py` can execute `max_jobs=1` and produce a valid run bundle.
- Resume behavior is explicit: second run skips only by existing `job_id` and logs `RESUME_SKIP_ALREADY_RECORDED`.

### B. Path coverage checks
- Manifest contains both orders when configured.
- Shards include both orders and selected profiles.
- At least one smoke shard run per order before campaign starts.
- Explicitly document that `no_wli` is outside current community campaign unless schema+runner mapping is extended.

### C. Data integrity checks
- Validate every submitted bundle with `validate_run_bundle.py` against expected `campaign_id` and `git_sha`.
- Enforce required bundle files and schema-valid rows.
- Enforce CPU/numpy/fastlm compliance fields.
- Detect duplicate `job_id` at manifest and result levels.
- Ensure every result `job_id` exists in the shard manifest.

### D. Integration robustness checks
- Combine only validated bundles.
- Record and review collisions (`collisions.jsonl`) each combine cycle.
- Confirm aggregate outputs are generated and row counts are sane.
- Track stop-reason distributions by cell/profile to catch systemic failures early.

## Proposed release-gate checklist (planning)

Gate 1: Setup and canary
- `install.py --target runner` passes on Windows and Linux.
- Canary campaign completes and validates.

Gate 2: Campaign execution correctness
- Community test suite green (`tests/community`).
- One controlled shard per order executed and validated.
- Resume semantics verified on interrupted/restarted shard.

Gate 3: Data pipeline integrity
- All incoming bundles pass validation.
- Combine report has expected row counts and reviewed collisions.
- Aggregate outputs published with summary + heatmaps + stop reasons.

Gate 4: Contributor clarity
- One "single-page operator runbook" exists and links out to detailed docs.
- One "campaign scan matrix" section explains period/columns/order/profile/replicate/caps.
- Explicit note distinguishes campaign scripts from flavor-specific experimentation scripts.

## Immediate next planning tasks (no code changes)

1. Write a single operator-first campaign runbook page that compresses setup, canary, shard run, validate, and share steps into one flow.
2. Add a campaign scan matrix table (axes, ranges, intent, cost) based on the active campaign config.
3. Add a short "in scope vs out of scope" note clarifying that current community campaign supports `col_then_sub` and `sub_then_col` only.
4. Define a small pre-campaign dry-run checklist for organisers (2-bundle combine/aggregate rehearsal).
5. Add a campaign runner compatibility checklist (required runner globals/behaviors) tied to tests.
