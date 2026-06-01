# Stage-2 Topk Selected-Family Low-Edge Phase-A Competitiveness Audit Plan

Date: 2026-04-23

Status:

- completed
- advance
- conditioned-gate branch decision ready

## Why this note exists

The exact replay family matrix for the narrowed upstream selector is now
complete:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_closure_note_2026-04-23.md`

That matrix proved the selector was not uniformly false.

It also proved the raw selector was not safe enough to promote.

So the right next science-method step was:

- stay on the same mechanism layer
- stay offline
- explain the split cheaply
- and look for an early signal that can help us stop or fallback faster

## Main question

After the mixed exact-family replay result, do simple early Phase-A challenger
competitiveness signals separate the `1111` wins / near wins from the hard
collapses cheaply enough to justify a conditioned selector rule?

## Mechanism layer

- selection

## Pre-run block

Question:

- can one early Phase-A competitiveness metric explain why the same saved-row
  truth gain:
  - wins on `7003`
  - nearly wins on `7005`
  - but collapses on `7001` and `7002`

Suspicion:

- the split is already visible by the top Phase-A challenger competitiveness
  level
- a simple threshold on early Phase-A init quality should filter the hard
  collapses while keeping the non-catastrophic lanes

Main alternative:

- the split is not visible cheaply at Phase A
- or any threshold that removes the collapse lanes also discards too many
  usable lanes

If suspicion is true, expect:

- at least one early Phase-A threshold to:
  - filter both hard collapse lanes
  - keep all three non-catastrophic lanes
- and the resulting counterfactual family mean delta versus baseline to become
  positive

If alternative is true, expect:

- no simple Phase-A threshold to isolate both collapse lanes cleanly
- or any such threshold to keep the counterfactual family read flat or worse

Tomorrow's decision rule:

- advance only if one early Phase-A gate filters both hard collapse lanes,
  keeps all three non-catastrophic lanes, and turns the counterfactual family
  mean delta versus baseline positive
- refine if the split is partially explanatory but still ambiguous
- close if no cheap early gate exists

## What we expect to learn

This study is meant to answer three things cheaply:

- whether the selector split is explanatory rather than mysterious
- whether the next branch should be a conditioned selector gate rather than a
  generic "refinement"
- whether this branch can contribute to faster stop / fallback discipline

## Why this is the right science-method step now

This is the method correction after the mixed exact-family result:

- do not launch a live runtime by inertia
- do not rerun another unconditioned exact family by habit
- use the already-completed exact bundles to see whether an early gate exists
  before paying for more execution

## Frozen inputs

Use exactly:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1/`

## Implementation

Single-script offline audit:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1.py`

Policy under audit:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

## Required outputs

This audit must emit:

- one machine-readable case table
- one machine-readable threshold summary table
- one short markdown readout
- one explicit advance / refine / close recommendation

Completed output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260424T021633Z__stage2_topk_selected_family_low_edge_phasea_competitiveness_audit_v1/`

## Result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_phasea_rank1_gate_microprobe`

Best gate:

- `rank1_init_ge_0p30`

Main read:

- the best metric is:
  - `phasea_rank1_init_match`
- threshold:
  - `0.30`
- kept seeds:
  - `7003,7004,7005`
- filtered seeds:
  - `7001,7002`
- kept mean delta versus baseline:
  - `+0.035`
- counterfactual family mean delta versus baseline:
  - `+0.021`
- counterfactual family worst delta versus baseline:
  - `-0.003`

Interpretation:

- the selector split is not just late-run noise
- an early Phase-A competitiveness gate already explains the two worst lanes
- the branch is now narrower than a generic postmortem
- the next honest microprobe is a concrete Phase-A rank-1 gate test

## Decision

Advance the branch, but not to a live runtime yet.

Advance to:

- a conditioned `phasea_rank1_init_match >= 0.30` gate microprobe

Do not advance to:

- another raw unconditioned replay family
- a live runtime on the ungated selector
- or a return to generic diversity / allocation work
