# Stage 3.5 baseline-selector live compare summary

Date: `2026-04-02`

## Scope

This note summarizes the first live Stage 3.5 baseline-selector study after the
selector hook and Stage 3.5 telemetry hardening.

Tested mechanism:

- choose the Stage 3.5 baseline row from the already-built Phase C frontier
- compare:
  - `legacy`
  - `score_plus_novelty`
- keep upstream search and Stage 3.5 search semantics fixed

## Runs covered

### `v49` reduced canary

Experiment id:

- `tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job`

Status:

- completed jobs: `2 / 2`
- stopped early: `0`
- purpose: validate live selector switching, Stage 3.5 execution, and saved
  diagnostics

### `v48` overnight live compare

Experiment id:

- `tune_v48_p9c3_seed411_stage35_baseline_selector_live_compare_2job`

Status:

- completed jobs: `1 / 2`
- remaining jobs: `1`
- stopped early: `1`
- reason: fixture-matrix wallclock cap reached after the legacy lane

## Main findings

### 1. `v49` is a clean plumbing/contract pass

The reduced canary did what it needed to do:

- the candidate lane selected a different Stage 3.5 baseline row
- Stage 3.5 ran to completion on both lanes
- the new Stage 3.5 telemetry persisted correctly
- the previous silent post-Phase-C stall did not recur

Persisted results:

#### `v49` legacy canary

- `stage35_baseline_selector = legacy`
- `stage35_baseline_candidate_hash = 54220d1286793f38`
- `stage35_baseline_differs_from_phasec_score_winner = 0`
- `stage35_accept_passed = 0`
- `stage35_accept_reason = search_score_drop_guard_failed`
- `stage35_best_match = 0.059`
- top-level `best_match_ratio = 0.060`

#### `v49` `score_plus_novelty` canary

- `stage35_baseline_selector = score_plus_novelty`
- `stage35_baseline_candidate_hash = 9ae14cd106fe28bc`
- `stage35_baseline_candidate_source = phaseB_topk`
- `stage35_baseline_differs_from_phasec_score_winner = 1`
- `stage35_accept_passed = 0`
- `stage35_accept_reason = search_score_drop_guard_failed`
- `stage35_best_match = 0.061`
- `stage35_truth_gain_vs_phasec_score_winner = +0.001`
- top-level `best_match_ratio = 0.060`

Reading:

- this is a real live-boundary validation
- it is not a meaningful science win by itself
- the reduced canary budget was enough to test wiring, not enough to test solve
  lift

### 2. `v48` completed only the legacy long lane

The intended overnight 2-job compare did not finish as a compare. Only job 1
completed before the fixture-matrix wallclock cap fired.

Completed lane:

- `stage35_baseline_legacy_live_p9`

Not completed:

- `stage35_baseline_score_plus_novelty_live_p9`

Persisted legacy long-run result:

- `stage35_baseline_selector = legacy`
- `stage35_baseline_candidate_hash = 73eee2bf84b7c07f`
- `stage35_baseline_candidate_source = stage3_best_phaseB`
- `stage35_baseline_differs_from_phasec_score_winner = 0`
- `stage35_accept_passed = 0`
- `stage35_accept_reason = search_score_drop_guard_failed`
- `stage35_best_candidate_hash = 0c8fa784a602ea64`
- `stage35_best_match = 0.038`
- `stage35_truth_gain_vs_selected_row = -0.001`
- `stage35_rounds_completed = 3`
- `stage35_evals = 30726`
- top-level `best_stage = stage2_search`
- top-level `best_match_ratio = 0.041`

Console/log reading:

- Phase C finished with the same weak score-led winner class we expected
- Stage 3.5 now showed explicit heartbeats throughout all `3` rounds
- Stage 3.5 still rejected the legacy path with
  `search_score_drop_guard_failed`
- the job ended `stalled`
- the best run-level result remained the earlier `stage2_search` result

Reading:

- the new telemetry is good enough to trust the live boundary now
- the legacy long lane behaves consistently with the earlier replay result:
  legacy hands Stage 3.5 a weak baseline and does not recover from it
- but this is still only the legacy half of the intended compare

### 3. The first live compare is therefore incomplete, not negative

What we can say now:

- the live hook is real
- the live diagnostics are real
- the legacy long lane confirms the expected failure mode

What we cannot say yet:

- whether the long `score_plus_novelty` lane reproduces the Stage B admission
  and continuation lift inside the full live run

So the correct maintained reading is:

- `v49` = successful gate
- `v48` = only the legacy baseline half of the real study
- the actual live compare result is still pending because the candidate long
  lane did not run

## Programme impact

This does not weaken the earlier Stage B result. It refines the operational
picture:

- replay validation already showed:
  - legacy selector chooses a baseline row that fails the Stage 3.5 admission
    guard
  - `score_plus_novelty` chooses a better baseline row
  - that better row admits a much better continuation path
- live testing now additionally shows:
  - the selector hook can be exercised safely in the live pipeline
  - the Stage 3.5 boundary is no longer opaque
  - the current 2-job overnight structure is too ambitious for the existing
    wallclock cap

## Concrete next steps

### Immediate

Run the missing long candidate lane on its own instead of reusing the same
2-job overnight compare shape.

Why:

- one legacy long lane is already locked
- rerunning the same 2-job overnight pair risks spending another night to
  reproduce the already-known legacy half
- the real missing evidence is the full-budget
  `stage35_baseline_score_plus_novelty_live_p9` lane

### Recommended execution shape

Use one fresh 1-job live run for:

- `stage35_baseline_score_plus_novelty_live_p9`

Then compare against the completed `v48` legacy long lane.

### Decision question for that next run

On the full live job, does `score_plus_novelty`:

1. choose a different Stage 3.5 baseline row?
2. change Stage 3.5 admission behavior?
3. produce a better downstream continuation than the completed legacy long lane?

That is the narrow readout contract for the next morning:

- did it choose a different baseline row?
- did Stage 3.5 admission change?
- did downstream continuation beat the locked legacy long lane?

### After that

If the candidate long lane shows the same mechanism-level win already seen in
Stage B, then the next integration step can be discussed as a benchmark-path or
toggle-gated live option.

If it does not, then the maintained lesson will be:

- the replay-ready frontier win is real
- but it does not transfer cleanly into the full live job under the current
  budgets/guards

## Bottom line

The neat reviewer summary is:

- the live Stage 3.5 selector boundary is now validated and observable
- the reduced canary proved the selector switch and diagnostics path
- the first overnight run only completed the legacy long lane because of the
  wallclock cap
- that legacy long lane confirms the expected failure mode
- the real missing experiment is now very specific:
  - run the full-budget `score_plus_novelty` lane on its own and compare it to
    the completed legacy long lane

## 2026-04-02 addendum: current `v50` candidate lane already changes the baseline row, but Stage 3.5 runtime is now the blocker

Even before completion, the current `v50` run has established:

- `score_plus_novelty` does choose a different Stage 3.5 baseline row in the
  full live job
- selected row:
  - `9002ee09917e5a0d`
- source:
  - `phaseA_selected`
- lane:
  - `challenger`
- source rank:
  - `2`

But the same run also shows that the stronger candidate path is dramatically
more expensive under the current full Stage 3.5 search shape.

Observed candidate Stage 3.5 progress:

- round `1 / 3`, mini `1 / 18`:
  - `elapsed = 1763.575s`
- round `1 / 3`, mini `8 / 18`:
  - `elapsed = 12245.814s`
- round `1 / 3`, mini `16 / 18`:
  - `elapsed = 24495.704s`

Reference legacy long lane:

- full Stage 3.5 runtime:
  - `27080.954s`
- and that legacy runtime completed all `3` rounds

So the current maintained reading is now:

- selector difference in the live job is real
- but Stage 3.5 runtime on the better candidate path is the immediate blocker
- the next technical focus should therefore shift to:
  - Stage 3.5 speed
  - Stage 3.5 observability
  - Stage 3.5 isolated replay/resume
