# Stage-2 Topk Family Representative Policy Sensitivity Plan

Date: 2026-04-22

Status:

- completed
- branch-finalizing offline sweep

## Why this note exists

The first concrete representative-policy audit found one promising selector:

- `selected_family_low_edge_eps_0p020_v1`

That was enough to say "a selector exists", but not enough to say:

- whether the policy depends on one arbitrary family view
- whether the score band is narrow and well-behaved
- which exact setting should become the next honest microprobe

This note records the required narrowing sweep.

## Main question

Is the `1111` representative-selection signal robust enough to specify one
narrow selector, or is it just a lucky family-view / score-band combination?

## Mechanism layer

- selection

## Pre-run block

Question:

- across the existing no-WLI family views and a small band-width sweep, is
  there one narrow selector that helps `1111` while staying inert on the
  controls?

Suspicion:

- the useful selector lives on the `prefix_hamming_le_24` family view
- the usable band is narrow
- there is a smallest positive width that captures the hidden stronger `1111`
  row without over-widening

Main alternative:

- the policy is view-dependent in a loose or arbitrary way
- or the score-band behaviour is unstable, harmful, or too broad to justify a
  microprobe

If suspicion is true, expect:

- only one family view to show a clean `1111`-only activation window
- a lower band to stay inert or harmful
- a slightly wider band to stay positive or attenuate
- controls to remain inert

If alternative is true, expect:

- multiple conflicting view-specific positives
- or no stable positive window
- or meaningful control movement

Tomorrow's decision rule:

- advance only if one setting isolates a clean `1111`-only positive window and
  identifies the smallest viable band
- refine if the pattern is promising but still ambiguous
- close if the signal depends on arbitrary or contradictory settings

## What we expect to learn

This sweep is meant to answer:

- whether the candidate policy is real rather than accidental
- which exact family view and score band should be carried into the next
  microprobe
- whether the next branch can now be specified as one concrete selector id

## Why this is the right science-method step now

This is the last cheap offline narrowing step before any replay or runtime:

- the diagnosis is already done
- the first concrete policy already exists
- now the branch needs one explicit minimal viable selector, not another broad
  runtime

## Frozen inputs

Use exactly:

- `planning/projects/no_wli/40_review_summaries/no_wli_fixed_panel_v1_external_review_pack_2026-04-14/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T025743Z__stage2_topk_family_representative_policy_audit_v1/`

## Implementation

Single-script offline sweep:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage2_topk_family_representative_policy_sensitivity_v1.py`

Focused proof:

- `tests/tools/test_no_wli_stage2_topk_family_representative_policy_sensitivity_v1.py`

Swept family views:

- `exact_key`
- `exact_tail`
- `near_tail_h1`
- `prefix_hamming_le_24`

Swept score bands:

- `0.010`
- `0.015`
- `0.016`
- `0.020`
- `0.025`

## Required outputs

This sweep must emit:

- one machine-readable case table
- one machine-readable setting-summary table
- one short markdown readout
- one explicit advance / refine / close recommendation

Completed output bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260423T030450Z__stage2_topk_family_representative_policy_sensitivity_v1/`

## Result

Recommendation:

- `advance`

Next branch:

- `stage2_topk_selected_family_low_edge_eps_0p016_microprobe`

Chosen policy:

- `selected_family_low_edge_eps_0p016_v1`

Main read:

- only `prefix_hamming_le_24` produces any clean `1111`-only activation window
- on that family view:
  - `eps = 0.015` is harmful on `1111`:
    - mean delta `-0.023`
  - `eps = 0.016` is the smallest clean positive:
    - mean delta `+0.070`
  - `eps = 0.020` stays equally positive:
    - mean delta `+0.070`
  - `eps = 0.025` over-widens and attenuates:
    - mean delta `+0.005`
- controls remain inert across the whole sweep

Interpretation:

- the selector is not an arbitrary cross-view artifact
- the useful window is narrow and asymmetric
- the smallest clean viable band is now explicit

## Decision

Advance to a concrete microprobe defined as:

- family view:
  - `prefix_hamming_le_24`
- selector:
  - `selected_family_low_edge_eps_0p016_v1`

Do not advance with:

- `eps = 0.015`
- broader `eps = 0.025`
- any non-`prefix_hamming_le_24` family view
