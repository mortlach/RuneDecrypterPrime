# Stage-2 Topk Family Representative Policy Audit Plan

Date: 2026-04-22

Status:

- completed
- branch-narrowing offline audit

## Why this note exists

The upstream promoted-family audit changed the question from:

- does `1111` lack the right family upstream?

to:

- can one simple representative selector recover the hidden stronger row inside
  the already-present `1111` family region?

This note records the first concrete policy audit on the saved `stage2_topk`
surface.

## Main question

After the upstream family audit, can one simple live-safe selector on the saved
`stage2_topk` surface recover the hidden stronger `1111` representative without
moving the control seeds?

## Mechanism layer

- selection

## Pre-run block

Question:

- can a simple within-family selector recover the hidden stronger `1111`
  representative while staying inert on `611`, `1411`, and `1511`?

Suspicion:

- inside the score-selected `1111` family, the score winner is not the best
  representative
- a narrow low-edge band rule can switch to the stronger same-family row
  without disturbing the controls

Main alternative:

- no simple selector isolates the `1111` issue cleanly
- or any selector that helps `1111` also moves the controls or introduces
  obvious harm

If suspicion is true, expect:

- `1111` candidate activation on all five retained lanes
- `1111` positive truth delta versus the baseline row
- controls to stay inert

If alternative is true, expect:

- no activation
- mixed or harmful `1111` changes
- or control movement that makes the selector too broad

Tomorrow's decision rule:

- advance only if one simple selector stays inert on `611`, `1411`, and `1511`
  while recovering the hidden stronger `1111` row on all five retained lanes
- refine if the selector helps but is still too broad or unstable
- close if no simple selector isolates the issue

## What we expect to learn

This audit is meant to answer:

- whether the upstream representative-selection story can be turned into one
  concrete selector rather than a vague diagnosis
- whether the next branch can be a codeable microprobe instead of another broad
  audit
- whether the candidate changes Stage-3 handoff preparation at all

## Why this is the right science-method step now

This is the correct next step after the upstream family audit:

- stay offline
- stay frozen-input
- keep the mechanism to `selection`
- move from diagnosis to one explicit policy candidate before any runtime

## Frozen inputs

Use exactly:

- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/`

## Implementation

Single-script offline audit:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_family_representative_policy_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage2_topk_family_representative_policy_audit_v1.py`

Family view:

- `prefix_hamming_le_24`

Candidate policy:

- `selected_family_low_edge_eps_0p020_v1`
- choose the lowest-score row inside the score-selected family whose score is
  within `0.020` of the family score winner

Coverage:

- fixed `611/search7001-7005`
- fixed `1111/search7001-7005`
- fixed `1411/search7001-7005`
- fixed `1511/search7001-7005`

## Required outputs

This audit must emit:

- one machine-readable case table
- one machine-readable fixture summary table
- one short markdown readout
- one explicit advance / refine / close recommendation

Completed output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/`

## Result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_microprobe`

Main read:

- the selector stays inert on:
  - `611`
  - `1411`
  - `1511`
- it switches all five `1111` lanes
- on `1111`, mean candidate truth delta versus the baseline row is:
  - `+0.070`
- candidate and within-family oracle match on all five `1111` lanes:
  - `5 / 5`

Interpretation:

- the upstream selection problem can now be expressed as one concrete policy
- the next issue is no longer "is there a selector at all?"
- the next issue is whether that selector is narrow and robust enough to carry
  forward

## Decision

Advance the branch to one more offline narrowing step:

- sweep family view and score-band width before turning this into a code or
  runtime microprobe

Do not jump straight to:

- a multi-hour runtime
- another generic family-diversity study
- another entry-allocation branch
