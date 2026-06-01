# Stage-2 Topk Selected-Family Low-Edge Phase-A Gate Live-Read Follow-On Plan

Date: 2026-04-23

Status:

- completed
- advance on live-read correctness
- refine on action timing

## Why this note exists

The selector branch now has:

- an offline gate:
  - `phasea_rank1_init_match >= 0.30`
- an operational value read:
  - about `42.3` filtered saved minutes
- a persisted replay artifact:
  - `resume_bundle/phasea_gate_snapshot.json`

The first real live-read check on this branch is:

- fixed `1111/search7004`

The first live-read canary exposed a real schema gap.

The patched `7004` rerun then closed that gap, and the bounded family
follow-on completed.

## Main question

Once a patched `1111/search7004` live-read canary completes with a usable
snapshot, do the remaining fixed `1111` exact replays also expose the new
Phase-A gate snapshot cleanly, and does that live snapshot reproduce the known
family keep/filter split?

## Mechanism layer

- selection
- instrumentation
- stop-discipline

## Pre-run block

Question:

- after a patched `7004` canary proves the new snapshot is usable on one lane,
  does the rest of the fixed `1111` family preserve the same gate surface
  cleanly enough to support a real action contract?

Suspicion:

- the live snapshot will persist on all family cells
- the live gate read will match the offline split:
  - keep:
    - `7003,7004,7005`
  - filter:
    - `7001,7002`

Main alternative:

- one or more cells will fail to expose a usable snapshot
- or the live snapshot will disagree with the known split enough that the
  branch is still not ready to choose fallback versus early stop

If suspicion is true, expect:

- every completed cell writes `phasea_gate_snapshot.json`
- every completed cell exposes `phasea_gate_snapshot_json_relpath`
- live verdicts agree with the known split on all five family cells

If alternative is true, expect:

- missing snapshot artifacts
- or verdict mismatches on one or more cells

Decision rule:

- advance only if the predecessor canary completes with a real snapshot, all
  follow-on cells expose the same snapshot surface, and the derived live gate
  verdict matches the known family split on every completed cell
- refine for any partial artifact or verdict mismatch

## Why this is the right science-method step now

This was the smallest honest longer run after the persistence patch:

- rerun one cheap `7004` canary once
- then collect the remaining four fixed `1111` family cells
- and only then judge the first automated gate-action branch

## Current predecessor canary

Original failed canary output dir:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T034213Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`

That first canary finished with a real file write, but not a usable verdict
surface:

- `resume_bundle/phasea_gate_snapshot.json` existed
- but:
  - `phaseA_rank1_init_match = null`
  - `phaseA_best_init_match = null`
  - `phaseA_rank1_final_match = null`
- snapshot timing was late:
  - about `53m42s`
  - about `0.891` of total runtime

Patched predecessor canary output dir:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061020Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`

Patched predecessor read:

- completion:
  - `00:23:56`
- replay result stayed the same local negative:
  - baseline `0.423`
  - retained Stage-3 reference `0.432`
  - replay `0.420`
  - delta vs baseline `-0.003`
- snapshot became usable:
  - `phaseA_rank1_init_match = 0.415`
  - verdict:
    - `keep`
- snapshot timing:
  - `1261.0s`
  - share `0.878`

## Runtime budget proof

Retained anchor for this exact replay family:

- completed reference:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T042429Z__stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1/`
- elapsed:
  - `01:07:53`

Session shape:

1. active predecessor canary:
   - `7004`
2. queued follow-on cells:
   - `7001`
   - `7003`
   - `7005`
   - `7002`

Budget read:

- anchored per-cell estimate:
  - about `1.13h`
- anchored five-cell family total:
  - about `5.66h`
- anchored queued follow-on only:
  - about `4.53h`
- intended session budget:
  - `8.0h`

Observed completed family run:

- output dir:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1/`
- elapsed:
  - `02:03:21`
- completed family coverage:
  - `5 / 5`
- post-first-job projected family total:
  - about `02:03:17`

So the session stayed well under the written `8.0h` budget.

## Stop condition

This follow-on was configured to stop if any of these became true:

- the patched predecessor canary finishes without a real and usable
  `phasea_gate_snapshot.json`
- after any completed follow-on cell, the observed projected five-cell family
  total exceeds `8h`
- a child replay fails and leaves the family in partial coverage

If that happens:

- stop before launching another cell
- keep the rescued completed rows as valid family coverage

## Implementation

Single Python follow-on runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py`

Preferred launch order:

- first run:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- then run:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py`
- the follow-on runner now blocks unless the predecessor wrote a real and
  usable `phasea_gate_snapshot.json`

Focused proof:

- `tests/tools/test_no_wli_phasea_gate_live_read_followon_1111_v1.py`

## Required outputs

Completed outputs:

- one run-state JSON
- one event log JSONL
- one per-cell CSV / JSONL
- one machine-readable summary
- one short readout
- partial coverage if the run stops before full completion

Completed result:

- machine recommendation:
  - `advance`
- snapshot-present count:
  - `5`
- snapshot-usable count:
  - `5`
- verdict-match count:
  - `5`
- mean snapshot elapsed:
  - `1303.4s`
- mean snapshot share:
  - `0.881`
- family split reproduced exactly:
  - keep:
    - `7003,7004,7005`
  - filter:
    - `7001,7002`

Decision after completion:

- this plan closes as a correctness pass for the live-read family
- the remaining open question is no longer whether the snapshot exists or
  matches the split
- the remaining open question is whether the gate should be wired as:
  - fallback
  - early stop
  - or both
- and whether the live verdict can be emitted earlier than the current
  approximately `0.88` share of total replay elapsed
