# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Refinement Audit Plan

Date: 2026-04-24

Status:

- active

## Why this note exists

The earlier-emission microprobe is now closed on the raw provisional checkpoint
surface:

- `7002` matched `filter` at every checkpoint
- `7003` stayed falsely filtered at every checkpoint
- the kept `7003` challenger was already present in the provisional data
- so the failure is not simply "too early"
- the failure is:
  - the wrong provisional ordering surface

That means the next honest step is not another action canary and not a wider
runtime batch.

It is a cheap checkpoint-refinement audit.

## Main question

Can one refined provisional checkpoint rule recover the trusted fixed-family
labels before the current late gate surface, without rerunning the full branch
blindly?

## Mechanism layer

- selection
- stop-discipline
- checkpoint-surface refinement

## Pre-run block

Question:

- using only fields already available in the current provisional snapshots and
  trusted late gate rows, is there a refined provisional rule that:
  - matches the late fixed-family split on `7001-7005`
  - matches the provisional canary split on `7002/7003`
  - and does so at a shared early checkpoint?

Suspicion:

- the current raw provisional `rank1` floor is too brittle on kept lanes
- but a refined rule that preserves the current `rank1` floor and allows a
  bounded high-best override may recover the split honestly

Main alternative:

- no small rule over the currently persisted provisional fields is good enough
- if so, the branch must persist richer provisional ordering fields rather than
  pretending the current surface can be tuned into correctness

If suspicion is true, expect:

- at least one concrete refined rule will match:
  - the trusted late family split on `7001-7005`
  - the provisional `7002/7003` checkpoints
- the earliest shared checkpoint should land before restart `64`
- the shared checkpoint should still beat the current late gate timing by a
  meaningful margin

If alternative is true, expect:

- either no refined rule will match both datasets
- or only degenerate rules will work on the current two canaries but fail the
  trusted late family labels

Decision rule:

- advance only if one concrete refined rule matches the trusted late family
  labels on `7001-7005` and the provisional canary split on `7002/7003` at a
  shared checkpoint earlier than the current late surface
- hold if no such rule exists over the currently persisted fields
- if held, the next branch becomes richer provisional ordering persistence

## Why this is the right science-method step now

This is the cheapest honest next step because it avoids two bad habits:

- do not widen a provisional surface that is already known to be wrong
- do not jump straight back into runtime just because the previous branch
  finished

The scientific method role here is explicit:

- write down the checkpoint-surface suspicion
- test the smallest offline consequence of that suspicion
- only then decide whether a short new replay canary is justified

## Inputs

Trusted late-family bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`

Provisional checkpoint microprobe bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1/`

Key child replay bundles:

- `.../20260424T175849Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_exact_replay_1111_search7002_v1/`
- `.../20260424T183152Z__stage2_topk_selected_family_low_edge_phasea_earlier_emission_exact_replay_1111_search7003_v1/`

## Runtime budget proof

This is an offline audit only.

Expected wallclock:

- well under `00:15:00`

So this step does not need a new runtime budget anchor.

## Implementation

Audit script:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement_audit_v1.py`

## Required outputs

The audit must emit:

- one candidate-rule rows CSV
- one candidate-rule rows JSONL
- one summary JSON
- one recommendation JSON
- one short readout

What the readout must answer:

- which refined provisional rule, if any, survives both the late family labels
  and the provisional canaries?
- what is the earliest shared checkpoint for that rule?
- how much timing headroom does it recover versus the current late gate?
- is the next honest move:
  - one short confirmation replay microprobe
  - richer provisional field persistence
  - or hold
