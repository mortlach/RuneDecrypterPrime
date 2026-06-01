# No-WLI Stage B first comparison note

## Purpose

Record the first concrete Stage B result after the `v46` replay-capture compare
finished: the replay-ready frontier export now works, the selector comparison is
frozen, and the selected candidate material is saved for direct replay/trial-key
tests.

## What was implemented

- a shared late-frontier row loader:
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_frontier_rows.py`
- exporter / replay / resume / truth-gap consumers now all use that shared
  frontier loader instead of assuming one artifact shape:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/replay_phasec_rescue_sweep.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py`
- fresh Stage B exports:
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_stageb_replay_ready_frontiers.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_selector_stageb_report.py`
- Stage B comparison helpers:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_stageb.py`

## Meaningful proof

- focused regression slice:
  - `58 passed`

## Exported Stage B artifacts

Replay-ready frontiers:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v46_seed411_control_replay_frontier.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v46_seed411_candidate_replay_frontier.json`

First Stage B comparison bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/summary.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stageb_v46/selected_trial_material_rows.json`

## What the first Stage B comparison says

Both `v46` frontiers are replay-ready:

- frontier key material complete:
  - control `1`
  - candidate `1`
- selected candidates replay-ready:
  - control `1`
  - candidate `1`

The selector choices are the same across both runs:

- legacy chooser:
  - `73eee2bf84b7c07f`
  - truth `0.039`
- frozen Stage A baseline `score + novelty`:
  - `9002ee09917e5a0d`
  - truth `0.418`
- optional source-penalty variant:
  - `9002ee09917e5a0d`
  - truth `0.418`
- oracle-best explored:
  - `9002ee09917e5a0d`
  - truth `0.418`

So the first replay-ready Stage B readout is:

- the replay-capable frontier confirms the same late-stage selection failure
- the frozen `score + novelty` baseline already picks the oracle-best explored
  challenger on both replay-ready `v46` runs
- the optional source-penalty variant adds no extra lift on this specific
  frontier because it picks the same row as the baseline

## Artifact correction

The earlier caution that the `v46` frontier only lived in the run-level
checkpoint file was too pessimistic.

The corrected reading is:

- `v46` final-instance artifacts do contain
  `stage3_diagnostics.phaseC_start_summaries`
- the run-level `phasec_start_checkpoints.jsonl` remains a valid cross-check
- the new shared frontier loader still matters because it keeps all replay and
  export paths robust to either storage shape

## Immediate practical consequence

Stage B is now past the "can we export and compare replay-ready frontiers?"
gate.

The next concrete step is:

- use `selected_trial_material_rows.json` to drive the first direct replay /
  continuation comparison for:
  - legacy
  - `score + novelty`
  - optional source-penalty variant

That is the next real discriminator.
