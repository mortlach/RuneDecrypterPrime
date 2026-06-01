# No-WLI Stage B first continuation note

## Purpose

Record the first direct Stage B continuation result from the replay-ready `v46`
frontier material.

This is the first check that goes beyond frozen selector ranking and asks the
real downstream question:

- if we choose the better late-stage challenger from the replay-ready frontier,
  does the actual Stage 3.5 continuation path improve?

## Inputs

Replay-ready selected-row handoff:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json`

Generated continuation bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/summary.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46_continuation/continuation_results.json`

Implementation path:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_stageb_continuation.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stageb_continuation_report.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`

## What was tested

For both replay-ready `v46` frontiers:

- control
- candidate

run the real Stage 3.5 continuation from the selected candidate material for:

- `legacy`
- `score_plus_novelty`
- `score_plus_novelty_plus_source_penalties`

## Result

The result is clean and repeated across both replay-ready runs.

### Legacy path

- selected candidate:
  - `73eee2bf84b7c07f`
- selected truth:
  - `0.039`
- Stage 3.5 selected:
  - `0`
- accept reason:
  - `search_score_drop_guard_failed`
- best continued truth:
  - `0.038`

Plain reading:

- the legacy-selected row does not survive the Stage 3.5 acceptance rule
- continuation from the legacy winner does not improve the run in truth terms

### `score + novelty` path

- selected candidate:
  - `9002ee09917e5a0d`
- selected truth:
  - `0.418`
- Stage 3.5 selected:
  - `1`
- accept reason:
  - `accepted`
- best continued candidate:
  - `d9430723f54e973e`
- best continued truth:
  - `0.496`
- truth gain vs selected challenger:
  - `+0.078`

Plain reading:

- the replay-selected challenger is not only better on the frozen frontier
- it also survives the real Stage 3.5 continuation path
- and that continuation produces a materially better downstream result

Important nuance:

- the best continued row is:
  - `d9430723f54e973e`
- and its Stage 3.5 metadata is:
  - `best_seed_source = final_best`
  - `best_stage3_source = stage3_best_phaseB`
  - `best_lane = anchor`

So the first continuation win should be read as:

- choosing `9002...` gives Stage 3.5 an accepted baseline and admits the better
  continuation path
- the improvement is not yet best described as:
  - "the exact challenger stays champion unchanged through every later step"
- it is better described as:
  - "the better challenger choice unlocks a materially better downstream
    continuation result"

### Source-penalty variant

On this frontier it selects the same challenger as `score + novelty`:

- `9002ee09917e5a0d`

and therefore produces the same continuation result:

- accepted by Stage 3.5
- best continued truth:
  - `0.496`

So the source-penalty variant adds no extra value on this first replay-ready
case.

## Scientific consequence

This is the first direct evidence that the late-stage problem on this `411`
frontier is not just a reporting defect and not just a frozen ranking curiosity.

The stronger statement is now:

- the legacy selector chooses a worse explored row
- the `score + novelty` reranker chooses a much better explored challenger
- and that better challenger choice admits a real Stage 3.5 continuation path
  that reaches a higher-truth downstream result

So on this replay-ready case, the late-stage selector is now validated as a real
marginal lever.

## Path-hygiene follow-up

The replay frontier fixture path contract was also tightened while locking this
result:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`

now emits repo-relative:

- `source_artifact_path`
- `phasec_checkpoint_path`

That keeps the Stage B handoff artifacts aligned with repo path rules and avoids
local absolute-path leakage in generated review outputs.

## Current maintained reading

- `score + novelty` remains the locked Stage B baseline
- the source-penalty variant stays optional only
- the first replay-ready continuation case is a real positive for the late
  selector / reranker direction
- the next scorer study can now be written against:
  - a real frozen failure fixture
  - a benchmark-only ranking harness
  - and one replay-ready continuation win
