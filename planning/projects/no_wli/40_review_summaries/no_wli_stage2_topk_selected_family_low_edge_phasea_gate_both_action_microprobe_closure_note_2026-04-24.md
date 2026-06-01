# Stage-2 Topk Selected-Family Low-Edge Phase-A Gate Both-Action Microprobe Closure Note

Date: 2026-04-24

Status:

- completed
- hold
- operationally blocked on timing

## Why this note exists

The selector branch had already validated:

- the concrete gate:
  - `phasea_rank1_init_match >= 0.30`
- persisted live-read correctness on the fixed `1111` family
- the family split:
  - keep:
    - `7003,7004,7005`
  - filter:
    - `7001,7002`

What still needed a real execution answer was the first action contract:

- fallback
- early stop
- or both

The chosen first contract for this microprobe was:

- both

## Runs

Microbatch runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1.py`

Completed bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_microprobe_v1/`

Filtered child canary:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T161225Z__stage2_topk_selected_family_low_edge_phasea_gate_both_action_exact_replay_1111_search7002_v1/`

Kept child canary:

- not launched

## Outcome

The filtered canary `7002` answered the branch before the kept canary was
needed.

Observed `7002` read:

- gate metric:
  - `phaseA_rank1_init_match = 0.289`
- verdict:
  - `filter`
- action contract:
  - `phasea_rank1_gate_both_v1`
- action applied:
  - yes
- fallback target:
  - retained baseline
  - stage:
    - `stage35_substitution_only`
  - match:
    - `0.754`
- final replay result:
  - `0.754`
- delta vs baseline:
  - `0.000`

So the first important truth is:

- the both-action contract is semantically correct on the filtered lane

## Timing result

The timing result is what closes the branch.

Reference exact replay for `7002` from the trusted fixed-family matrix:

- elapsed:
  - `00:22:13`
  - `1333.3s`

Current filtered action canary:

- elapsed:
  - `01:09:52`
  - `4191.9s`
- actual saved attempt seconds versus the trusted prior exact replay:
  - `-2858.6s`
- actual saved attempt share:
  - `-2.144`

Persisted gate timing:

- snapshot elapsed:
  - `4190.0s`
- snapshot share of total elapsed:
  - `0.9996`

So the operational read is explicit:

- the current gate verdict is not arriving early
- it is arriving essentially at the end of the replay
- wiring `both` at the current emitted gate point does not save time
- on this first filtered canary it actually made the run slower than the
  trusted prior exact replay

## Budget read

Written microbatch budget:

- `01:00:00`

After the first completed canary:

- projected two-canary total:
  - `01:31:46`

So the stop rule fired correctly:

- microbatch status:
  - `stopped_over_budget`
- `7003` was not launched

## Decision

- do not widen the both-action branch in its current emitted form
- do not spend another kept-lane no-harm canary on the current gate surface
- close the action-choice question in this narrow sense:
  - `both` is not the blocker
  - timing is the blocker
- move the branch upstream to an earlier-emission question instead:
  - what earlier checkpoint can emit the same keep/filter verdict before the
    full Phase-A / basin-judge completion surface

## Next honest move

- keep the validated gate semantics
- keep the current live-read family split as trusted
- stop treating:
  - fallback
  - early stop
  - or both
  as the main open choice
- make the next branch:
  - earlier gate emission
  - or a different earlier gate surface

Until that exists:

- no wider both-action batch
- no live runtime justified from this selector branch
