# Stage-2 Topk Selected-Family Low-Edge Phase-A Gate Persistence Microprobe Plan

Date: 2026-04-23

Status:

- completed
- advance
- live-read canary ready

## Why this note exists

The Phase-A rank-1 gate was already strong enough offline:

- `phasea_rank1_init_match >= 0.30`

The remaining question was no longer whether the gate existed.

It was whether the gate could be surfaced early enough during a real replay so
an IDE-driven run could inspect it before paying for the rest of the attempt.

## Main question

Can the exact replay path persist a stable Phase-A gate snapshot early enough
that the selector branch can inspect it during the run without bespoke terminal
tooling?

## Mechanism layer

- instrumentation
- stop-discipline

## Pre-run block

Question:

- can the current selector branch make the Phase-A gate visible inside the
  Python-run artifacts before the expensive continuation starts?

Suspicion:

- the gate can be persisted immediately after Phase-A selected rows are fixed
- the resume bundle can carry one explicit snapshot file plus one progress
  event and one status pointer
- that will be enough to support a cheap real-run canary next

Main alternative:

- the gate may still be reconstructable only after completion
- or the persistence hook may require too much interface churn to land
  cleanly

If suspicion is true, expect:

- one repo-native `resume_bundle/phasea_gate_snapshot.json`
- one `stage3_phasea_gate_snapshot` progress event
- one stable status-file relpath to the snapshot

If alternative is true, expect:

- no early persisted file
- or a patch that depends on ad hoc launch tooling rather than Python-run
  artifacts

Decision rule:

- advance only if the gate snapshot lands in the real resume bundle plumbing,
  is visible from the exact replay wrapper, and is covered by focused tests
- refine otherwise

## Why this is the right science-method step now

This is the correct methods step after the operational gate microprobe:

- first prove the gate is worth the time
- then make it inspectable mid-run
- only then spend more wallclock on a real replay or runtime decision

## Implementation

Core persistence patch:

- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_two_phase.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/stage3_runtime_calls.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`

Exact replay wrapper update:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`

Focused proof:

- `tests/tools/test_no_wli_artifact_resume.py`
- `tests/tools/test_no_wli_stage3_phasec.py`
- `tests/tools/test_no_wli_selected_family_low_edge_exact_replay_1111_7004.py`

## Required outputs

The persistence microprobe must emit:

- one early snapshot file:
  - `resume_bundle/phasea_gate_snapshot.json`
- one progress event:
  - `stage3_phasea_gate_snapshot`
- one status pointer / relpath surfaced by the replay wrapper

## Result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_phasea_gate_live_read_canary`

Main read:

- the snapshot now persists immediately after Phase-A selected rows and Phase-B
  family-preservation context are fixed
- the snapshot is written before Phase-B / Phase-C continuation spends the rest
  of the replay wallclock
- the exact replay wrapper now surfaces the snapshot relpath in
  `attempt_status.json`
- focused verification passed:
  - `40 passed`

Interpretation:

- the persistence half of the gate branch is now real
- the remaining question is practical actionability during one cheap rerun:
  - can a human inspect the snapshot quickly enough
  - and should the wrapper eventually turn that into:
    - fallback
    - early stop
    - or both
