# No-WLI Pipeline Hardening Backlog

Date: 2026-03-30

Purpose:
- define a concrete hardening plan for the no-WLI experiment loop while the
  current v42 width compare is running
- focus on reliability work that improves whether long runs are scientifically
  trustworthy
- ground the plan in the actual code surfaces that are still generating
  config/state/persistence bugs

Non-goals:
- this is not a broad rewrite proposal for the whole repo
- this is not a new science-study plan
- this does not change the currently running v42 compare

## 1. Why This Plan Exists

Recent work proved that several science studies were valid negatives, but it
also exposed a recurring reliability pattern:

- config and services are still carried through large mutable `state` bags
- experiment settings are defined and re-threaded in multiple places
- some telemetry exists in memory but is not always persisted into reviewable
  artifacts
- rerun control files can be reused accidentally
- runtime failures can invalidate a long compare before evidence is written

This means the main hardening goal is not "remove every bug." It is:

- make the no-WLI experiment loop dependable enough that a finished long run
  can be trusted as either:
  - a valid negative
  - a valid positive
  - or an explicitly invalid infrastructure failure

## 2. Current Smells Confirmed In Code

### 2.1 Matrix entry still starts from `globals()`

File:
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`

Observed shape:
- `main()` calls `_run_mainflow_impl(state=globals(), ...)`

Why this is risky:
- every top-level constant in the module becomes part of the runtime state
- it is easy for unrelated module data to become part of the effective config
- shape errors are discovered late, not at config resolution time

### 2.2 Matrix mainflow still consumes a broad mutable dict

File:
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`

Observed shape:
- `run_mainflow(...)` reads many values directly from `state[...]`
- optional behavior also uses permissive `state.get(...)`

Why this is risky:
- there is no single typed contract for matrix-level config
- entry, plan building, checkpointing, and job creation all depend on the same
  untyped bag

### 2.3 Runtime defaults still mutate a giant state bag and mirror shadow defaults

File:
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`

Observed shape:
- `initialize_runtime_state(...)` mutates a very large `state` mapping
- it also copies many values into `_..._DEFAULT` shadow keys

Why this is risky:
- later code can accidentally reset active state from shadow defaults
- config provenance becomes hard to trace
- it is easy to read the wrong layer and silently get the wrong value

### 2.4 Run-config emission is a second hand-threaded config surface

File:
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`

Observed shape:
- `build_run_config(...)` re-reads many `state[...]` keys and serializes them
  into nested config payloads

Why this is risky:
- config is merged in one place, then re-materialized in another
- if a new knob is threaded incorrectly, live behavior and saved config can
  diverge

### 2.5 Diagnostics persistence is still too manual

File:
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`

Observed shape:
- `build_stage3_diagnostics(...)` has a very large explicit parameter list
- downstream persistence paths still need those fields copied correctly into
  `stages.json`, `best_instance.json`, and `final_instances/...json`

Why this is risky:
- telemetry can exist in memory and still disappear from reviewer-facing files
- this already happened in Study 2 before the persistence fix

### 2.6 Control-file identity is still hand-maintained

File:
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`

Observed shape:
- `RUN_STATE_PATH`
- `RUN_EVENTS_PATH`
- `PLAN_OUTPUT_PATH`

These are still three separate hardcoded path constants.

Why this is risky:
- reruns can accidentally resume/skip against stale state
- we already saw this with the first Study 2 rerun attempt

## 3. Positive Patterns Already In The Repo

The plan should expand patterns that are already working.

### 3.1 Narrow data models already exist

File:
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`

Good pattern:
- `FixtureSpec`
- `NoWliFixtureJob`
- both are frozen dataclasses with explicit fields

### 3.2 Narrow bridge contracts already exist

File:
- `tools/benchmarks/periodic_sub_trans/no_wli/commit_bridge_state.py`

Good pattern:
- explicit allowed bridge keys
- explicit required runner services
- early validation before work begins

### 3.3 Science canaries are already proving real boundaries

Examples:
- `tests/tools/test_no_wli_stage3_entry_canary.py`
- `tests/tools/test_no_wli_phasec_start_policy_canary.py`
- `tests/tools/test_no_wli_phaseb_family_preservation_canary.py`

Good pattern:
- config resolution
- job materialization
- run-config / lock emission
- runtime/bridge acceptance

The hardening plan should generalize these patterns, not replace them.

## 4. Recommended Target Architecture

The right answer is not one giant dataclass for everything.

That would just move the blob around.

The better target is several small typed layers:

### 4.1 Matrix-level config object

Suggested name:
- `MatrixConfig`

Purpose:
- represent the hardcoded control knobs currently defined in
  `fixture_matrix_config.py`

Fields should cover:
- fixture selection
- schedule coverage mode
- seeds / offsets
- tuning preset ids
- wallclock / max-jobs / stop-on-error
- control-file experiment id

### 4.2 Matrix control-file object

Suggested name:
- `MatrixControlFiles`

Purpose:
- derive:
  - state path
  - events path
  - plan path
- from one single experiment id string

This removes the current "three separate path constants" failure mode.

### 4.3 Stage-3 tuning preset object

Suggested name:
- `Stage3TuningPreset`

Purpose:
- replace `dict[str, object]` preset payloads with a typed preset schema

This is especially important because Science Studies 1/2/3 all relied on
presets carrying the exact right override knobs.

### 4.4 Resolved run config object

Suggested name:
- `ResolvedRunConfig`

Purpose:
- hold the final merged runtime configuration after:
  - runtime defaults
  - profile defaults
  - fixture-matrix preset overrides

Hardening rule:
- merge once
- validate once
- freeze once
- serialize from this object
- do not silently reset values later

### 4.5 Runner services object

Suggested name:
- `RunnerServices`

Purpose:
- carry callbacks such as:
  - `write_json`
  - `_build_summary`
  - `_append_csv_row`
  - `_append_iteration_audit_row`
  - `_hash_payload`
  - `_sha256_file`
  - `_format_seconds`

This is the natural extension of the current
`commit_bridge_state.validate_commit_runner_state(...)` contract.

### 4.6 Stage-boundary payload objects

Suggested names:
- `PreStage3Payload`
- `Stage3DiagnosticsPayload`
- `CommitBridgePayload`

Purpose:
- make stage boundaries explicit
- stop passing broad mutable dicts between major pipeline phases

## 5. Hardening Principles

These should be treated as operating rules for future work.

1. Merge config once.
2. Validate config once.
3. Freeze config after resolution.
4. Pass typed objects forward, not `dict(state)` snapshots.
5. Unknown override keys fail early.
6. Critical fields do not use silent fallbacks.
7. Every science knob must appear in:
   - live behavior
   - saved `run_config.json`
   - reviewable artifacts when relevant
8. Control-file identity comes from one experiment id.
9. Infrastructure failures are recorded separately from science negatives.

## 6. Phased Backlog

### Phase 0. Immediate runtime trust blockers

Priority:
- blocks science directly

Goal:
- make long runs less likely to fail without evidence

Tasks:
- add a small GPU/accelerator preflight before long fixture-matrix runs
- fail early if CUDA is unavailable or poisoned instead of waiting for a
  mid-run `AcceleratorError`
- log the preflight result into the run-state / event stream

Target files:
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
- possibly a new helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runtime_preflight.py`

Meaningful tests:
- deterministic preflight unit test
- one fixture-matrix runtime test proving the preflight result is emitted

Success criterion:
- invalid hardware/runtime state becomes an explicit pre-run failure class

### Phase 1. Matrix config spine hardening

Priority:
- highest code-architecture blocker for future drift

Goal:
- remove `globals()` and replace matrix-entry config with typed objects

Tasks:
- define `MatrixConfig`
- define `MatrixControlFiles`
- load/construct them in `run_fixture_matrix.py`
- pass the typed config into `fixture_matrix_mainflow.py`
- keep a thin compatibility adapter only where needed during migration
- derive all three control files from one experiment id

Target files:
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`

Meaningful tests:
- config resolution test
- control-file derivation test
- active compare identity test
- rerun resume/skip identity test

Success criterion:
- matrix entry no longer depends on `globals()`
- one experiment id deterministically defines state/events/plan paths

### Phase 2. Tuning preset typing

Priority:
- high

Goal:
- stop science presets from being loose `dict[str, object]` bags

Tasks:
- define `Stage3TuningPreset`
- validate preset keys at load time
- convert preset application helpers to consume typed fields
- fail on unknown preset keys instead of carrying them forward loosely

Target files:
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`

Meaningful tests:
- unknown preset-key rejection
- preset round-trip serialization test
- canary proving preset changes show up in:
  - job materialization
  - run config
  - lock payload

Success criterion:
- a new study knob cannot silently leak through the system untyped

### Phase 3. Resolved runtime-config object

Priority:
- high

Goal:
- replace giant live `state` config reads with one validated resolved object

Tasks:
- define `ResolvedRunConfig`
- split service callbacks from configuration values
- migrate `run_config_builder.py` to serialize from `ResolvedRunConfig`
- reduce dependence on shadow `_DEFAULT` keys in `runner_state_defaults.py`

Target files:
- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/runtime_defaults.py`
- `tools/benchmarks/config/no_wli_pipeline_profiles.py`

Meaningful tests:
- resolved-config serialization test
- override precedence test
- proof that active runtime values and saved config stay aligned

Success criterion:
- live config and saved config come from the same resolved source of truth

### Phase 4. Stage-boundary payload hardening

Priority:
- high

Goal:
- stop passing broad stage/iteration dicts across boundaries

Tasks:
- formalize:
  - `PreStage3Payload`
  - `Stage3DiagnosticsPayload`
  - `CommitBridgePayload`
- move more boundary code toward the current
  `commit_bridge_state.py` model
- remove remaining wide `dict(state)` handoffs in hot experiment paths

Target files:
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_pre_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_contract.py`

Meaningful tests:
- payload-construction tests
- missing required field rejection tests
- real-path callback-chain canaries

Success criterion:
- stage boundaries fail early on shape errors and do not depend on broad mutable
  state bags

### Phase 5. Diagnostics persistence unification

Priority:
- high

Goal:
- one telemetry payload in memory should map consistently into all saved review
  artifacts

Tasks:
- define one serializer for stage diagnostics
- use it for:
  - `stages.json`
  - `best/best_instance.json`
  - `final_instances/...json`
- stop manual multi-path field threading where feasible

Target files:
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_commit.py`

Meaningful tests:
- persistence parity test across saved artifacts
- regression covering the Study 2 telemetry-loss bug class

Success criterion:
- if telemetry exists in memory, reviewer-facing files show it consistently

### Phase 6. Rerun hygiene and experiment identity

Priority:
- medium-high

Goal:
- make reruns explicit and hard to misfire

Tasks:
- derive control-file paths from a single id
- add a fixture-matrix canary that prints/proves the active:
  - seed set
  - preset ids
  - control-file id
- reject obviously stale control-file reuse when configured to be a fresh run

Target files:
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_runtime.py`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`

Meaningful tests:
- rerun identity canary
- stale control-file detection test

Success criterion:
- accidental "resume: skipping pre-completed jobs" becomes much less likely

### Phase 7. Lower-priority cleanup

Priority:
- can wait

Goal:
- reduce background drift risk after the experiment loop is dependable

Tasks:
- trim remaining non-hot-path `state.get(...)` drift surfaces
- continue replacing lower-value whole-state copies
- reduce `_DEFAULT` shadow-key sprawl further

Target files:
- `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_contract.py`
- nearby reporting/audit/orchestration helpers

Success criterion:
- fewer soft edges remain, but this phase should not block science once
  Phases 0-6 are healthy

## 7. What Blocks Science Versus What Can Wait

### Blocks science now

- Phase 0 runtime preflight
- Phase 1 matrix config spine hardening
- Phase 2 preset typing
- Phase 4 boundary payload hardening
- Phase 5 persistence unification
- Phase 6 rerun hygiene

These are the items that most directly decide whether a long run is valid,
auditable, and reproducible.

### Can wait after the loop is dependable

- large-scale cleanup of non-hot-path helpers
- broad `_DEFAULT` key reduction outside critical paths
- aesthetic config/API cleanup that does not change reliability

## 8. Suggested Execution Order

If this backlog is executed, the most effective order is:

1. Phase 0 runtime preflight
2. Phase 1 matrix config spine
3. Phase 6 rerun hygiene
4. Phase 2 preset typing
5. Phase 4 stage-boundary payloads
6. Phase 5 persistence unification
7. Phase 3 resolved run-config object
8. Phase 7 cleanup

Why this order:
- first stop invalid long runs
- then stop stale reruns
- then stop config drift
- then stop boundary/persistence bugs
- only after that do the larger config-object migrations

## 9. Minimum Canary Suite For Future Science Work

Before any future long science compare, the repo should have a short canary set
covering:

1. active fixture-matrix config identity
2. preset override application
3. run-config / lock payload parity
4. stage-boundary payload validity
5. diagnostics persistence parity
6. commit/resume bridge integrity
7. runtime preflight emission

Suggested anchor test files:
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
- `tests/tools/test_no_wli_stage3_entry_canary.py`
- `tests/tools/test_no_wli_phasec_start_policy_canary.py`
- `tests/tools/test_no_wli_phaseb_family_preservation_canary.py`
- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
- future:
  - `tests/tools/test_no_wli_run_preflight.py`
  - `tests/tools/test_no_wli_diagnostics_persistence_parity.py`
  - `tests/tools/test_no_wli_matrix_config_identity.py`

## 10. Practical Bottom Line

The user suspicion is directionally right:
- the repo does have too much messy shared config/state flow
- and that is a major source of repeated bugs

But the fix should not be:
- one giant config dataclass

The fix should be:
- several smaller typed config/state layers
- one experiment id for control files
- one resolved config source of truth
- narrow stage-boundary payloads
- one diagnostics serializer
- canaries that prove the experiment loop before each long run

That is the smallest hardening plan that directly reduces the bug classes that
have already interfered with science.

## 11. Status Update: First Hardening Slice Implemented

Date:
- 2026-03-30

Implemented in this slice:

1. Matrix entry no longer passes `globals()` into mainflow.
2. Fixture-matrix control files now derive from one experiment id.
3. The experiment id is now threaded into:
   - matrix-entry state
   - plan payload
   - run-state metadata
4. A runtime preflight boundary now exists for future long compares.

Concrete code changes:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
  - added `MatrixControlFiles`
  - added `FixtureMatrixMainflowConfig`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - added:
    - `CONTROL_FILES_BASE_DIR`
    - `EXPERIMENT_RUN_ID`
    - `MATRIX_CONTROL_FILES`
  - derived:
    - `RUN_STATE_PATH`
    - `RUN_EVENTS_PATH`
    - `PLAN_OUTPUT_PATH`
    from the single experiment id
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
  - added `build_matrix_mainflow_config()`
  - added `build_matrix_mainflow_state()`
  - removed the `state=globals()` mainflow entry path
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
  - narrowed the `state` contract from mutable mapping to mapping
  - added runtime-preflight execution and preflight-failure early write/abort
  - added experiment id and runtime-preflight metadata to run-state payloads
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan.py`
  - plan payload now records `experiment_run_id`
- `tools/benchmarks/periodic_sub_trans/no_wli/runtime_preflight.py`
  - new explicit preflight helper for torch/CUDA availability/smoke status

Meaningful proof:

- focused slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `25 passed`
- broader guard slice:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_runtime_preflight.py -q`
  - `35 passed`

What this slice closes:

- the matrix-entry `globals()` smell
- the three-separate-control-file-constants smell
- missing experiment identity in plan/run-state metadata
- absence of a pre-run torch/CUDA preflight boundary

What remains open from the backlog:

- typed Stage-3 tuning presets
- resolved runtime-config object
- wider stage-boundary payload hardening beyond commit bridge
- diagnostics persistence unification
- stronger rerun stale-state detection beyond derived control-file identity

This slice should be treated as:
- Phase 0 implemented
- Phase 1 implemented
- Phase 6 partially implemented

It is not the whole backlog yet, and it should not be described that way.

### 2026-03-30 second hardening slice landed: typed presets and stale-rerun guards

The second backlog slice is now implemented and proven.

Implemented:

- typed `Stage3TuningPreset` schema with strict normalization
- unknown preset-field rejection at the normalization boundary
- mainflow/state serialization of normalized preset payloads
- duplicate job-key rejection before checkpoint execution
- stale run-state rejection on:
  - `experiment_run_id` mismatch
  - `planned_job_keys_signature` mismatch
  - missing identity fields in an existing run-state file
- run-state identity persistence:
  - `planned_job_count`
  - `planned_job_keys_signature`
  - `run_state_version = "v2"`
- event-row identity persistence:
  - `experiment_run_id`
- plan payload identity persistence:
  - `planned_job_keys_signature`

Concrete code changes:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
  - added `Stage3TuningPreset.from_mapping(...)`
  - `FixtureMatrixMainflowConfig` now carries typed preset objects
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - added typed preset normalization
  - `_resolve_stage3_tuning_overrides_for_job(...)` now resolves via the typed preset
- `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
  - mainflow config now materializes normalized presets instead of raw config dicts
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_runtime.py`
  - added `planned_job_keys_signature(...)`
  - added duplicate-key guard
  - added experiment/signature stale-state rejection
  - now writes `run_state_version = "v2"` and persisted identity fields
  - event rows now carry `experiment_run_id`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
  - preflight-abort run-state now also records planned-job identity
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan.py`
  - plan payload now records `planned_job_keys_signature`
- `tests/tools/test_no_wli_fixture_matrix_hardening.py`
  - new proof slice for typed preset normalization and stale-rerun rejection

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py -q`
  - `38 passed`
- broader guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `45 passed`

What this slice closes:

- Phase 2 preset typing
- the most important remaining part of Phase 6 rerun hygiene
- the specific bug class where a reused run-state file can silently skip or
  intersect a different plan

What remains open after this slice:

- resolved runtime-config object
- broader stage-boundary payload typing beyond the matrix entry/commit bridge
- diagnostics persistence unification so stage telemetry does not need manual
  field threading across multiple artifact writers
- lower-priority cleanup of remaining non-hot-path mutable state surfaces

Status now:

- Phase 0 implemented
- Phase 1 implemented
- Phase 2 implemented
- Phase 6 substantially implemented

The backlog is still active, but the matrix-entry/preset/rerun trust boundary is
materially stronger than it was before this slice.

### 2026-03-30 third hardening slice landed: finalize-path persistence unification

The next hot-path persistence slice is now implemented and proven.

Implemented:

- one explicit `IterationPersistencePayload` serializer for finalize-path
  reviewer-facing enrichments
- centralized artifact enrichment for:
  - `target_key_idx`
  - `truth_diagnostics`
  - `word_ngram_report`
  - `stage2_topk_word_ngram_report`
  - `stage3_topk_word_ngram_report`
  - `stage35_archive`
  - `stage35_seed_rows`
  - `stage35_requested_cfg`
  - `stage35_proof_valid`
  - `stage35_proof_invalid_reason`
- centralized instance-row enrichment for:
  - word-ngram summary fields
  - truth-diagnostics summary fields
  - Stage-3.5 summary fields
- `iteration_finalize.py` now applies one persistence payload instead of
  manually threading these fields one by one

Concrete code changes:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_payload.py`
  - added `IterationPersistencePayload`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
  - finalize path now uses the shared persistence payload
- `tests/tools/test_no_wli_iteration_persistence_payload.py`
  - new targeted serializer proof

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_run_completion.py -q`
  - `7 passed`
- combined guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_hardening.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_fixture_matrix_mainflow.py tests/tools/test_no_wli_fixture_matrix.py tests/tools/test_no_wli_runtime_preflight.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_run_completion.py tests/tools/test_no_wli_stage3_entry_canary.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `52 passed`

What this slice closes:

- the exact finalize-path bug class where in-memory telemetry can be added to
  one artifact output but forgotten in another
- another chunk of Phase 5 diagnostics persistence unification

What remains open after this slice:

- resolved runtime-config object
- broader stage-boundary payload typing
- full persistence unification for non-finalize paths such as auxiliary/guard
  flows and any remaining duplicated stage diagnostics writers
- lower-priority cleanup of non-hot-path mutable state surfaces

Status now:

- Phase 0 implemented
- Phase 1 implemented
- Phase 2 implemented
- Phase 5 partially implemented
- Phase 6 substantially implemented

This still does not mean the whole backlog is done, but the finalize-path
review artifacts now rely on one persistence serializer instead of scattered
manual field threading.

### 2026-03-30 fourth hardening slice landed: explicit Phase-C policy and novelty diagnostics

Why this counts as hardening:

- the `411` novel-start study needed new Phase-C telemetry
- without explicit persistence, the study would have risked another
  "operationally changed, scientifically ambiguous" outcome
- a real pre-existing trust gap was also closed:
  - `phaseC_start_policy` itself was not being persisted in
    `stage3_diagnostics`

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
  - explicit `novel_challenger_v1` return fields
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - explicit state threading for the new Phase-C policy and novelty counters
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - explicit diagnostics wiring
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
  - explicit persistence schema additions

Hardening effect:

- no new dict-only side channel was introduced
- no monkey-patch/shim layer was introduced
- reviewer-facing artifacts can now distinguish:
  - policy selected no eligible novel challengers
  - policy found eligible challengers but selected none
  - policy selected challengers into real starts

Evidence:

- `tests/tools/test_no_wli_stage3_phasec.py`
  - deterministic start-set change under `novel_challenger_v1`
- `tests/tools/test_no_wli_truth_diagnostics.py`
  - persisted novelty fields survive `build_stage3_diagnostics(...)`
- `tests/tools/test_no_wli_phasec_start_policy_canary.py`
  - config / lock / runtime surfaces stay explicit

### 2026-03-30 fifth hardening slice landed: Phase-C diagnostics contract and finalize-path proof

Why this slice mattered:

- the `v43` study depends on new Phase-C novelty telemetry
- before this slice, the pipeline still had one fail-open path:
  - `iteration_post_stage3.py` could silently default missing Phase-C /
    novel-start diagnostics to zeros or empty strings
- builder-level persistence was already covered, but the real finalize-path
  artifact build still needed explicit proof with the new fields

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/phasec_diagnostics_contract.py`
  - explicit required-key contract for:
    - Phase-C diagnostics when Phase-C ran
    - novelty diagnostics when `novel_challenger_v1` ran
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  - validates two-phase follow-up payloads before default-based copying
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - validates Phase-C diagnostics before building reviewer-facing outputs
- `tests/tools/test_no_wli_phasec_diagnostics_contract.py`
  - direct contract coverage
- `tests/tools/test_no_wli_iteration_finalize_word_ngram.py`
  - finalize-path proof now covers the new novelty fields end to end

Hardening effect:

- removed another silent-drop class from the Phase-C artifact path
- ensured missing novel-start telemetry now fails early instead of degrading to
  innocuous-looking zeros
- kept the change contract-oriented rather than adding another monkey patch,
  shim, or local override path

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `41 passed`
- broader guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `101 passed`

What this closes:

- the remaining trust gap where a future `v43`-style run could appear
  operationally negative simply because the new novelty diagnostics had been
  dropped or defaulted late in the artifact path

What remains open after this slice:

- resolved runtime-config object
- broader stage-boundary payload typing outside the current hot path
- full persistence unification for remaining non-finalize / auxiliary flows
- lower-priority cleanup of mutable-state surfaces that are not currently
  distorting science readouts

### 2026-03-30 sixth hardening slice landed: Stage-3 config bridge forwarding

Why this slice mattered:

- the first live `v43` novel-start compare failed before producing any science
  readout
- both jobs crashed with:
  - `KeyError: 'STAGE3_PHASEC_START_POLICY'`
- run-config emission was already correct, so the bug class was:
  - config present in saved config/locks
  - but missing from live per-iteration Stage-3 state

Root cause:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
  builds a narrowed `stage3_state`
- that bridge was forwarding:
  - base iteration fields
  - `STAGE35_ENABLED`
  - `STAGE35_CFG`
- but it was not forwarding:
  - `STAGE3_PHASEC_START_POLICY`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  later requires that key directly

Implemented:

- added explicit Stage-3 config allowlist in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
- `_build_stage3_state(...)` now forwards:
  - `STAGE3_PHASEC_START_POLICY`
- strengthened live-bridge regression coverage in:
  - `tests/tools/test_no_wli_stage_engine_iteration_bridge.py`

Hardening effect:

- closes another concrete mutable-state/bridge drift bug class
- ensures a study-semantic Phase-C policy can no longer exist in
  `run_config.json` while still being absent from the live Stage-3 iteration
  state
- keeps the fix explicit and contract-like rather than adding a late fallback,
  monkey patch, or local shim

Meaningful proof:

- focused regression:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `26 passed`
- broader guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `108 passed`

Status impact:

- this closes another hot-path Stage-3 boundary bug
- the next clean long compare is the same novel-start study re-armed on fresh
  control files
- it also strengthens the case for continuing Phase 4-style boundary typing as
  part of the remaining backlog

### 2026-03-30 seventh hardening slice landed: unify Stage-3 runtime-state contract across both live paths

Why this slice mattered:

- the first `v43` failure showed one Stage-3 bridge was missing
  `STAGE3_PHASEC_START_POLICY`
- the fresh `v44` rerun proved that fix alone was insufficient:
  the fixture-matrix live path still failed with the same `KeyError`
- this exposed a second, earlier boundary bug:
  - the matrix runtime's typed config/state path had never carried the Phase-C
    start policy at all

Root cause:

- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_builder.py`
  was constructing `IterationMatrixConfig` without a
  `stage3_phasec_start_policy` field
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
  then built stage-engine iteration state without the policy
- so the live matrix path still dropped the policy before
  `stage3_iteration_flow.py` executed

Implemented:

- added shared Stage-3 runtime-state contract:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_state_contract.py`
- wired the lower bridge through the shared contract:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_engine_iteration_bridge.py`
- extended the matrix typed config:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_builder.py`
- added matrix-path regression coverage:
  - `tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py`

Hardening effect:

- the Phase-C start policy is now part of the typed live matrix config, not
  just ambient mutable state
- both live Stage-3 entry paths now depend on the same explicit runtime-state
  contract
- this closes the exact bug class where a setting exists in:
  - fixture preset
  - run config
  - lock payload
  but still disappears before live Stage-3 execution

Meaningful proof:

- focused:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_fixture_matrix_runtime.py -q`
  - `34 passed`
- broader guard:
  - `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_phasec_start_policy_canary.py tests/tools/test_no_wli_stage3_phasec.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_iteration_finalize_word_ngram.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_periodic_sub_trans_runner_scorer_impl.py tests/tools/test_no_wli_iteration_persistence_payload.py tests/tools/test_no_wli_run_config_span_aux.py tests/tools/test_no_wli_phaseb_family_preservation_canary.py -q`
  - `116 passed`

### 2026-03-31 New hardening item: reviewer-facing exposure of high-truth challenger paths

`v45` exposed a real adequacy gap in the current artifact/reporting layer.

What is happening:

- `phasec_start_checkpoints.jsonl` records true per-start truth-match values
- but top-level run summaries still surface only the score-selected winning path
- so a materially higher-truth Phase-C challenger can be explored and persisted
  without changing top-level `best_match_ratio`

Concrete evidence:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/20260331T075915341627Z__bench_solve_pipeline_no_wli__55b7159/phasec_start_checkpoints.jsonl`
  shows:
  - `candidate_hash = 9002ee09917e5a0d`
  - `final_match = 0.418`
  - `final_score = 0.17284542866740327`
- the same run's top-level artifact still reports:
  - `best_match_ratio = 0.041`
  - because the score-selected winner was:
    - `candidate_hash = 73eee2bf84b7c07f`
    - `final_match = 0.039`
    - `final_score = 0.19101667350788198`

Why this matters:

- this is not a pipeline correctness failure
- but it is a scientific-visibility failure
- it makes reviewer-facing summaries understate explored challenger quality and
  can obscure whether a study changed the truth-strong downstream path

Recommended hardening response:

- persist a reviewer-facing “max explored Phase-C truth” summary alongside the
  score-selected winner
- persist the best truth challenger hash/source/rank when it differs from the
  score-selected winner
- keep this additive only; do not change current score-selected winner semantics
  as part of the reporting fix

### 2026-03-31 hardening slice closed: benchmark disagreement reporting and replay-fixture capture for late-stage frontier analysis

This slice is now implemented.

Closed items:

- additive benchmark disagreement reporting for Phase-C explored starts:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_reporting.py`
  - threaded into:
    - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_outcome.py`
- benchmark truth-gap dataset/export support:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_phasec_truth_gap_dataset.py`
- replay-fixture capture/export scaffold for future late-stage scorer tests:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_frontier_fixture.py`
- Phase-C replay-capture fields made explicit in live summaries:
  - `init_key_idx`
  - `init_plaintext_idx`
  - `final_key_idx`
  - `final_plaintext_idx`
- replay-material completeness enforced in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_diagnostics_contract.py`

Why this counts as hardening:

- benchmark runs no longer have to hide score-vs-truth disagreement behind only
  the score-selected winner
- late-stage frontier capture now has an explicit contract rather than an
  ad-hoc best-effort path
- future scorer experiments can replay real explored-frontier rows without
  inventing local shims or one-off fixture formats

Meaningful proof:

- focused replay/reporting slice:
  - `25 passed`
- broader guard slice:
  - `59 passed`

Remaining open point:

- historical `v45` artifacts remain replay-material incomplete because they
  were created before the new key/plaintext capture fields existed
- one fresh comparable run is still required to produce a fully replayable
  frontier fixture

Status:

- this closes the reporting-side hardening needed to expose benchmark
  disagreement cleanly
- it does not yet close the wider backlog item of unifying all late-stage
  persistence under one typed object
