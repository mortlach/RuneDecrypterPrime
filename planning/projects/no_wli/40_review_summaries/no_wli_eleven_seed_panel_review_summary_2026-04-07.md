# No-WLI eleven-seed hard panel review summary

Date: 2026-04-07

## Purpose

This note summarizes where the no-WLI programme stands after the finished
eleven-seed `p9/c3` hard panel:

- `seed411`
- `seed611`
- `seed711`
- `seed811`
- `seed911`
- `seed1011`
- `seed1111`
- `seed1211`
- `seed1311`
- `seed1411`
- `seed1511`

It is intended as a reviewer-facing summary of:

- what is now supported
- what is still not supported
- what the current hard-seed taxonomy appears to be
- what the stop cross-check now says after the new reject seeds

## Short version

The atlas / map project is healthy and more useful than before.

The finished eleven-seed panel now supports a real fresh-seed taxonomy:

- `411` remains the only proven selector-sensitive live win
- `611`, `711`, `1011`, and `1111` are selector-neutral bounded Stage 3.5 wins
- `811` is a selector-sensitive reject
- `911` is a selector-neutral reject
- `1211` and `1411` look like a selector-neutral reject subtype with
  `phaseA_selected` baselines
- `1311` and `1511` look like a selector-neutral reject subtype with
  `phaseB_topk` baselines and moderate late truth

The stop project also learned something important:

- the locked harness-backed dump result still stands
- but the new `v69` seeds create real broader false-positive pressure

So the map side remains strong, while the stop side is still best described as
an offline dump-calibration harness rather than a policy candidate.

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
- `seed1311`
  - `best_match_ratio = 0.570`
  - `best_stage = stage3_full_refine`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline from `phaseB_topk`
- `seed1411`
  - `best_match_ratio = 0.264`
  - `best_stage = stage3_full_refine`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline from `phaseA_selected`
- `seed1511`
  - `best_match_ratio = 0.583`
  - `best_stage = stage3_full_refine`
  - `stage35_accept_reason = search_score_drop_guard_failed`
  - `stage35_baseline_differs_from_phasec_score_winner = 0`
  - baseline from `phaseB_topk`

## Current programme reading

### What is supported

1. Bounded Stage 3.5 utility is clearly broader than the exact `411` family.

Evidence:

- `seed611`, `seed711`, `seed1011`, and `seed1111` all win late without
  needing a selector override
- `seed411` remains a real live late-stage win under the same bounded lane

2. Selector-sensitive late divergence exists beyond `411`, but is not enough by
   itself.

Evidence:

- `seed811` is a fresh current-code case where
  `stage35_baseline_differs_from_phasec_score_winner = 1`
- `seed811` still rejects and does not beat Stage 3

3. The current hard-seed space is genuinely multi-shape.

At minimum the finished panel now suggests:

- selector-sensitive win
- selector-neutral bounded late win
- selector-sensitive reject / no-lift
- selector-neutral reject / no-lift
- selector-neutral reject / no-lift with `phaseA_selected` baseline
- selector-neutral reject / no-lift with `phaseB_topk` baseline and moderate
  late truth

### What is still not supported

1. Selector generality is not proven.

The only clearly causal selector-sensitive win remains `seed411`.

2. Broad promotion is not justified.

The panel is still small, and the reject side is now materially richer.

3. A single shared hard-family story is not supported.

The new seeds continue to widen the taxonomy rather than collapse it.

## Map / atlas reading

Fresh atlas outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260407T235219Z__space_map_v1_atlas/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260407T235219Z__space_map_v1_audit/`

Useful late-boundary pattern:

- `seed1111`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - accepted late win
- `seed1211`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - rejected late continuation
- `seed1311`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - rejected late continuation
- `seed1411`
  - `phaseC_start family_count = 6`
  - `stage35_seed family_count = 2`
  - `stage35_archive family_count = 1`
  - rejected late continuation
- `seed1511`
  - `phaseC_start family_count = 2`
  - `stage35_seed family_count = 1`
  - `stage35_archive family_count = 1`
  - rejected late continuation

Working interpretation:

- coarse late family-count compression alone is not enough to explain win
  versus reject
- `1111`, `1211`, `1311`, and `1411` can all look broadly like `6 -> 2 -> 1`
  while only `1111` converts
- `1511` shows that even a strong-looking `2 -> 1 -> 1` late compression shape
  can still reject
- so the atlas is useful for taxonomy and loss-point reading, but not yet for a
  simple “compressed means good” conclusion

## Stop cross-check

### Harness-backed result

The locked `score_stop_shadow_v2` harness-backed panel covers:

- solved control `511`
- hard seeds `411`, `611`, `711`, `811`, `911`, `1011`, `1111`, `1211`

From that locked panel:

- trust-led dump fires on:
  - `511`
  - `611`
  - `711`
  - `1011`
- archive-only same-family uplift fallback fires on:
  - `411`
- dump stays quiet on:
  - `811`
  - `911`
  - `1211`
- accepted win `1111` still misses
- no shadow stop fires

### Wider `v69` cross-check

The three fresh `v69` seeds were then checked against the same current dump
logic:

- `1311`
  - would dump under the trust-led branch
- `1411`
  - would dump under the archive-uplift fallback
- `1511`
  - stays quiet

This matters because it means:

- the locked harness result is still useful and clean on its target set
- but the current dump layer does not generalize cleanly to the wider
  eleven-seed panel

So the stop project should still be described as:

- offline only
- dump-calibration first
- stop-shadow-only
- not a policy candidate yet

## Measurement cautions

1. `stage35_seed` should be read using the reviewer-facing fields:

- `review_primary_row_count`
- `review_primary_row_count_kind`
- `review_primary_relation`

Do not over-read raw `selected_row_count` there.

2. Stage 3 prep ancestry is still partly fallback scaffolding.

So the current map is good enough for late-boundary compression reading, but
not yet strong enough for bold global connectivity claims.

3. The current stop layer should be reported with a clean evidence split:

- what the locked harness proves
- what the wider fresh-seed falsification read adds

## Recommended next step

The highest-value immediate question is still in the stop layer, not another
live seed run.

Recommended order:

1. keep the eleven-seed panel as the reviewer-ready taxonomy set
2. keep stop shadow-only
3. use `1111` as the accepted-win discriminator
4. use `1311` and `1411` as the new false-positive tests
5. only consider another dump axis after review of that evidence

## Bottom line

The best compact reviewer reading is:

- the atlas / taxonomy side is healthy and already useful
- bounded Stage 3.5 utility is broader across hard seeds
- selector generality is still not proven
- the hard-seed space now has at least six visible shapes
- the stop side is better than before, but broader generalization is still not
  clean

That is a strong place to pause, review, and tighten the stop science before
collecting more live seeds.
