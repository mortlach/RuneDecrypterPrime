# Stage-2 Topk Selected-Family Low-Edge Handoff Audit Plan

Date: 2026-04-22

Status:

- completed
- final cheap gate before replay/runtime

## Why this note exists

The selector branch is now narrowed to one concrete policy:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

The remaining cheap question is whether that selector actually changes the
saved Stage-2 to Stage-3 handoff, or whether it is effectively a label-only
swap before Stage 3 starts.

This note records that handoff audit.

## Main question

After narrowing the selector to `selected_family_low_edge_eps_0p016_v1`, does
it materially change the saved Stage-2 to Stage-3 handoff on `1111`, or is it
effectively a no-op before Stage 3 starts?

## Mechanism layer

- selection

## Pre-run block

Question:

- does the concrete selector change:
  - `best2_key`
  - `promoted_keys`
  - `init3`
  on `1111` while staying inert on the control seeds?

Suspicion:

- the selector is not just selecting a truth-better row on paper
- it should alter the real Stage-3 handoff on all five retained `1111` lanes
- the controls should stay completely inert

Main alternative:

- the selector may look interesting at the row level but still fail to move the
  saved handoff meaningfully
- or it may move handoff surfaces on the controls too

If suspicion is true, expect:

- `best2_key_changed = 1` on all five retained `1111` lanes
- `init3_changed = 1` on all five retained `1111` lanes
- non-zero edit counts on `1111`
- zero handoff changes on `611`, `1411`, and `1511`

If alternative is true, expect:

- little or no handoff movement on `1111`
- or control movement that makes the selector too broad

Tomorrow's decision rule:

- advance only if the concrete selector changes the saved Stage-3 handoff on
  all five retained `1111` lanes and remains inert on the controls
- refine if the handoff change is partial or ambiguous
- close if the selector is effectively a no-op at handoff level

## What we expect to learn

This audit is meant to answer:

- whether the selector is a real Stage-3 input change rather than just a row-id
  change
- whether the branch has earned the right to a replay or runtime microprobe
- whether any further purely offline selector narrowing is still needed

## Why this is the right science-method step now

This is the last cheap gate before a more expensive execution test:

- diagnosis is complete
- selector narrowing is complete
- now the only cheap remaining issue is:
  - does the selector change the saved Stage-3 handoff at all?

## Frozen inputs

Use exactly:

- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/`

## Implementation

Single-script offline audit:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_handoff_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage2_topk_selected_family_low_edge_handoff_audit_v1.py`

Coverage:

- fixed `611/search7001-7005`
- fixed `1111/search7001-7005`
- fixed `1411/search7001-7005`
- fixed `1511/search7001-7005`

Tracked handoff fields:

- `best2_key`
- `promoted_keys`
- `init3`

## Required outputs

This audit must emit:

- one machine-readable case table
- one machine-readable fixture summary table
- one short markdown readout
- one explicit advance / refine / close recommendation

Completed output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T031321Z__stage2_topk_selected_family_low_edge_handoff_audit_v1/`

## Result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_eps_0p016_microprobe`

Main read:

- `1111`:
  - `best2_key_changed_run_count = 5`
  - `init3_changed_run_count = 5`
  - mean `init3_edit_count = 7.8`
  - mean `stage3_promoted_keys_edit_count = 7.8`
- controls:
  - `611`: all zero
  - `1411`: all zero
  - `1511`: all zero

Interpretation:

- the selector is not a handoff no-op
- it changes the real saved Stage-3 input surface on `1111`
- further purely offline selector narrowing is no longer the honest next step

## Decision

Advance to an execution-level microprobe.

That next step should be:

- a retained replay
- or a one-job runtime microprobe

but not:

- another generic selector sweep
- another family-diversity audit
- another entry-allocation branch
