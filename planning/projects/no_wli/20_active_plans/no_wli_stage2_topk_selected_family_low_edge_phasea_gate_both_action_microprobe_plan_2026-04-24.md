# Stage-2 Topk Selected-Family Low-Edge Phase-A Gate Both-Action Microprobe Plan

Date: 2026-04-24

Status:

- completed
- hold
- operationally blocked on timing

## Why this note exists

The selector branch has now cleared the live-read correctness question:

- `phasea_rank1_init_match >= 0.30` matches the fixed `1111` split
- the replay bundle persists a usable `phasea_gate_snapshot.json`
- the bounded family live-read follow-on reproduced:
  - keep:
    - `7003,7004,7005`
  - filter:
    - `7001,7002`

What is still open is the first real action contract:

- fallback
- early stop
- or both

The chosen branch for this study is:

- both

## Main question

If the validated Phase-A gate is wired as both fallback and early stop at the
live decision point, does one filtered `1111` lane save real wallclock while
one kept `1111` lane preserves the prior no-harm / positive exact replay read?

## Mechanism layer

- selection
- stop-discipline

## Pre-run block

Question:

- once the gate is wired as both fallback and early stop, does:
  - filtered `1111/search7002`
    - stop cleanly and fall back to baseline
  - kept `1111/search7003`
    - continue cleanly and preserve the prior exact replay result

Suspicion:

- `7002` should emit `filter`, apply the both-action contract, and land at the
  retained baseline while finishing faster than the prior exact replay
- `7003` should emit `keep`, apply no stop, and reproduce the prior clean
  exact positive

Main alternative:

- the gate may still be too late to save useful wallclock
- or the kept path may perturb the previously trusted positive lane enough that
  the first both-action contract is not yet honest

If suspicion is true, expect:

- `7002`
  - observed gate verdict:
    - `filter`
  - fallback applied:
    - yes
  - result:
    - retained baseline
  - elapsed:
    - lower than the prior exact replay
- `7003`
  - observed gate verdict:
    - `keep`
  - fallback applied:
    - no
  - result:
    - matches the prior exact replay within replay tolerance

If alternative is true, expect:

- `7002`
  - little or no saved wallclock
  - or a mismatch against the retained baseline fallback target
- `7003`
  - keep-path harm relative to the prior exact replay

Decision rule:

- advance only if the filtered canary applies the both-action contract cleanly
  and the kept canary stays no-harm relative to the prior exact replay
- if correctness passes but the filtered save is still small because the
  verdict arrives late, refine toward earlier emission rather than widening the
  action batch
- hold if either canary fails the first correctness contract

## Why this is the right science-method step now

This is the smallest honest branch after live-read validation:

- do not reopen whether the gate exists
- do not rerun the full family just to collect the same split again
- do not launch a live runtime before the action contract itself exists

The next honest step is:

- one filtered canary
- one kept canary
- one explicit decision about whether the first action should be:
  - fallback
  - early stop
  - or both

## Canary choice

Filtered canary:

- `1111/search7002`
- reason:
  - strongest filtered severe collapse in the trusted exact-family matrix
  - cleanest stop/fallback proof lane

Kept canary:

- `1111/search7003`
- reason:
  - strongest clean kept positive in the trusted exact-family matrix
  - cleanest no-harm proof lane

## Runtime budget proof

Retained exact replay anchors from the completed fixed `1111` matrix:

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

- `01:00:00`

So this is still a short independently complete microbatch and can be run as a
single Python script without violating the runtime-sizing rules.

## Stop condition

This microbatch stops if either of these becomes true:

- after the first completed canary, the observed completed-row elapsed plus the
  remaining retained anchor projects above the `01:00:00` budget
- a canary fails before writing extractable artifacts

If it stops early:

- keep the rescued completed canary rows
- write partial coverage explicitly
- do not silently discard the partial read

## Implementation

Single Python runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1.py`

Underlying replay path:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

Action plumbing:

- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`

Focused proof:

- `tests/tools/test_no_wli_artifact_resume.py`
- `tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py`
- `tests/tools/test_no_wli_phasea_gate_both_action_microprobe_v1.py`

## Required outputs

The run must emit:

- one state JSON
- one event log JSONL
- one per-canary rows CSV
- one per-canary rows JSONL
- one machine-readable summary
- one machine-readable recommendation
- one short human readout

What the readout must answer:

- did `7002` stop early and fall back cleanly?
- how much real wallclock did `7002` save versus the prior exact replay?
- did `7003` keep and stay no-harm relative to the prior exact replay?
- is the next honest move:
- wider both-action batch
- earlier emission refinement
- or hold

## Completed result

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1/`

Observed outcome:

- the filtered canary `7002` answered the branch before the kept canary was
  needed
- `7002` emitted:
  - verdict:
    - `filter`
  - action applied:
    - yes
  - fallback result:
    - retained baseline `0.754`
- but the action timing failed:
  - prior exact replay elapsed:
    - `00:22:13`
  - current filtered action canary elapsed:
    - `01:09:52`
  - snapshot share of total elapsed:
    - `0.9996`
- the microbatch then stopped correctly over budget before launching `7003`

Decision after completion:

- hold the current both-action branch
- do not widen it
- move the next branch to earlier emission rather than another action-choice
  canary
