# No-WLI eight-seed hard panel review summary

Date: 2026-04-07

## Purpose

This note summarizes where the no-WLI programme stands after the finished
eight-seed `p9/c3` hard panel:

- `seed411`
- `seed611`
- `seed711`
- `seed811`
- `seed911`
- `seed1011`
- `seed1111`
- `seed1211`

It is intended as a reviewer-facing summary of:

- what is now supported
- what is still not supported
- what the current hard-seed taxonomy appears to be
- what the next best measurement question is

## Short version

The programme now supports a broader claim about bounded late-stage utility
than it did after the six-seed panel, but it still does not support a broad
claim about selector generality.

What is now real:

- `seed411` is a proven selector-sensitive late-stage win
- `seed611`, `seed711`, `seed1011`, and `seed1111` are selector-neutral bounded
  Stage 3.5 wins
- `seed811` is a selector-sensitive reject / no-lift case
- `seed911` is a selector-neutral reject / no-lift case
- `seed1211` is a selector-neutral reject whose baseline winner comes from
  `phaseA_selected`, so it may be a distinct reject subshape from `seed911`

So the current evidence says:

- bounded Stage 3.5 utility is broader than one seed or one family
- selector override is still only clearly causal on `seed411`
- the hard-seed space now looks like a real multi-shape taxonomy, not a single
  story

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
- `seed1111`
  - `best_match_ratio = 0.519`
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
- `seed1211`
  - `best_match_ratio = 0.304`
  - `best_stage = stage3_full_refine`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline from `phaseA_selected`

## Current programme reading

### What is supported

1. Bounded Stage 3.5 utility is clearly broader than the exact `411` family.

Evidence:

- `seed611`, `seed711`, `seed1011`, and `seed1111` all win late without
  needing a selector override
- `seed411` remains a real live late-stage win under the same bounded lane

2. Selector-sensitive late divergence exists beyond `411`.

Evidence:

- `seed811` is a fresh current-code case where
  `stage35_baseline_differs_from_phasec_score_winner = 1`

3. Selector-sensitive divergence is not enough by itself.

Evidence:

- `seed811` still rejects in Stage 3.5 and does not beat Stage 3

4. The current hard-seed space is genuinely multi-shape.

At minimum the finished panel now suggests:

- selector-sensitive win
- selector-neutral bounded late win
- selector-sensitive reject / no-lift
- selector-neutral reject / no-lift
- selector-neutral reject / no-lift with `phaseA_selected` baseline
  (`seed1211`, provisional as a distinct subshape)

### What is still not supported

1. Selector generality is not proven.

The only clearly causal selector-sensitive win remains `seed411`.

2. Broad promotion is not justified.

The panel is still small, and there are clear hard negatives alongside the
wins.

3. A single shared hard-family story is not supported.

The fresh seeds do not collapse into one visible behavior.

## Map / atlas reading

Fresh atlas outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260407T005632Z__space_map_v1_atlas/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260407T005632Z__space_map_v1_audit/`

Useful late-boundary pattern:

- `seed711`
  - `phaseC_start family_count = 2`
  - `stage35_seed family_count = 1`
  - accepted late win
- `seed1011`
  - `phaseC_start family_count = 3`
  - `stage35_seed family_count = 1`
  - accepted late win
- `seed1111`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - accepted late win
- `seed811`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - rejected late continuation
- `seed911`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - rejected late continuation
- `seed1211`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - rejected late continuation

Working interpretation:

- the clean selector-neutral wins (`611`, `711`, `1011`, `1111`) look like
  cases where bounded Stage 3.5 can exploit an already-usable late family
- coarse late family-count compression alone is not enough to explain win
  versus reject:
  - `seed1111` and `seed911` both look broadly like `6 -> 2 -> 1`
  - but `1111` accepts and `911` rejects
- `seed1211` broadens the reject side in a potentially important way:
  - it is selector-neutral like `911`
  - but its baseline winner comes from `phaseA_selected`
  - so it may be a different reject subshape rather than just another
    `phaseB_topk` negative
- `411` remains distinct because the useful late path depends on switching away
  from the Phase C score winner

## Measurement cautions

1. `stage35_seed` should be read using the new reviewer-facing fields:

- `review_primary_row_count`
- `review_primary_row_count_kind`
- `review_primary_relation`

Do not over-read raw `selected_row_count` there.

2. Stage 3 prep ancestry is still partly fallback scaffolding.

So the current map is good enough for late-boundary compression reading, but
not yet strong enough for bold global connectivity claims.

## Recommended next step

The highest-value immediate science question is now in the stop layer, not in
more seed collection.

Recommended order:

1. keep the eight-seed panel as the reviewer-ready taxonomy set
2. refine `score_stop_shadow_v2` before more live seed runs:
  - inspect the `411` miss against the `1011` hit
  - use persisted blocker diagnostics, not ad hoc reads
  - keep dump and stop separate
  - keep stop shadow-only and stricter than dump
3. only return to new live seeds after the next stop read is complete

## Bottom line

The best compact reviewer reading is:

- `411` is still the only proven selector-sensitive live win
- bounded Stage 3.5 utility is now broader across hard seeds
- the hard-seed space appears to contain multiple distinct shapes
- `1211` may be the first sign of a second selector-neutral reject subtype
- the panel is now strong enough for a real taxonomy discussion
- but it is still too early for broad solver or selector promotion
