# Bench Campaign Cleanup Plan (Runner Harmonization)
Date: 2026-02-25
Status: Draft for implementation discussion

## Goal
Align `periodic_sub_trans` runner flavors so campaign orchestration can choose randomized runner configs with minimal flavor-specific logic, while keeping the same proven solving implementation.

This plan is structural and orchestration-focused:
- keep solver behavior intact
- reduce duplicated runner plumbing (config load/apply/save/log/checkpoint)
- keep outputs deterministic and campaign-schema compliant

## Progress Update (2026-02-27, post common-path refactor)

Completed in code:
- Shared runner `Tier` dataclass introduced and adopted by all three flavors:
  - `tools/benchmarks/periodic_sub_trans/common/runner_types.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
- Common IO/report helpers expanded:
  - `append_csv_row(...)`
  - `write_pipeline_snapshot_files(...)`
  - in `tools/benchmarks/periodic_sub_trans/common/io_reports.py`
- All three flavors now use common snapshot/checkpoint writer path for `instances/stages/summary` JSON+CSV outputs.
- Campaign single-job runner now resolves run directories from flavor-specific output roots (not broad top-level guessing):
  - `tools/benchmarks/community/_run_single_job.py`
- Campaign single-job runner now hard-pins scorer impl to NumPy across runner scorer globals and stage scorer profile dictionaries:
  - `tools/benchmarks/community/_run_single_job.py`
- Runner config entrypoint (`configure_campaign_run(...)`) added to all periodic_sub_trans flavors and used by campaign single-job dispatch when available:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
  - `tools/benchmarks/community/_run_single_job.py`
- Campaign adapter now requires the runner entrypoint (legacy fallback removed):
  - `tools/benchmarks/community/_run_single_job.py`
- `no_wli`, `sub_then_col`, and `col_then_sub` now write history rows directly with `common/io_reports.append_csv_row(...)` (local wrappers removed):
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
- Community run-bundle integrity chain added (tamper-evident row hash-chain):
  - sidecar `results_integrity.jsonl`
  - validator enforcement in `validate_run_bundle.py`
  - chain summary in `run_meta.json`

Validation completed:
- `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py` passed.
- `tests/community/test_run_single_job_config_v1_1.py` passed.
- `tests/community/test_run_shard_v1_1.py` passed.
- `tests/community/test_validate_run_bundle_v1_1.py` passed.
- `tests/community/test_combine_and_aggregate_v1_1.py` passed.

Still open from this plan:
- Full shared runner-config dataclass migration (beyond shared `Tier`).
- Campaign schema/profile-level expansion for additional flavors and richer scorer provenance fields.
- Optional strict full-shard completeness policy (currently validator allows partial results if rows present are valid).

## Constraints From Active Specs
1. Public v1.1 campaign contract is CPU + NumPy + fastlm (`10_contracts/campaign_spec_v1_1.md`, section 5).
2. Campaign semantics are deterministic and config-driven (`20_active_plans/community_benchmark_unified_plan_v1_1.md`, locked decisions).
3. Solver rewrites are out of scope for this cleanup wave (same plan, phase scope).
4. Internal no-WLI/Torch tuning can continue, but public schema/integration remains strict CPU/NumPy.

## Current State (Evidence)

### What is already good
- All three flavors are in one package tree: `tools/benchmarks/periodic_sub_trans/`.
- Shared helpers exist (`common/paths.py`, `common/io_reports.py`, `common/batch_eval.py`).
- Stage solve flow is already similar (3-stage structure, Kaeding calls, staged summaries).
- no-WLI has per-instance crash-safe checkpointing (not end-only).

### What is still fragmented
1. Campaign adapter is flavor-limited:
- only dispatches `col_then_sub` and `sub_then_col`
  - `tools/benchmarks/community/_run_single_job.py:246`
  - `tools/benchmarks/community/_run_single_job.py:248`
- campaign module must provide `configure_campaign_run(...)`; no mutation fallback path remains.

2. Campaign profile contract says profiles own solver/scorer tuning, but scorer schedule is not applied to runners in the current profile adapter:
- profile catalog notes:
  - `tools/benchmarks/community/profile_catalog_v1_1.json:4`
  - `tools/benchmarks/community/profile_catalog_v1_1.json:5`
- adapter currently applies override maps only (no `scorer_schedule` plumbing into runner scorer configs):
  - `tools/benchmarks/community/config/profile_config.py:228`
  - `tools/benchmarks/community/config/profile_config.py:302`

3. Schema currently excludes no-WLI and p5/p6 custom scans by design:
- manifest order enum only has `col_then_sub` and `sub_then_col`
  - `tools/benchmarks/community/schemas/manifest_schema_v1_1.json:47`
- period range fixed to 7..13
  - `tools/benchmarks/community/schemas/manifest_schema_v1_1.json:37`
- result schema locks `device=cpu`, `scoring_backend=numpy`
  - `tools/benchmarks/community/schemas/result_schema_v1_1.json:150`
  - `tools/benchmarks/community/schemas/result_schema_v1_1.json:156`

5. Campaign adapter now uses explicit runner entrypoint when available, and run-directory capture is flavor-scoped and deterministic:
- run dir discovery is no longer top-level broad guessing
  - `tools/benchmarks/community/_run_single_job.py`
- remaining coupling concern is now limited to schema/profile scope, not runner wiring.

6. Output persistence timing differs by flavor implementation details (although all checkpoint per instance in practice):
- no-WLI explicit per-instance checkpoint block
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py:3065`
- col-then-sub explicit per-instance checkpoint block
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py:2503`
- sub-then-col explicit per-instance checkpoint block
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py:1402`

7. Operator-facing labels are partly ambiguous or drift-prone:
- AVG objective can be configured as `avg.logp.win20` while runtime is `full_text` policy; users read `win20` and assume fixed-window scoring.
  - objective summary helper shows both configured/effective (`tools/benchmarks/periodic_sub_trans/no_wli/runner.py:799`)
  - scorer telemetry marks effective full-text window (`src/rune_decrypter_prime/scoring/rune_scorer.py:951`, `src/rune_decrypter_prime/scoring/torch_rune_scorer.py:962`)
- Stage-2 judge toggles are `True` in top-level defaults but forced `False` in scan mode, which can mislead quick readers of runner constants.
  - defaults (`tools/benchmarks/periodic_sub_trans/no_wli/runner.py:74`)
  - scan-mode override (`tools/benchmarks/periodic_sub_trans/no_wli/runner.py:532`)
- Profile naming fields are inconsistent (`NO_WLI_PIPELINE_PROFILE_ID`, `PROFILE`, run config `profile` key), making cross-run comparison harder than necessary.

## Effort Estimate

Two realistic scope options:

### Option A: Minimal harmonization (recommended immediate)
Estimate: 5 to 7 engineer-days

Includes:
- unify write/checkpoint/history helpers
- unify runner contract dataclass layer
- keep flavor-specific stage logic in each runner
- fix campaign adapter to resolve run dirs robustly
- keep current public v1.1 schema (no new no-WLI campaign mode yet)

### Option B: Full campaign-ready harmonization (includes randomized flavor selection)
Estimate: 10 to 14 engineer-days

Includes Option A, plus:
- add explicit flavor dimension to campaign engine
- optional schema extension for internal campaign mode (`no_wli` and p5/p7 style ranges)
- scorer schedule application contract across all flavors
- simplified user entrypoint wrappers for non-expert contributors

## Detailed TODO Workstreams

## W0: Define Runner Contract Dataclasses (config surface) [In Progress]
Estimate: 1.5 to 2.0 days

TODO:
- Create shared dataclasses for runner config (run mode, tiers, seeds, scorer impl, stage knobs, output policy).
- Convert flavor globals into a `RunnerConfig` instance assembled at startup.
- Keep existing hardcoded launch files, but make them fill dataclasses instead of mutating many globals.
- Done (partial): shared `Tier` dataclass extracted and used by all three flavors.

Files to touch:
- `tools/benchmarks/periodic_sub_trans/config/` (new files)
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
- `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`

## W1: Unify Save/Load/Checkpoint/History Helpers [Mostly Complete]
Estimate: 1.5 to 2.0 days

TODO:
- Add common helpers for:
  - append-safe CSV row with schema/header evolution
  - periodic checkpoint write (`instances/stages/summary`)
  - final write + best-instance materialization
  - history row append and solve-proof files
- Remove local `_write_csv_rows`/`_append_csv_row` implementations from no-WLI and sub-then-col.
- Keep flavor-specific history file names, but use one common writer implementation.
- Done:
  - common append writer + snapshot writer added in `common/io_reports.py`
  - all three flavors moved to shared snapshot writer
  - no-WLI and sub-then-col removed `_write_csv_rows` local shims
  - all three flavors now call shared append helper directly
  - history appends route through shared append logic in all flavors
- Remaining:
  - `proven_logs.py` extraction is still pending

Files to touch:
- `tools/benchmarks/periodic_sub_trans/common/io_reports.py`
- `tools/benchmarks/periodic_sub_trans/common/` (new `checkpoints.py`, `proven_logs.py`)
- `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
- `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`

## W2: Runner Orchestration Boundary (same solver impl, less duplication)
Estimate: 2.5 to 3.5 days

TODO:
- Extract a shared stage-orchestration helper for common mechanics:
  - stage summary row shape
  - checkpoint timing
  - score/match best-selection policy hooks
  - artifact payload assembly
- Keep flavor differences as strategy callbacks (order, WLI usage, stage2 exact/hybrid policy, no-WLI stage3 two-phase behavior).
- Do not change solver algorithm internals (`SolverSpec.kaeding` call sites remain).

Files to touch:
- `tools/benchmarks/periodic_sub_trans/common/` (new `pipeline_core.py` or similar)
- all three flavor runners

## W3: Campaign Adapter Rationalization [Partial]
Estimate: 2.0 to 3.0 days

TODO:
 - Replace mutable-global coupling with explicit runner config object entrypoint.
 - Stop broad mutable-global poking from `_run_single_job`; pass one explicit config object into runner entrypoint.
 - Add optional `flavor` routing for internal campaign mode (if chosen).
 - Ensure scorer/backends provenance in result rows comes from runner telemetry, not hardcoded constants.
- Add explicit requested-vs-effective scorer metadata in run/result artifacts:
  - `objective_requested` (e.g., `avg.logp.win20`)
  - `avg_window_policy` (e.g., `full_text`)
  - `window_effective` (e.g., `full_text` vs `win20`)
  - `objective_effective` (normalized operator label, e.g., `avg.logp.full_text`)
- Normalize profile naming keys across run artifacts (`profile_id` as canonical key; retain backward-compatible alias only if needed).

Done:
- run-dir detection now scoped to flavor output roots in `_run_single_job.py`, removing prior top-level ambiguity.
- campaign scoring backend pinning added in `_run_single_job.py` to enforce v1.1 CPU/NumPy contract at runner config level.
- explicit runner config entrypoint wired in `_run_single_job.py` (`configure_campaign_run(...)`) and required.

Remaining:
- scorer/backend provenance fields sourced from runner runtime rather than hardcoded row constants
- optional flavor expansion policy and schema strategy for internal modes

Files to touch:
- `tools/benchmarks/community/_run_single_job.py`
- `tools/benchmarks/community/run_shard.py`
- `tools/benchmarks/community/config/profile_config.py`
- `tools/benchmarks/community/profile_catalog_v1_1.json` (if schedule mapping expanded)

## W4: Schema and Campaign Mode Split (public vs internal)
Estimate: 1.5 to 2.5 days (Option B only)

TODO:
- Keep public v1.1 schema unchanged for leaderboard integration.
- Add internal/experimental schema variant (or optional fields) for no-WLI + p5/p7 campaigns.
- If no-WLI is included, add explicit flavor field rather than overloading `order`.

Files to touch:
- `tools/benchmarks/community/schemas/manifest_schema_v1_1.json`
- `tools/benchmarks/community/schemas/result_schema_v1_1.json`
- `tools/benchmarks/community/generate_manifest.py`
- `tools/benchmarks/community/validate_run_bundle.py`
- docs + planning spec docs listed below

## W5: User Entry Points (casual operator)
Estimate: 1.0 to 1.5 days

TODO:
- Provide thin, hardcoded run files for common workflows:
  - campaign canary
  - p5/p7 no-WLI scan
  - col-then-sub focus run
  - sub-then-col focus run
- Keep simple naming and one-file edits for non-expert users.
- Document each entrypoint in a short matrix (what it runs, expected runtime, outputs).
- Add a one-screen "How to read labels" section:
  - requested objective vs effective runtime objective
  - configured window vs effective window
  - profile defaults vs run-mode overrides
  - fixed examples (`win20 + fixed_win`, `win20 + full_text`, `win30 + fixed_win`)

Files to touch:
- `tools/benchmarks/periodic_sub_trans/*/README.md`
- `tools/benchmarks/community/README_runner.md`
- `docs/howto/benchmarking.md` (or dedicated runner quickstart)

## W6: Tests and Gates
Estimate: 1.5 to 2.0 days

TODO:
- Extend runner tests for shared writer behavior and checkpoint timing parity.
- Add campaign adapter tests for deterministic run-dir resolution and flavor dispatch.
- Add config-layer tests proving `scorer_schedule` and overrides are both applied.
- Add label-consistency tests and guards:
  - if `avg_window_policy=full_text`, operator label must not imply effective `winK`
  - run artifacts must include both requested and effective objective/window fields
  - scan-mode override flags are recorded in run config and printed setup lines

Files to touch:
- `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py`
- new tests under `tests/tools/` for checkpoint writer parity
- `tests/community/test_run_single_job_config_v1_1.py`
- `tests/community/test_run_shard_v1_1.py`
- `tests/community/test_profile_config_layer_v1_1.py`

## Recommended Sequence
1. W0 (contract dataclasses)
2. W1 (I/O and checkpoint helper unification)
3. W3 partial (run-dir/result provenance fixes)
4. W6 partial (tests for W0-W3)
5. W2 (stage orchestration extraction)
6. W5 (user entrypoint simplification)
7. W4 only if internal randomized-flavor campaign is enabled now

## Acceptance Criteria For "Clean Campaign-Ready Runners"
1. Same solve logic remains intact across flavors (no solver rewrite).
2. One shared checkpoint/history writer path used by all flavors.
3. Campaign adapter no longer relies on fragile global-mutation + top-level run-dir guessing.
4. Profile config semantics are consistent with profile catalog notes.
5. Casual operators have simple hardcoded entry files with clear docs.
6. Per-instance crash-safe persistence is verified in all flavors.
7. Requested-vs-effective scorer/window labels are explicit and non-ambiguous in console logs and run artifacts.

Current acceptance status snapshot:
- (2) Met: all three flavors append history via the shared append writer path.
- (3) Met: campaign uses runner entrypoint config path; top-level run-dir guessing and global mutation path removed.

## Notes On Current Torch/no-WLI Work
- Current no-WLI branch is intentionally Torch-pinned for internal testing.
- Public community v1.1 compliance still requires CPU+NumPy.
- Keep this split explicit in docs/config names to avoid mixed datasets.

## W7: Local Campaign Pipeline Test + Console UX Pass (New)
Date: 2026-02-27
Status: In progress (console shape implemented, broader smoke matrix still pending)

Goal:
- run a real local campaign smoke pass end-to-end
- verify exactly what operators see on screen
- simplify campaign console output to a compact, user-friendly shape

### Why now
- Campaign wiring changed recently (`configure_campaign_run(...)` contract, run-dir routing, integrity chain).
- We need operator confidence before longer community-style runs.
- Current campaign top-level console output is too sparse for live monitoring (mostly final summary only).

### Current screen output reality (code evidence)
1. `run_shard.py` now prints compact operator lines:
- start banner (`campaign`, `runner`, `jobs`, `caps`, `shard`)
- path pointer line (`bundle`, `run_log`, `results`, `integrity`)
- per-job progress line (`job_id`, `status`, `stop`, `match`, `secs`, `evals`)
- final summary (`processed/skips/seen`, status counts, integrity tail)
2. Per-job lifecycle (`JOB_START/JOB_EXIT/RESUME_SKIP...`) is written to `run.log`, not stdout.
3. Runner internals (`[colsub]`, `[subcol]`, `[pipeline_no_wli] ...`) are captured into `run.log` by `_run_single_job` subprocess capture path.
4. `validate_run_bundle.py`, `combine_results.py`, `aggregate_results.py` already print concise final summaries.

Progress evidence:
- updated file: `tools/benchmarks/community/run_shard.py`
- local validation run:
  - `C:\\Python\\Python311\\python.exe -m pytest tests/community/test_run_shard_v1_1.py::test_run_shard_writes_schema_valid_results -s -q`
  - confirmed compact start/job/end lines on stdout
- regression tests:
  - `C:\\Python\\Python311\\python.exe -m pytest tests/community/test_run_shard_v1_1.py tests/community/test_validate_run_bundle_v1_1.py tests/community/test_combine_and_aggregate_v1_1.py tests/community/test_run_single_job_config_v1_1.py -q`
  - passed

### Local test matrix (hardcoded-config workflow, no CLI tuning knobs)
1. Contract/unit checks:
- `tests/community/test_run_single_job_config_v1_1.py`
- `tests/community/test_run_shard_v1_1.py`
- `tests/community/test_validate_run_bundle_v1_1.py`
- `tests/community/test_combine_and_aggregate_v1_1.py`
2. One-shard smoke run:
- use local runner config file with `max_jobs` set small (e.g. 1-3)
- verify `results.jsonl`, `results_integrity.jsonl`, `run_meta.json`, `run.log` are created and coherent
3. Resume behavior check:
- rerun same shard config and confirm resume skips + no duplicate rows
4. Tamper check:
- edit one `results.jsonl` row and confirm validator rejects integrity mismatch
5. Integration pass:
- combine 2+ run bundles, then aggregate; confirm deterministic outputs

### Proposed campaign console shape (target)
Print only high-signal lines:
1. Start banner:
- campaign_id, runner_id, shard file, total jobs, caps, resume flag, output bundle path
2. Per-job compact progress:
- `i/N job_id status stop_reason best_match total_seconds total_evals`
3. Resume skip line:
- `SKIP job_id already recorded`
4. End summary:
- processed, solved/unsolved/error counts, resume_skips, rows_written, integrity row_count/final hash
5. Pointers:
- `run.log`, `results.jsonl`, `results_integrity.jsonl`, `run_meta.json`

### Implementation approach (consistent with repo rule: hardcoded switches, no new CLI args)
- Add top-level console constants in `run_shard.py`, e.g.:
  - `CONSOLE_MODE = "compact"`
  - `CONSOLE_PRINT_PER_JOB = True`
  - `CONSOLE_PRINT_EVERY_N = 1`
  - `CONSOLE_PRINT_INTEGRITY_SUMMARY = True`
- Keep verbose details in `run.log`; keep stdout compact.
- Do not add new command-line flags for console behavior.

### Acceptance criteria
1. Operator can monitor live run progress without opening `run.log`.
2. Console output stays under control (no stage-level spam).
3. Final line always includes integrity-chain summary and key output paths.
4. Existing tests still pass after console-output refactor.

Current status snapshot:
- (1) Met
- (2) Met
- (3) Met
- (4) Met for targeted community tests

### Execution notes (2026-02-28 local drill)
1. Step 1 (fresh canary run, max_jobs=1): pass for pipeline wiring + logging hygiene.
- New bundle created:
  - `output/tools/benchmarks/community/canary/run_bundle__community_bench_canary_v1_1_example__local_privacycheck__canary_shard_00`
- `run.log` `JOB_CMD` is sanitized (no `C:\\Users\\...` absolute user path).

2. Step 2 (resume rerun): pass for resume-skip semantics + no duplicate `job_id`.
- Resume run produced one `RESUME_SKIP_ALREADY_RECORDED` and one new processed row (`max_jobs` counts processed jobs, not seen jobs).
- `results.jsonl` job_ids remained unique.

3. Step 3 (tamper drill): pass.
- Modified a copied bundle `results.jsonl` row.
- Validator rejected bundle with integrity mismatch (`integrity row ... mismatch for row_hash`).

4. Step 4 (combine+aggregate determinism): pass on local valid bundle pair.
- `combined_results.jsonl`, `collisions.jsonl`, and aggregate CSV hashes matched across two independent combine/aggregate runs.
- Run root:
  - `output/tools/benchmarks/community/local_integration_check`

5. Follow-up blocker discovered:
- Real canary run rows in this environment had `fastlm_present=false` + `status=error/exception_raised`, so those bundles are not organiser-valid under strict v1.1 gate.
- Next action:
  - investigate `_run_single_job` failure payload for the canary jobs and resolve fastlm/runtime setup before campaign submission dry-runs.
  - confirmed immediate root cause for failing canary job in this local run:
    - `ValueError` from path rendering in `sub_then_col` flow:
      - `'...output\\tools\\benchmarks\\periodic_sub_trans\\sub_then_col\\<run_id>' is not in the subpath of '...\\tools\\benchmarks'`
    - this needs a small path-relative fix in runner logging/output formatting (use repo-root-relative or safe fallback).

6. Follow-up fix + recheck (2026-02-28): pass.
- Applied fix:
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`
  - `_repo_root()` now returns repo root (`_ROOT`) instead of `parents[2]`.
- Added guard test:
  - `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py::test_sub_then_col_repo_root_matches_repo_root`
- Local rerun result (2-job canary shard including `sub_then_col`):
  - no `exception_raised` rows
  - `status=unsolved`, `stop_reason=time_cap_reached` for both rows (expected due 20s cap)
  - `run.log` contains zero `C:\\Users\\` path leaks
  - bundle validation passes (`require_fastlm_true=False`) for schema + integrity chain

7. FastLM strict-gate behavior fixed for timeout fallback rows (2026-02-28): pass.
- Applied fixes:
  - `tools/benchmarks/community/_run_single_job.py`
    - ensure both repo root and `src/` are on `sys.path` before fastlm probe.
  - `tools/benchmarks/community/run_shard.py`
    - timeout/error fallback rows now set `fastlm_present` using repo-aware fastlm detection.
- Added tests:
  - `tests/community/test_run_single_job_config_v1_1.py::test_run_single_job_helper_adds_src_import_path`
  - `tests/community/test_run_shard_v1_1.py::test_run_job_with_helper_timeout_preserves_fastlm_detection`
- Verified:
  - local smoke run with `time_cap_reached` row now has `fastlm_present=true`.
  - strict bundle validation (`require_fastlm_true=True`) passes.

8. `col_then_sub` non-p10 campaign tier filter fixed + full canary matrix recheck (2026-02-28): pass.
- Applied fix:
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/runner.py`
  - campaign config entrypoint now forces `TIERS_PERIOD_SWEEP=\"none\"` and `TIERS_MIN_COLUMNS=None`.
- Added test:
  - `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py::test_col_then_sub_campaign_config_disables_tier_sweep_filters`
- Verified:
  - prior period-11 `exception_raised` repro now resolves to one explicit tier without override failure.
  - local 8-cell canary matrix run (10s cap) produced:
    - `status_counts={\"unsolved\": 8}`
    - `stop_reason_counts={\"time_cap_reached\": 8}`
    - `error=0`
  - strict bundle validation (`require_fastlm_true=True`) passes.

9. Campaign result-integrity hardening (2026-02-28): pass.
- Applied fixes (`tools/benchmarks/community/run_shard.py`):
  - enforce returned row identity against scheduled manifest job keys (hard fail-to-row with `invalid_config` on mismatch),
  - resume guards for existing rows:
    - reject duplicate existing `job_id`,
    - reject existing `job_id` not in current shard,
    - reject existing row identity mismatch vs shard job payload,
  - `resume=False` now resets `run.log` and `run_meta.json` in addition to results files.
- Added tests:
  - `tests/community/test_run_shard_v1_1.py::test_run_shard_marks_identity_mismatch_as_invalid_config`
  - `tests/community/test_run_shard_v1_1.py::test_run_shard_resume_rejects_duplicate_existing_job_ids`
  - `tests/community/test_run_shard_v1_1.py::test_run_shard_resume_rejects_existing_job_not_in_shard`
  - `tests/community/test_run_shard_v1_1.py::test_run_shard_resume_false_resets_run_log_and_rows`
- Validation:
  - `tests/community/test_run_shard_v1_1.py` now passes with all new guards.

10. Full-cap canary matrix run (2026-03-01 UTC): pass (schema/integrity/privacy/fastlm gate).
- Run setup:
  - full 8-cell canary matrix (`p10..p11`, `c3..c4`, `col_then_sub` + `sub_then_col`)
  - cap `max_seconds_per_job=300`
  - resumable execution in 4 passes (`max_jobs=2`) against one bundle
- Final outcome:
  - `rows_total=8`
  - `status_counts={\"unsolved\": 8}`
  - `stop_reason_counts={\"time_cap_reached\": 8}`
  - `error=0`
  - `fastlm_present=true` for all rows
  - strict validator (`require_fastlm_true=True`) passed
  - `run.log` privacy check: no `C:\\Users\\` absolute-path leaks
- Bundle:
  - `output/tools/benchmarks/community/local_canary_fullcap_20260228T223633Z/run_bundle__community_bench_canary_v1_1_fullcap_20260228T223633Z__local_fullcap__canary_shard_00`
