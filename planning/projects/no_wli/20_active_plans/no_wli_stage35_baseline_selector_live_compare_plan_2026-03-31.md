# No-WLI Stage 3.5 Baseline Selector Live Compare Plan

## Purpose

This plan locks the next live scorer-facing experiment to one narrow boundary:

- choose which already-explored Phase-C row becomes the Stage 3.5 baseline

It explicitly does **not** broaden into a general live late-selector rewrite.

## Maintained mechanism

The current maintained mechanism from `v45` + `v46` is:

- frozen frontier ranking failure exists
- `score + novelty` rescues that failure on the replay-ready frontier
- the rescued challenger is admitted by Stage 3.5
- that admitted path continues to a materially better downstream result

So the live question is now:

> does changing only the Stage 3.5 baseline row from `legacy` to
> `score_plus_novelty` improve live continuation on the same `411`-style case?

## Narrow intervention boundary

Keep fixed:

- seed family
- upstream search
- Phase-B width
- Phase-C start policy
- Stage 3.5 search semantics
- Stage 3.5 config values

Change only:

- `STAGE35_BASELINE_SELECTOR`

Allowed values:

- `legacy`
- `score_plus_novelty`

## Implementation contract

The live implementation must:

- use a small shared selector core, not the benchmark harness directly
- consume only live-available Phase-C frontier fields
- preserve explicit config plumbing through:
  - runtime defaults
  - runner state
  - fixture-matrix preset overrides
  - iteration matrix config
  - Stage 3 runtime contract
  - run config / lock payload
- persist the Stage 3.5 baseline-selection reporting fields in
  `stage3_diagnostics`

## Required reporting

Each run must persist:

- `stage35_baseline_selector`
- `stage35_baseline_candidate_hash`
- `stage35_baseline_candidate_source`
- `stage35_baseline_candidate_lane`
- `stage35_baseline_candidate_source_rank`
- `stage35_baseline_candidate_final_score`
- `stage35_baseline_candidate_final_match` when truth exists
- `stage35_phasec_score_winner_candidate_hash`
- `stage35_phasec_score_winner_candidate_source`
- `stage35_phasec_score_winner_candidate_lane`
- `stage35_phasec_score_winner_candidate_final_score`
- `stage35_phasec_score_winner_candidate_final_match` when truth exists
- `stage35_baseline_differs_from_phasec_score_winner`
- existing Stage 3.5 result fields:
  - accept / reject
  - accept reason
  - best continued hash
  - best continued truth / score
  - truth gain vs selected row
  - truth gain vs Phase-C score winner

## Run sequence

### Step 1

Short canary pair:

- control:
  - `legacy`
- candidate:
  - `score_plus_novelty`

Purpose:

- prove the selector mode switches cleanly
- prove reporting is complete
- prove Stage 3.5 runs without breaking the pipeline

### Step 2

Only if the canary is clean, switch to the overnight pair:

- control:
  - `legacy`
- candidate:
  - `score_plus_novelty`

Same seed family and same search semantics, only the Stage 3.5 baseline selector
changes.

## Canary pass criteria

The canary passes only if:

- selector mode differs between the two jobs
- saved reporting fields are populated
- Stage 3.5 runs cleanly
- selected Stage 3.5 baseline row differs when the frontier supports it
- no unrelated search semantics changed

## Implementation status

Implemented:

- shared live-safe selector core:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_core.py`
- explicit config/runtime plumbing for:
  - `STAGE35_BASELINE_SELECTOR`
- persisted Stage 3.5 baseline-selection reporting in:
  - `stage3_diagnostics`
- fixture-matrix preset overrides for:
  - canary pair
  - overnight pair

Current active matrix mode:

- `canary` in the running process
- on-disk config is now pre-armed for:
  - `overnight`
  so the next invocation can launch immediately after a clean canary

Current active compare:

- control:
  - `stage35_baseline_legacy_canary_p9`
- candidate:
  - `stage35_baseline_score_plus_novelty_canary_p9`

Prepared next compare after a clean canary:

- control:
  - `stage35_baseline_legacy_live_p9`
- candidate:
  - `stage35_baseline_score_plus_novelty_live_p9`

Meaningful proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_stage3_phasec.py -q`
- `83 passed`

## Canary follow-up

The first canary launch correctly exposed one missing live-path contract:

- `emit_setup_logging()` did not yet accept
  `stage35_baseline_selector`

This was a real pipeline omission, not a science failure.

Fix:

- `tools/benchmarks/periodic_sub_trans/no_wli/setup_logging.py`
  now accepts and prints `stage35_baseline_selector`
- `tests/tools/test_no_wli_setup_logging.py`
  now guards that signature explicitly

Updated proof:

- `C:\Python\Python311\python.exe -m pytest tests/tools/test_no_wli_setup_logging.py tests/tools/test_no_wli_fixture_matrix_runtime.py tests/tools/test_no_wli_stage35_substitution_solver.py tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py tests/tools/test_no_wli_truth_diagnostics.py tests/tools/test_no_wli_phasec_diagnostics_contract.py tests/tools/test_no_wli_stage_engine_iteration_bridge.py tests/tools/test_no_wli_artifact_resume.py tests/tools/test_no_wli_stage3_phasec.py -q`
- `84 passed`

Overnight automation:

- a detached watcher now waits for the active canary process to exit
- if the canary state and event files show a clean pass, it launches the
  overnight pair automatically
- watcher log:
  - `planning_old/working/no_wli_stage35_canary_watch_2026-03-31.log`

## Overnight readout

Read the overnight result at three levels:

1. selection
   - did the Stage 3.5 baseline row change?
2. admission
   - did Stage 3.5 accept / reject differently?
3. continuation
   - did downstream truth or score improve?

## Guardrails

Do not:

- mix in width changes
- mix in Phase-C start-policy changes
- mix in new scorer feature families
- mix in semantic/plaintext live feature work
- widen the experiment into a general scorer rewrite

This plan is only about:

- Stage 3.5 baseline row selection from an already-built Phase-C frontier

## 2026-04-01 canary reset after the silent post-Phase-C stall

The repaired `v47` canary should now be treated as invalid for scheduling
purposes.

What happened:

- the run completed Phase C cleanly
- logging stopped immediately after:
  - `stage3-phaseC ... best_match=0.726 best_score=0.279830`
- no run artifact in the active run dir advanced after that checkpoint
- the Python process kept consuming CPU for hours

Current reading:

- this was not a lost Phase-C heartbeat
- it was a silent Stage 3.5 followup / immediate post-Phase-C burn
- the original canary preset was too heavy to function as a real canary

Fixes now applied:

- Stage 3.5 emits explicit:
  - `stage35-start`
  - `stage35-heartbeat`
  - `stage35-finish`
- canary-only Stage 3.5 search budget is reduced to a true plumbing canary
- canary-only late search budgets are reduced
- fresh canary experiment id is now:
  - `tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job`
- on-disk compare mode is reset to:
  - `canary`

Current run order:

1. rerun the reduced `v49` canary pair
2. require clean selector/admission persistence plus visible Stage 3.5 progress
3. only then switch back to the overnight `v48` compare

Operational handoff now armed:

- watcher script:
  - `planning_old/working/no_wli_stage35_v49_watch_and_launch_2026-04-01.ps1`
- watcher log:
  - `planning_old/working/no_wli_stage35_v49_watch_2026-04-01.log`

Watcher behavior:

- monitor the active `v49` state/events files
- only if `v49` completes cleanly:
  - switch `fixture_matrix_config.py` from `canary` to `overnight`
  - launch the `v48` real compare
- if `v49` fails or stops early:
  - do not launch the overnight run

Overnight console/log handoff:

- the real run is launched in a visible PowerShell window
- its stdout/stderr is tee'd to:
  - `planning_old/working/no_wli_stage35_v48_overnight_console_2026-04-01.log`
- this preserves live console visibility while also saving a file copy

## 2026-04-01 state after `v49` completion

`v49` has now completed cleanly and served its intended gate role.

Summary:

- both canary jobs completed
- both Stage 3.5 lanes returned and persisted diagnostics
- the `score_plus_novelty` lane selected a different Stage 3.5 baseline row
- but both reduced-budget canary lanes still failed the Stage 3.5
  `search_score_drop_guard`

So the maintained reading is:

- the live boundary is now trusted
- the reduced canary was strong enough to validate plumbing
- the real science question remains the full `v48` compare

Current overnight status:

- `v48` was auto-launched after the clean canary pass
- matrix state still shows job 1 in progress until the first job boundary is
  crossed
- ongoing progress for job 1 is visible in:
  - `planning_old/working/no_wli_stage35_v48_overnight_console_2026-04-01.log`
- because Stage 3.5 writes no mid-stage artifact files, the console log is the
  main live source once Phase C has finished

## 2026-04-02 live compare readout and revised execution plan

`v48` only completed the legacy long lane before the wallclock cap fired.

Observed outcome:

- completed long lane:
  - `stage35_baseline_legacy_live_p9`
- unrun lane:
  - `stage35_baseline_score_plus_novelty_live_p9`
- legacy Stage 3.5 outcome:
  - `stage35_accept_passed = 0`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_best_match = 0.038`
  - top-level `best_match_ratio = 0.041`

Operational lesson:

- the Stage 3.5 hook and telemetry are now good enough
- the overnight 2-job structure is not compatible with the current wallclock
  cap for this workload

Revised next step:

1. keep the completed `v48` legacy long lane as the locked live baseline
2. do not rerun the same 2-job overnight shape under the same cap
3. run the missing full-budget `stage35_baseline_score_plus_novelty_live_p9`
   lane as a fresh 1-job compare
4. compare that result directly against the completed legacy long lane

Active execution config:

- mode:
  - `candidate_single`
- experiment id:
  - `tune_v50_p9c3_seed411_stage35_baseline_selector_candidate_live_single_1job`
- preset:
  - `stage35_baseline_score_plus_novelty_live_p9`

Readout contract for that 1-job candidate lane:

1. did it choose a different Stage 3.5 baseline row?
2. did Stage 3.5 admission change?
3. did downstream continuation beat the locked `v48` legacy long lane?

Decision boundary after the 1-job candidate run:

- if the candidate lane changes Stage 3.5 admission and improves downstream
  continuation, the live mechanism win is confirmed
- if it does not, the replay-proven mechanism remains real but does not yet
  transfer cleanly into the full live job under current settings

