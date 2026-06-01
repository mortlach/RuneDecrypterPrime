# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Best-Init Window Timing Postmortem Audit Plan

Date: 2026-04-24

Status:

- completed

## Why this note exists

The selector checkpoint subtopic now passes semantically across the fixed
`1111` family, but one kept lane still has an operational caveat.

Already closed:

- restart32 best-init action hard pair:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T211444Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_action_microprobe_v1/`
- restart32 best-init remaining-family microbatch:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T222109Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1/`

What is no longer in doubt:

- filtered lanes:
  - `7001`
  - `7002`
  save real wallclock
- kept lanes:
  - `7003`
  - `7004`
  - `7005`
  stay no-harm on exact outcome

What still needs explaining:

- kept `7004` preserved the exact outcome but ran at `00:37:37`
- its reference exact replay anchors were much lower:
  - `00:24:17`
  - `00:22:52`

So the next honest step is not another canary.

It is a short postmortem timing audit.

## Main question

After the restart32 best-init family microbatch passed semantically, what
explains the kept `7004` wallclock inflation relative to its reference exact
replays?

## Mechanism layer

- selection
- checkpoint action contract
- runtime interpretation

## Pre-run block

Question:

- is the kept `7004` slowdown a gate-logic problem, or a broader throughput
  slowdown that happens to preserve the same exact result?

Suspicion:

- the slowdown should already be visible before and after the kept decision
- `7003` under the same action wiring should stay timing-stable
- so the anomaly should not read like a gate-logic failure

Main alternative:

- the slowdown may still be tied to repeated gate churn or a genuinely late
  kept decision

If suspicion is true, expect:

- `7003` family microbatch vs reference:
  - near-parity elapsed timing
  - near-parity downstream heartbeat timing
- `7004` family microbatch vs references:
  - first keep decision already at restart `32`
  - first keep decision still materially before total completion
  - slowdown already visible by restart `64`
  - slowdown still visible deep in Phase B

If alternative is true, expect:

- `7004` first keep decision will be late enough to explain most of the
  overrun
- or the slowdown will collapse back to one narrow gate-related surface rather
  than broad runtime loss

Decision rule:

- advance only if the audit shows `7003` is timing-stable under the same action
  wiring, `7004` decides keep early at restart `32`, and the slowdown is
  already visible both at restart `64` and deep in Phase B
- otherwise refine

## Why this is the right science-method step now

This is the smallest honest next move.

It does not reopen live runtime.
It does not rerun another replay family.
It explains the only remaining caveat on an otherwise complete selector
checkpoint subtopic.

## Comparison set

Control pair:

- `7003` reference exact replay
- `7003` family-microbatch kept run

Anomaly pair:

- `7004` reference exact replay anchor
- `7004` latest prior exact replay
- `7004` family-microbatch kept run

## Runtime budget proof

This is an offline extractor only.

Expected wallclock:

- well under `00:10:00`

Stop condition:

- if the extractor fails to recover the needed progress/timing fields from the
  saved bundles, stop and refine the extractor rather than infer from memory

## Implementation

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1.py`

## Required outputs

The audit must emit:

- one comparison rows CSV
- one comparison rows JSONL
- one summary JSON
- one recommendation JSON
- one short readout

What the readout must answer:

- was kept `7004` already `keep` early enough that gate timing cannot explain
  the whole overrun?
- is the extra wallclock visible before and after the checkpoint?
- does `7003` stay stable under the same action wiring?
- is the selector checkpoint subtopic now review-ready?

## Completion

Bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T001151Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_timing_postmortem_audit_v1/`

Result:

- `advance`

Key read:

- `7003` family elapsed / reference:
  - `1.007`
- `7003` family Phase-B step2112 elapsed / reference:
  - `0.997`
- `7004` first keep checkpoint:
  - restart `32`
- `7004` first keep elapsed share:
  - `0.269`
- `7004` family elapsed / latest reference:
  - `1.646`
- `7004` family restart64 elapsed / latest reference:
  - `1.518`
- `7004` family Phase-B step2112 elapsed / latest reference:
  - `2.474`

Conclusion:

- the `7004` slowdown does not read like a gate-logic failure
- the selector checkpoint subtopic is now review-ready
- live runtime still should not reopen from this audit alone
