# No-WLI `space_map_v1` classifier spec v1

## Purpose

Define a first-pass, auditable classifier vocabulary for partial states, pools,
and runs saved in `stage3_diagnostics.space_map_v1`.

This is a **science/reporting layer only**. It is not a live solver policy.

## Core rule

Classifier labels must be deterministic from saved artifact fields and
provisional thresholds. If a label cannot be assigned safely from current
`space_map_v1` data, the classifier should emit a conservative fallback label
and record a data-gap flag rather than inventing certainty.

## Row-type labels

- `repair_candidate`
  - `admitted_by_next_stage = 1`
  - `continued_best_match >= final_match + 0.01`
- `false_friend`
  - `score_gain >= 0.002`
  - `match_gain <= -0.001`
- `promising_outsider`
  - `eligible = 1`
  - `selected = 0`
  - `distance_to_anchor >= 0.10`
  - `score_gain >= 0`
  - `match_gain >= -0.005`
- `undervalued_good_family`
  - `selected = 0`
  - `final_match >= 0.30`
  - `distance_to_anchor >= 0.05`
- `good_family_not_exploited`
  - `selected = 0`
  - `admitted_by_next_stage = 0`
  - `final_match >= 0.30`
- `weak_family_survivor`
  - `selected = 1`
  - `final_match < 0.20`
  - `abs(match_gain) <= 0.01`
- `dead_path`
  - `selected = 0`
  - `admitted_by_next_stage = 0`
  - `final_match < 0.10`
- `unclassified_row`
  - fallback

## Pool-type labels

- `not_run_pool`
  - `pool_status = "not_run"`
- `empty_pool`
  - `pool_status = "empty"`
- `single_hill_pool`
  - `family_count <= 1`
  - `row_count > 0`
- `broad_multi_hill_pool`
  - `family_count >= 4`
  - `largest_family_share <= 0.5`
- `compressed_multi_hill_pool`
  - `family_count >= 2`
  - `largest_family_share > 0.5`
- `unclassified_pool`
  - fallback

## Run-type labels

- `solved_control`
  - `best_match_ratio >= 0.999`
- `stage35_live_win`
  - `stage35_accept_passed = 1`
  - `best_stage = "stage35_substitution_only"`
  - `best_match_ratio >= 0.30`
- `stage35_noop_reject`
  - `stage35_accept_reason = "top_candidate_matches_baseline"`
- `stage35_guard_reject`
  - `stage35_accept_reason = "search_score_drop_guard_failed"`
- `incomplete_or_capped`
  - `stage35_outcome_status != "completed"` or `stage35_capped = 1`
- `unclassified_run`
  - fallback

## Data-gap flags

- `missing_space_map_v1`
- `missing_space_map_run_id`
- `missing_partial_state_rows`
- `missing_pool_summaries`
- `missing_parent_candidate_hash`
- `missing_family_id`
- `missing_distance_to_anchor`
- `missing_continued_best_links`
- `missing_stage35_progress_paths`
- `phasec_pool_not_row_complete`

## Seed-category comparison rule

This classifier should support a small **seed taxonomy** study, not just
single-run labels.

Maintain two kinds of seed roles:

- anchor seeds:
  - keep `411` as a fixed hard-case reference so new runs remain comparable to
    the known `9002...` continuation mechanism
- probe seeds:
  - use fresh seeds such as `611` and `711` to test whether the same hill
    families and pool-compression patterns repeat

Post-run comparison dimensions:

- `run_type`
- per-boundary `pool_type`, `family_count`, and `largest_family_share`
- whether the selected Stage 3.5 baseline and accepted archive rows share a
  repeated `family_id` or parent-path motif across seeds
- whether a seed is best described as:
  - repeated solved-control behavior,
  - repeated `411`-like hard-family behavior,
  - or a new hard family

Interpretation caveat:

- if all seeds appear unique, treat that as a **descriptor-quality warning**
  as well as a possible solver-space fact
- in that case, inspect `missing_family_id`, `missing_distance_to_anchor`, and
  fallback parent links before concluding that no repeated hill structure
  exists

## Known limitations

- Stage 2 promoted pools, Stage 3 prep pools, and row-complete Phase C pools
  are now serialized for fresh artifacts, but older artifacts still predate
  those fields.
- `family_id` is still a first-pass cluster label under one family view, not a
  proven hill ontology.
- Stage 3 prep mutated-row parent links may still fall back to the prep anchor
  when exact mutation-origin metadata is absent.
- continued-best links are strongest at Stage 3.5 and still sparse at earlier
  boundaries.

## Bottom line

This first-pass classifier is there to make space-map artifacts easier to
audit and discuss. It should stay deterministic, provisional, and separate
from live solver decisions.
