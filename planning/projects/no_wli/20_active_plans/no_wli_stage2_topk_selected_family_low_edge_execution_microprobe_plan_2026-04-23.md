# Stage-2 Topk Selected-Family Low-Edge Execution Microprobe Plan

Date: 2026-04-23

Status:

- completed
- closed
- clean exact negative

## Why this note exists

The selector branch has now passed the cheap offline gates:

- upstream promoted-family diagnosis
- concrete selector audit
- family-view / score-band sensitivity sweep
- saved handoff audit

This note records the first exact execution gate for that selector line.

It now also records the outcome and closure decision.

## Main question

On fixed `1111/search7004`, does the concrete upstream selector
`selected_family_low_edge_eps_0p016_v1` improve the executed Stage-3 outcome,
or does it only change the saved handoff while staying flat once real search
runs?

## Mechanism layer

- selection

## Pre-run block

Question:

- if the `best2_key` handoff is replaced by the concrete selected-family
  low-edge row on fixed `1111/search7004`, does the retained Stage-3 replay
  beat the retained baseline outcome?

Suspicion:

- `1111/search7004` is a real upstream representative-selection miss
- the concrete selector changes the saved handoff materially
- that handoff improvement can survive into a better executed Stage-3 result

Main alternative:

- the selector changes the saved handoff but Stage 3 still lands flat or worse
- or the execution family becomes too slow to justify further runtime

If suspicion is true, expect:

- completed retained replay
- same search budget family as the retained cell
- replay best match above retained baseline `0.423`

If alternative is true, expect:

- completed but flat / worse replay
- or no honest completion inside the written budget

Tomorrow's decision rule:

- advance only if the selector replay completes honestly and beats retained
  baseline cleanly
- refine only if there is a narrow gain or a budget-fragile positive
- close if flat, worse, or operationally too expensive

## Why this is the first execution target

Choose fixed `1111/search7004` first because:

- the selector branch is specifically about `1111`
- `search7004` already has a stable retained identity in this project
- the retained fixed-cell wallclock is about:
  - `2.36h`
- the killed `v76` control rescue and the closed `v78` partial bundle both gave
  useful same-cell context already
- `1111/search7002` is not allowed as the first execution target here even
  though its legacy retained time is similar, because altered families on that
  seed already stretched to about:
  - `18.81h`

## Planned execution shape

First execution unit:

- one retained Stage-3 replay
- one fixed cell:
  - `1111/search7004`
- one mechanism change only:
  - replace the saved representative using:
    - family view:
      - `prefix_hamming_le_24`
    - policy:
      - `selected_family_low_edge_eps_0p016_v1`

Do not bundle:

- a second cell
- a same-session control pair
- any extra late-policy changes

Prepared implementation surface:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- launchers:
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_launch_2026-04-23.ps1`
  - `planning/projects/no_wli/60_launch_scripts/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_open_terminal_2026-04-23.ps1`

## Budget and stop rule

Retained exact-cell anchor:

- fixed `1111/search7004`
  - about `2.36h`

New-family caution:

- this selector branch is still a materially new execution family
- budget it conservatively rather than assuming legacy timing will hold exactly

Intended session budget:

- `5h`

Stop rule:

- if the replay has not completed by launch `+ 6h`, stop it and record
  operational incompleteness

## Required outputs

The execution microprobe must emit:

- one machine-readable summary
- one short human readout
- one explicit baseline-versus-selector comparison
- one explicit advance / refine / close recommendation

## What happened

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`

Completion state:

- `attempt_status.json`
  - `status = "completed"`
  - `elapsed = "01:07:53"`
  - `resume_bundle_written = 1`

Result summary:

- `run_summary.json`
  - `baseline_best_match_ratio = 0.423`
  - `retained_stage3_reference_match_ratio = 0.432`
  - `resume_best_match_ratio = 0.420`
  - `match_delta_vs_baseline = -0.003`
  - `match_delta_vs_retained_stage3_reference = -0.012`

Selector-specific read:

- `selected_family_low_edge_exact_replay_summary.json`
  - baseline row truth:
    - `0.091`
  - candidate row truth:
    - `0.161`
  - truth delta:
    - `+0.070`
  - candidate Stage-3 promoted keys:
    - `144`

Checkpoint read:

- `resume_bundle/phasec_start_checkpoints.jsonl`
- strongest challenger:
  - start `2`
  - source:
    - `phaseA_selected`
  - init `0.415`
  - final `0.420`
  - `became_global_best = 1`
  - `overtook_anchor = 1`

## Interpretation

The replay completed honestly enough to judge.

It answered the main question cleanly:

- the selector is not a no-op
- the selector improves the saved handoff materially
- the selector creates a strong challenger execution lane
- but the exact replay still stays below both the artifact baseline and the
  retained Stage-3 reference

So this first exact execution gate is a clean negative.

## Decision

Decision:

- `close`

Meaning:

- close this exact replay microprobe as a solve-improvement gate
- do not schedule a second replay or a new live runtime by default
- move next to a cheaper execution-collapse / postmortem audit if this branch
  is revisited
