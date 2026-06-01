# Stage-2 Topk Selected-Family Low-Edge Phase-A Earlier-Emission Microprobe Plan

Date: 2026-04-24

Status:

- active

## Why this note exists

The live-read branch is now closed on correctness:

- the late gate snapshot is persisted
- the late snapshot is usable
- the late snapshot reproduces the fixed `1111` split:
  - keep:
    - `7003,7004,7005`
  - filter:
    - `7001,7002`

The first explicit `both` action canary also closed the action-choice question:

- filtered `7002` emitted the correct `filter` verdict
- the fallback landed cleanly at retained baseline `0.754`
- the blocker was timing, not semantics

So the open branch is now narrower:

- can an earlier provisional Phase-A checkpoint recover the same split before
  the current late gate surface?

## Main question

Can a provisional Phase-A checkpoint reproduce the validated keep/filter split
on one filtered and one kept `1111` lane materially earlier than the current
late gate snapshot?

## Mechanism layer

- selection
- stop-discipline

## Pre-run block

Question:

- if we persist provisional Phase-A gate checkpoints during the restart loop,
  does one filtered lane and one kept lane recover the same verdicts before the
  current full restart-64 / late-snapshot surface?

Suspicion:

- a shared checkpoint at or before restart `48` should already recover the
  split on:
  - filtered `7002`
  - kept `7003`
- if that happens with a materially lower elapsed share than the current late
  gate, then an earlier stop/fallback contract becomes technically honest

Main alternative:

- the split may only stabilize at the current full restart-64 surface
- or the provisional checkpoint ranking may drift enough that the earlier
  checkpoints do not recover the same verdicts

If suspicion is true, expect:

- at least one shared checkpoint before restart `64`
- `7002`
  - provisional verdict:
    - `filter`
- `7003`
  - provisional verdict:
    - `keep`
- mean checkpoint elapsed share should beat the current late-gate family anchor
  on these same seeds

If alternative is true, expect:

- no shared provisional checkpoint before restart `64`
- or the first shared match still lands too late to matter operationally

Decision rule:

- advance only if both canaries match at a shared checkpoint before restart
  `64` and that checkpoint lands materially earlier than the current late gate
- refine if the split appears but still too late
- hold if the provisional checkpoints do not reproduce the split

## Why this is the right science-method step now

This is the smallest honest branch after the failed `both` canary:

- do not reopen whether the gate exists
- do not spend a wider family batch on the current late surface
- do not launch a live runtime while the action point is still effectively at
  the end of the replay

The next honest step is:

- instrument provisional checkpoints
- test one filtered lane
- test one kept lane
- only widen if the provisional surface is actually informative

## Canary choice

Filtered canary:

- `1111/search7002`
- reason:
  - strongest filtered collapse
  - cleanest stop/fallback proof lane

Kept canary:

- `1111/search7003`
- reason:
  - strongest clean kept positive
  - cleanest no-harm continuation lane

## Runtime budget proof

Retained exact replay anchors from the completed `1111` matrix:

- `7002`
  - `00:22:13`
  - `1333.3s`
- `7003`
  - `00:21:54`
  - `1314.4s`

Anchored two-canary total:

- `2647.7s`
- about `00:44:08`

Intended session budget:

- `01:15:00`

Stop condition:

- after the first completed canary, recompute the projected two-canary total
  from:
  - the observed completed row
  - the remaining retained anchor
- if that projection exceeds `01:15:00`, stop before launching the second
  canary

## Implementation

Replay wrapper with provisional checkpoint persistence:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

Checkpoint persistence surface:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_phasea_restarts.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`

Microprobe runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage3_phasec.py`
- `tests/tools/test_no_wli_artifact_resume.py`
- `tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py`
- `tests/tools/test_no_wli_phasea_earlier_emission_microprobe_v1.py`

## Required outputs

The run must emit:

- one state JSON
- one event log JSONL
- one per-checkpoint rows CSV
- one per-checkpoint rows JSONL
- one summary JSON
- one recommendation JSON
- one short readout

What the readout must answer:

- what is the earliest shared provisional checkpoint that matches both canaries?
- how much earlier is that checkpoint than the current late gate?
- is the next honest move:
  - wider family follow-on
  - checkpoint refinement
  - or hold
