# No-WLI hard-seed panel review summary

Date: 2026-04-06

## Purpose

This note summarizes where the no-WLI programme stands after the finished
single-job hard-seed panel:

- `p9/c3 seed411`
- `p9/c3 seed611`
- `p9/c3 seed711`
- `p9/c3 seed811`
- `p9/c3 seed911`
- `p9/c3 seed1011`

It is intended as a reviewer-facing summary of:

- what is now supported
- what is still not supported
- what the current hard-seed taxonomy appears to be
- what the next best discriminator is

## Short version

The programme now supports a stronger claim about bounded late-stage utility
than it did before, but still not a broad claim about selector generality.

What is now real:

- `seed411` is a proven selector-sensitive late-stage win
- `seed611`, `seed711`, and `seed1011` are selector-neutral bounded Stage 3.5
  wins
- `seed811` is a selector-sensitive late-stage reject / no-lift case
- `seed911` is a selector-neutral late-stage reject / no-lift case

So the current evidence says:

- bounded Stage 3.5 utility is broader than one seed or one family
- selector override is still only clearly causal on `seed411`
- the hard-seed space already looks multi-shape, not single-shape

## Core live results

### Hard-seed wins

- `seed411`
  - `best_match_ratio = 0.487`
  - `best_stage = stage35_substitution_only`
  - `stage35_accept_reason = accepted`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - baseline from `phaseA_selected`
- `seed611`
  - `best_match_ratio = 0.635`
  - `best_stage = stage35_substitution_only`
  - `stage35_accept_reason = accepted`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline from `phaseB_topk`
- `seed711`
  - `best_match_ratio = 0.761`
  - `best_stage = stage35_substitution_only`
  - `stage35_accept_reason = accepted`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline from `phaseB_topk`
- `seed1011`
  - `best_match_ratio = 0.737`
  - `best_stage = stage35_substitution_only`
  - `stage35_accept_reason = accepted`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline from `phaseB_topk`

### Hard-seed rejects / no-lift cases

- `seed811`
  - `best_match_ratio = 0.475`
  - `best_stage = stage3_full_refine`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 1`
  - baseline from `phaseA_selected`
- `seed911`
  - `best_match_ratio = 0.176`
  - `best_stage = stage2_search`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline from `phaseB_topk`

## Current programme reading

### What is supported

1. Bounded Stage 3.5 utility is now clearly broader than the exact `411`
   family.

Evidence:

- `seed611`, `seed711`, and `seed1011` all win late without needing a selector
  override
- `seed411` still remains a real live late-stage win under the bounded lane

2. Selector-sensitive late divergence exists beyond `411`.

Evidence:

- `seed811` is a fresh current-code case where
  `stage35_baseline_differs_from_phasec_score_winner = 1`

3. Selector-sensitive divergence is not enough by itself.

Evidence:

- `seed811` still rejects in Stage 3.5 and does not beat Stage 3

4. The current hard-seed space is already multi-shape.

At minimum the finished panel now suggests:

- override-sensitive win
- selector-neutral bounded late win
- override-sensitive reject / no-lift
- selector-neutral reject / no-lift

### What is still not supported

1. Selector generality is not proven.

The only clearly causal selector-sensitive win remains `seed411`.

2. Broad promotion is not justified.

The panel is still small, and there are clear hard negatives (`seed811`,
`seed911`) alongside the wins.

3. A single shared hard-family story is not supported.

The fresh seeds do not all collapse into one visible behavior.

## Map / atlas reading

Fresh atlas outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260406T144043Z__space_map_v1_atlas/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260406T144043Z__space_map_v1_audit/`

Useful late-boundary pattern:

- `seed711`
  - `phaseC_start family_count = 2`
  - `stage35_seed family_count = 1`
  - accepted late win
- `seed1011`
  - `phaseC_start family_count = 3`
  - `stage35_seed family_count = 1`
  - accepted late win
- `seed811`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - rejected late continuation
- `seed911`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - rejected late continuation

Working interpretation:

- the clean selector-neutral wins (`611`, `711`, `1011`) look like cases where
  the late frontier is already concentrated enough for bounded Stage 3.5 to
  exploit
- the two reject cases (`811`, `911`) still carry broader or less stable late
  diversity and do not convert into accepted continuation
- `411` remains distinct because the useful late path depends on switching away
  from the Phase C score winner

## Measurement cautions

1. `stage35_seed` should be read using the new reviewer-facing fields:

- `review_primary_row_count`
- `review_primary_row_count_kind`
- `review_primary_relation`

Do not over-read raw `selected_row_count` there.

2. Stage 3 prep ancestry is still partly fallback scaffolding.

So the current map is good enough for late-boundary compression reading, but not
yet strong enough for bold global connectivity claims.

## Recommended next step

If the goal is the highest-value next discriminator, I would choose one of
these, in order:

1. One more fresh hard seed

Reason:

- the current panel is now broad enough to justify testing whether the emerging
  shapes repeat again

2. A targeted control only if a new selector-sensitive seed appears

Reason:

- the selector question is already answered for `611`
- the next clean selector discriminator would only be worth paying for if we
  get another non-`411` case like `811`, where override fires again

## Bottom line

The best compact reviewer reading is:

- `411` is still the only proven selector-sensitive live win
- bounded Stage 3.5 utility is now broader than `411`
- the hard-seed space already appears to contain multiple distinct shapes
- the panel is now strong enough for a real taxonomy discussion
- but it is still too early for broad solver or selector promotion
