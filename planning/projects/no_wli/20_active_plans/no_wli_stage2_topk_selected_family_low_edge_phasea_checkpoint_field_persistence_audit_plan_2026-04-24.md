# Stage-2 Topk Selected-Family Low-Edge Phase-A Checkpoint Field-Persistence Audit Plan

Date: 2026-04-24

Status:

- completed
- hold

## Why this note exists

The refined confirmation microprobe is now closed:

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T193014Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1/`
- result:
  - `hold`

That hold was narrow and informative rather than fatal:

- filtered `7001` stayed at:
  - `phaseA_best_init_match = 0.378`
- kept `7005` stayed at:
  - `phaseA_best_init_match = 0.395`
- both values persisted unchanged across checkpoints:
  - `16 / 32 / 48 / 64`
- the other saved provisional fields were effectively invariant across the
  available lanes

So the next honest question is no longer whether the current composite rule
survives.

It is whether the useful provisional signal is a stable `best_init` band, and
whether that signal persists across the full retained `1111` family.

## Main question

Across the retained fixed `1111/search7001-7005` family, does
`phaseA_best_init_match` persist early enough and cleanly enough that the next
provisional rule should be a direct `best_init` threshold rather than the
current composite `rank1 or best` rule?

## Mechanism layer

- selection
- stop-discipline
- checkpoint-surface persistence

## Pre-run block

Question:

- once the refined rule fails on kept `7005`, is the real early signal simply a
  stable `phaseA_best_init_match` band across the full retained `1111` family?

Suspicion:

- the saved provisional checkpoint surface is mostly one-field:
  - `phaseA_best_init_match`
- filtered lanes should stay below a narrow upper floor
- kept lanes should stay above a narrow lower floor
- and those values should persist from the earliest saved checkpoint onward

Main alternative:

- the apparent separation is overfit to the currently available four-lane
  subset
- or the missing `7004` provisional lane will collapse the narrow band
- or richer fields will be needed after all

If suspicion is true, expect:

- the provisional checkpoint bundle will show:
  - `phaseA_best_init_match`
  - as the only materially informative early scalar
- `7001 / 7002` should stay on the filtered side
- `7003 / 7004 / 7005` should stay on the kept side
- the full-family gap should justify one simpler threshold candidate for the
  next action branch

If alternative is true, expect:

- `7004` will not support the apparent separation
- or the kept / filtered gap will collapse into overlap
- or richer checkpoint fields will be needed before another rule is honest

Decision rule:

- advance only if the full retained `1111` family shows a stable early
  `best_init` separation with a concrete candidate threshold
- refine if the signal is still promising but the full-family gap is too narrow
  or incomplete
- hold if the full-family provisional surface does not support a cleaner rule
  than the current composite threshold

## Why this is the right science-method step now

This stays cheap and disciplined:

- do not reopen another action canary yet
- do not widen to live runtime
- do not guess a new threshold from four lanes and call that solved

The method step is:

1. complete the missing provisional lane if needed
2. audit the full retained `1111` family checkpoint fields
3. decide whether the next rule is:
   - simple `best_init`
   - richer provisional surface
   - or no new rule at all

## Data basis

Already available provisional lanes:

- filtered:
  - `7001`
  - `7002`
- kept:
  - `7003`
  - `7005`

Known missing provisional lane:

- kept:
  - `7004`

Short completion canary if needed:

- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004.py`
- trusted same-file anchor:
  - `00:23:56`
- intended budget:
  - `00:45:00`
- stop condition:
  - stop if the rerun exceeds `00:45:00` or fails to write provisional
    checkpoint snapshots

## Implementation

Field-persistence extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1.py`

## Required outputs

The audit must emit:

- one rows CSV
- one rows JSONL
- one summary JSON
- one recommendation JSON
- one short readout

What the readout must answer:

- is `phaseA_best_init_match` the real stable checkpoint signal?
- what filtered / kept range does it occupy on the full retained family?
- is the next honest branch:
  - a simpler `best_init` action canary
  - richer provisional field refinement
  - or closure

## Result

- bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T210520Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_field_persistence_audit_v1/`
- recommendation:
  - `hold`
- reason:
  - the full retained provisional family did not yield a stable separating
    checkpoint field from restart `16`

Branch consequence:

- filtered `7002` was still moving between restart `16` and restart `32`
- so the honest follow-on was:
  - stabilization-window audit
  - not another action canary
