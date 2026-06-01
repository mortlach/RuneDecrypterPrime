# Stage-2 to Stage-3 Promoted Family Audit Plan

Date: 2026-04-22

Status:

- first-pass offline audit completed
- branch decision ready

## Why this note exists

The fixed `1111/search7004` entry-allocation line is now closed:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_closure_note_2026-04-22.md`

That closure changed the next science step.

It did not justify another vague upstream runtime.

The right correction was:

- move upstream first
- stay offline first
- test whether `1111` is missing the right promoted family at all, or whether
  it already carries a better family but surfaces the wrong representative
  inside it before Stage 3 starts

This note records that study and its result.

## Main question

On the fixed primary trio, does `1111` fail because upstream
`stage2_topk -> stage2_promoted -> stage3_prep` supply is missing the right
family, or because it already carries a better family but keeps surfacing a
weak representative inside it before Stage 3 starts?

## Mechanism layer

- selection

## Pre-run block

Question:

- on the fixed primary trio, what exactly is the upstream family problem class
  on `1111`:
  - family absence / weak diversity
  - or within-family representative selection

Suspicion:

- `1111` does not mainly lack promoted-family variety
- it already carries a better upstream family region, but the top score row is
  a poor representative inside that region, and this survives into
  `stage2_promoted`

Main alternative:

- the stronger `1111` family is genuinely absent or too weakly represented
  upstream, so the next branch should target promoted-family mix / diversity
  rather than representative selection

If suspicion is true, expect:

- `1111` to show a persistent upstream within-family gap at both:
  - `stage2_topk`
  - `stage2_promoted`
- `1111` cross-family gap to stay smaller than the within-family gap
- controls `611` and `1511` to stay near zero on the same within-family metric

If alternative is true, expect:

- `1111` to show a larger cross-family gap than within-family gap
- or `1111` to show no stable upstream distinction from `611` and `1511`

Tomorrow's decision rule:

- advance if `1111` shows a persistent within-family upstream gap while the
  controls do not
- advance to diversity / family-mix work only if `1111` looks cross-family
  blocked instead
- refine if the offline read stays mixed or unstable

## What we expect to learn

This study is meant to answer three things cheaply:

- whether the current `1111` failure is already visible before Stage 3 local
  search
- whether the next honest mechanism is upstream representative selection or
  upstream family diversity
- whether another multi-hour runtime is justified before one more offline audit

## Why this is the right science-method step now

This is the method correction after the closed allocation probe:

- stop spending runtime where the mechanism is still poorly specified
- use the retained fixed panel to identify the actual upstream failure class
- only then write the next microprobe

So this step is deliberately:

- offline
- frozen-input only
- primary-trio only
- one mechanism-layer diagnosis

## Frozen inputs

Use exactly:

- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260415T160503Z__fixed_instance_solver_development_v1/1111_conversion_compare_rows.csv`

Do not auto-discover newer panel evidence.

## Implementation

Single-script offline audit:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_stage3_promoted_family_audit_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage2_stage3_promoted_family_audit_v1.py`

Primary family view:

- `prefix_hamming_le_24`

Primary fixed cases:

- `611/search7001-7005`
- `1111/search7001-7005`
- `1511/search7001-7005`

## Required outputs

This audit must emit:

- one machine-readable case table
- one machine-readable fixture summary table
- one short markdown readout
- one explicit advance / refine / close recommendation

Completed output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T014608Z__stage2_stage3_promoted_family_audit_v1/`

## First-pass result

Recommendation:

- `advance`

Next branch:

- `stage2_stage3_within_family_representative_selection_microprobe`

Main read:

- `1111` is the only seed family in the primary trio with a persistent
  upstream within-family representative gap
- mean `stage2_topk` within-family gap on `1111`:
  - `0.070`
- mean `stage2_promoted` within-family gap on `1111`:
  - `0.070`
- mean `stage2_promoted` between-family gap on `1111`:
  - `0.014`
- controls stay near zero:
  - `611` promoted within-family gap:
    - `0.000`
  - `1511` promoted within-family gap:
    - `0.000`

Interpretation:

- the current `1111` problem does not primarily look like missing promoted
  family diversity
- it looks like upstream representative selection inside an already-present
  family region

## Decision

Advance the branch, but not to another runtime yet.

Advance to:

- a small upstream within-family representative-selection microprobe

Do not advance to:

- another generic family-diversity audit
- another entry-allocation rerun
- another multi-hour same-cell runtime before the microprobe is specified
