# No-WLI Pipeline Hardening Review

Date: 2026-03-25
Scope: live commit / handoff emission, resumed-live parity, and nearby
state-plumbing risks in the no-WLI pipeline.

## Findings

### 1. Critical: commit handoff contract was implicit and too wide

Observed failures:

- live `seed211` reruns completed the solve path and then crashed at commit with
  `KeyError: 'base'`
- after one local fix, the next rerun crashed at the same boundary with
  `KeyError: 'write_json'`

Root cause:

- the commit path allowed a sparse per-iteration `bridge_state` to stand in for
  the full runner state
- `bridge_state` is only meant to carry live handoff payloads:
  - `stage2_resume_live`
  - `stage3_prep_live`
- but the bridge was effectively being treated as a general-purpose state bag,
  so runner services like `base`, `write_json`, summary builders, hashers, and
  snapshot writers could disappear at commit time

Why this matters:

- this is the exact bug class that blocked live handoff emission
- it also made narrow helper tests look green while the real callback path was
  still wrong

Current status:

- fixed in code by:
  - merging sparse bridge overrides onto the full runner state
  - extracting only explicit live handoff payloads at the caller
  - rejecting unexpected bridge override keys
  - validating that required commit runner services are present and callable

### 2. High: `iteration_post_stage3` was still passing the whole iteration state

Observed code shape before the fix:

- `iteration_post_stage3.py` passed `bridge_state=dict(state)` into the commit
  callback

Why this is risky:

- even after the merge fix, passing the entire iteration state keeps the bridge
  contract loose
- any future key collision between iteration-local data and runner services can
  silently shadow the commit path
- this recreates the same bug class in a subtler way

Current status:

- fixed in code by extracting a minimal bridge payload containing only:
  - `stage2_resume_live`
  - `stage3_prep_live`

### 3. Medium: callback and state contracts are cleaner, but still dict-based

Evidence:

- runner services are still carried through large mutable dictionaries instead
  of a typed service object

Why this matters:

- the pipeline is currently relying on shape conventions across many files
- those conventions are easy to break when refactoring, because nothing close to
  the boundary declares the full required contract

What is fixed:

- the commit bridge now validates required runner services before commit work
  begins, so missing or non-callable services fail early with a clear contract
  error instead of surfacing later as `KeyError` crashes
- `finalize_iteration_and_commit` now forwards `bridge_state` explicitly when
  present; the hot path no longer relies on per-call signature reflection

Not fixed yet:

- the code is safer than before, but the broader runner-service model is still
  dict-based

### 4. Medium: the stage-engine path had the same whole-state leak pattern

Observed code shape before the fix:

- `iteration_matrix_flow.py` built `stage_engine_state` with `dict(locals())`
- `stage_engine_iteration_bridge.py` copied broad outer state bags and then
  mutated them into stage-local state

Why this matters:

- that stage-engine path is not the same failing live handoff path, but it uses
  the same general pattern: copy a large generic state bag and rely on shape
  conventions
- this is the same architectural smell that caused the commit failures

Why this matters:

- unrelated runner-loop objects and helpers could cross the stage boundary even
  when the stage code did not actually need them
- this is the same class of bug that made the commit path brittle

Current status:

- fixed in code by replacing those wide copies with explicit state builders for:
  - pre-stage3 state
  - stage3 state
  - finalize/post-stage3 state

### 5. Medium: `REQUIRE_BATCH_SCORING` was silently dropped on the iteration-matrix path

Observed issue:

- `iteration_post_stage3.py` reads `state.get("REQUIRE_BATCH_SCORING", True)`
- but the old `iteration_matrix_flow.py` never propagated that field into the
  finalize-state payload
- result: this path silently defaulted to `True` regardless of runner config

Why this matters:

- final word-ngram/truth scoring and related downstream reporting could run with
  a different batch requirement than the rest of the live pipeline

Current status:

- fixed in code by threading `require_batch_scoring` through
  `IterationMatrixConfig` and into the explicit finalize-state builder
- fixed in code by removing the last silent default in
  `iteration_post_stage3.py`; finalize now reads `REQUIRE_BATCH_SCORING` as a
  required contract value on the live path

### 6. Low: stage-engine contract artifact generation had a lower-risk broad state copy

Observed code shape:

- `stage_engine_contract.py` still uses `profile_state = dict(state)` in
  `build_no_wli_stage_specs_from_profile`

Why this matters:

- it is outside the hot live commit path, so this is not the current blocker
- but it is the same general code smell: copy a broad state bag when only a
  narrow subset is really needed

Current status:

- fixed in code by narrowing the profile-overlay state to the exact stage-spec
  fields that builder actually needs
- a dedicated regression now proves stage2/stage3 override values still survive
  without carrying unrelated state through the profile overlay

### 7. Medium: runtime reliability is still only partially proven

What is true:

- targeted no-WLI regression slices are green after the hardening changes
- resumed `seed411` ranking probe now runs to completion

What is not yet proven:

- a fresh live `seed211` run completing end-to-end with the new stricter bridge
  contract loaded from process start
- correct `resume_handoffs/.../manifest.json` emission showing
  `stage2_to_stage3.source = "live_stage3_pipeline"`

Why this matters:

- the active live rerun that was already in memory before the latest bridge
  tightening cannot validate the new code path

## Changes Already Made

### Commit-path hardening

- added explicit commit bridge helpers in
  `tools/benchmarks/periodic_sub_trans/no_wli/commit_bridge_state.py`
- runner-side commit resolution now merges sparse bridge payloads onto the full
  runner state in `tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py`
- `iteration_post_stage3.py` now passes only explicit live handoff payloads
- commit bridge resolution now validates required runner services before commit
  work begins
- `iteration_finalize.py` now forwards `bridge_state` explicitly instead of
  using runtime signature inspection

### Earlier related hardening

- fixed repo-relative scorer asset resolution for resumed/offline scripts
- fixed repo-root output-root resolution for offline/replay scripts
- added more real callback-path regressions around live resume handoff emission
- replaced stage-engine `locals()` / wide state copies with explicit state builders
- fixed iteration-matrix propagation of `REQUIRE_BATCH_SCORING`
- removed the remaining `REQUIRE_BATCH_SCORING` silent default from the
  finalize/post-stage3 live path
- hardened Stage1/Stage2 boundary contracts in
  `tools/benchmarks/periodic_sub_trans/no_wli/stage12_pipeline.py`
  so missing or wrong-shaped stage payloads fail immediately
- removed the mirrored Stage1/Stage2 silent defaults from
  `tools/benchmarks/periodic_sub_trans/no_wli/iteration_pre_stage3.py`
- tightened progress accounting in
  `tools/benchmarks/periodic_sub_trans/no_wli/run_progress.py`
  so unknown status keys no longer pass silently
- tightened late commit payload access in
  `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_commit.py`
  so required artifact/instance fields are treated as required
- tightened Stage-3 tuning preset resolution in
  `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  so unknown non-`base` preset IDs fail instead of silently degrading to an
  empty preset
- tightened internal summary/completion paths in
  `tools/benchmarks/periodic_sub_trans/no_wli/run_summary.py` and
  `tools/benchmarks/periodic_sub_trans/no_wli/run_completion.py`
  so live instance rows and status counts are treated as required contracts
- tightened the runner/config contract further in:
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_bindings.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/commit_bridge_state.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_bridges.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_builder.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/setup_logging_payload.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage3_iteration_flow.py`
  so that:
  - `_format_seconds` is now an explicit installed runner service instead of a
    hidden bridge fallback
  - commit bridge validation covers both required services and required
    non-callable values such as `SAVE_RESUME_HANDOFFS`
  - Phase-C / Stage35 / word-ngram / span-aux settings are now read as required
    runner defaults on the live path instead of silently degrading through
    `.get(...)` defaults

### Latest cross-check result

What was reviewed next:

- runner service installation vs. downstream assumptions
- live Stage-3 runtime call-context construction
- iteration-matrix config shaping
- run-config / setup-logging materialization

What was found:

- one more real hidden contract remained at commit:
  - commit formatting still fell back internally if `_format_seconds` was
    missing
- several central config readers still used permissive `.get(...)` defaults for
  keys that are already installed by the runner default layer

Why this matters:

- those defaults reduce confidence because a broken runner state can keep
  limping forward with altered behavior instead of failing at the boundary where
  the shape mismatch first appears

Current status:

- fixed in code by making `_format_seconds` part of the explicit runner-service
  contract
- fixed in code by removing the remaining defaulted reads for:
  - resume-handoff enablement at commit
  - Phase-C config in live runtime wiring
  - Stage35 config in live runtime wiring
  - word-ngram and span-aux config in run-config emission
  - Phase-C / Stage35 logging payload emission

Residual risk still worth tracking:

- `stage3_iteration_flow.py` still accepts a broad set of optional keys from
  helper return payloads such as `stage3_prep`, `two_phase_followup`, and
  `stage35_followup`
- some of those defaults are intentional for optional telemetry, but that
  boundary is still softer than the now-hardened Stage1/Stage2 and commit
  contracts
- that is the next most likely place for a subtle live/plumbing bug to hide

## Regression Coverage

Useful current checks:

- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
  - real commit callback path
  - sparse live bridge state
  - unexpected bridge-key rejection
  - missing/non-callable runner-service rejection
- `tests/tools/test_no_wli_stage_engine_contract.py`
  - profile-overlay stage specs still preserve required stage2/stage3 override
    values without copying unrelated state
- `tests/tools/test_no_wli_stage_engine_iteration_bridge.py`
  - real stage-engine path
  - proves unrelated outer state keys do not leak into stage3 state
- `tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py`
  - proves iteration-matrix state is filtered to an explicit contract
  - proves `REQUIRE_BATCH_SCORING` now reaches finalize-state correctly
- `tests/tools/test_no_wli_output_root_paths.py`
  - repo-root output anchoring for offline scripts
- `tests/tools/test_no_wli_stage12_pipeline.py`
  - missing-key and wrong-shape rejection for Stage1/Stage2 return payloads
- `tests/tools/test_no_wli_stage_iteration_commit.py`
  - commit path rejects missing required artifact fields instead of silently
    fabricating defaults
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - unknown Stage-3 tuning preset IDs now fail early
- `tests/tools/test_no_wli_run_summary.py`
  - internal live summary rows now use explicit required fields
- `tests/tools/test_no_wli_run_completion.py`
  - completion path rejects incomplete status-count payloads
- `tests/tools/test_no_wli_runner_bindings_commit_bridge.py`
  - runner module exposes the installed `_format_seconds` service
- `tests/tools/test_no_wli_run_config_span_aux.py`
  - run-config builder now fails fast if required span-aux / Phase-C keys are
    missing from runner state
- resumed artifact tests and probe-script tests
  - ensure resumed entrypoints still start and serialize properly
- oracle/progress tests
  - unknown status keys now fail early in manifest checkpointing

Latest focused validations:

- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
- `tests/tools/test_no_wli_runner_bindings_commit_bridge.py`
- `tests/tools/test_no_wli_run_config_span_aux.py`
- `tests/tools/test_no_wli_setup_logging.py`
  - `15 passed`

- `tests/tools/test_no_wli_fixture_matrix_runtime.py`
- `tests/tools/test_no_wli_stage_engine_iteration_bridge.py`
- `tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py`
- `tests/tools/test_no_wli_stage3_phasec.py`
- `tests/tools/test_no_wli_run_config_span_aux.py`
- `tests/tools/test_no_wli_setup_logging.py`
- `tests/tools/test_no_wli_resume_handoff_artifacts.py`
- `tests/tools/test_no_wli_runner_bindings_commit_bridge.py`
  - `49 passed`

## Recommended Next Steps

1. Fresh live canary:
   rerun single-seed `seed211` after the new bridge-contract code is loaded
   from process start, then verify `resume_handoffs/.../manifest.json`.

2. Replace runtime signature inspection in `finalize_iteration_and_commit`:
   done; keep the callback contract explicit and avoid reintroducing reflective
   forwarding.

3. Keep replacing helper-only tests with real-path tests:
   for plumbing bugs, the minimum standard should be one regression that
   exercises the actual callback chain where the production failure happened.

4. Keep trimming lower-risk broad state copies outside the hot path when there
   is test coverage to support it.

5. Consider replacing the remaining untyped runner-service dictionaries with a
   narrower typed service object once the current live handoff canary is green.

## Current Confidence

Confidence is improving, but the no-WLI pipeline is not yet generally proven.

The strongest current claim is:

- the specific live handoff commit bug class is now fixed more holistically than
  before
- the resumed/offline path bugs seen this week are fixed and covered

The strongest current uncertainty is:

- fresh end-to-end live confirmation is still required after the latest commit
  bridge tightening
