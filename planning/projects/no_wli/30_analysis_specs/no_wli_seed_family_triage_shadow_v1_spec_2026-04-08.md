---

# No-WLI seed-family-triage-shadow v1 spec

Date: 2026-04-08

## Purpose

Build a new **offline-only shadow triage and budget-allocation study** on top of the frozen:

* `score_stop_shadow_v2`
* `late_family_quality_v1`
* `late_family_quality_v2`
* `late_family_quality_v3`

This is **not** an early-stop policy.

This is **not** a promoted family-quality head.

This is a bounded study whose purpose is:

**use the current stop and family-quality results to rank seeds and families for follow-up budget, while keeping all recommendations shadow-only and non-gating.**

In plain English:

* not “stop early because we’ve won”
* but “spend more time on the right seeds and the right families earlier”

---

## Why this is the next move

The current programme has not produced a trustworthy stop rule.

But it has produced something useful:

* `score_stop_shadow_v2` is now a stable benchmark / explanation harness
* `late_family_quality_v1` showed real family-level signal
* `late_family_quality_v2` found meaningful winner-family split patterns
* `late_family_quality_v3` strengthened the accepted-miss side, but did **not** produce clean stronger suspicious labels for the false-fire pair under the stricter combined read

So the evidence supports:

* **better triage and budget allocation**
* but **not** a hard stop policy

That is the basis of this study.

---

## Study stance

This study is:

* offline only
* deterministic
* shadow only
* non-gating
* intended to improve prioritisation and budget allocation
* allowed to combine stop-side and family-side evidence
* allowed to emit budget recommendations
* not allowed to control the live solver yet

This study is **not**:

* a new stop-rule branch
* a live-policy promotion
* a replay-score redesign
* a family re-clustering effort
* a new live-seed campaign
* a promoted score head
* a hard kill rule for seeds or families

---

## Recommended code location

Create a new analysis branch:

* `tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/`

with:

* `SPEC.md`
* `EXPERIMENT_PLAN.md`
* `extract_seed_family_triage_shadow_v1.py`

Add tests in:

* `tests/tools/test_no_wli_seed_family_triage_shadow_v1.py`

Keep this separate from:

* `score_stop_shadow_v2`
* `late_family_quality_v1`
* `late_family_quality_v2`
* `late_family_quality_v3`

This must consume frozen outputs, not import evolving internal helpers.

---

## Frozen input contract

### Required frozen bundles

#### Stop harness bundle

Use:

```python
INPUT_SCORE_STOP_BUNDLE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2"
)
```

Required files:

* `run_shadow_summary.jsonl`
* `row_scores.jsonl`
* `case_explanations.jsonl`

#### Family quality v1 bundle

Use:

```python
INPUT_LFQ_V1_BUNDLE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v1/20260408T152322Z__late_family_quality_v1"
)
```

Required files:

* `family_quality_rows.jsonl`
* `family_quality_case_digest.jsonl`
* `family_quality_summary.json`

#### Family quality v2 bundle

Use:

```python
INPUT_LFQ_V2_BUNDLE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v2/20260408T154637Z__late_family_quality_v2"
)
```

Required files:

* `seed_agreement_rows.jsonl`
* `winner_pairwise_rows.jsonl`
* `agreement_summary.json`

#### Family quality v3 bundle

Use:

```python
INPUT_LFQ_V3_BUNDLE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v3/20260408T162219Z__late_family_quality_v3"
)
```

Required files:

* `pattern_strength_rows.jsonl`
* `truth_relative_pair_rows.jsonl`
* `pattern_strength_summary.json`

### Important rule

Do **not** auto-discover “latest” bundles.

Reason:

* the triage study must be deterministic
* input drift would make budget recommendations hard to compare
* we want the review pack and the triage study to remain explicitly linked

---

## Frozen seed contract

This study has two seed scopes.

### Scope A: full review-panel seeds

These are the seeds that must receive a seed-level triage row.

Core panel:

* `511`
* `411`
* `611`
* `711`
* `811`
* `911`
* `1011`
* `1111`
* `1211`

Pressure panel:

* `1311`
* `1411`
* `1511`

Define:

```python
TRIAGE_CORE_PANEL_SEEDS = (511, 411, 611, 711, 811, 911, 1011, 1111, 1211)
TRIAGE_PRESSURE_PANEL_SEEDS = (1311, 1411, 1511)
TRIAGE_REVIEW_SEEDS = (
    511, 411, 611, 711, 811, 911, 1011, 1111, 1211,
    1311, 1411, 1511,
)
```

### Scope B: family-enriched seeds

These are the seeds that must also receive family-level triage rows and budget recommendations using v1/v2/v3 family-quality data.

* `1111`
* `1311`
* `1411`
* `411`
* `611`
* `1011`

Define:

```python
TRIAGE_FAMILY_ENRICHED_SEEDS = (1111, 1311, 1411, 411, 611, 1011)
```

### Important rule

Do not widen either seed set in v1.

The point is to build a disciplined shadow triage layer against the frozen review pack, not to drift into a new data-collection phase.

---

## Units of analysis

This study has two output levels.

### 1. Seed-level triage row

One row per seed in `TRIAGE_REVIEW_SEEDS`.

Purpose:

* tell us how promising the seed looks overall
* recommend a follow-up priority
* recommend a seed-level budget policy
* state whether the read is family-enriched or stop-only

### 2. Family-level priority row

One row per family for seeds in `TRIAGE_FAMILY_ENRICHED_SEEDS`.

Purpose:

* tell us which families deserve more, normal, or minimal continuation budget
* rank families within a seed
* recommend a shadow portfolio split

---

## What this study must include that earlier branches did not

This section is here on purpose.

The dev must not silently leave these out.

### Required inclusions

1. **Seed-level rows for all 12 review seeds**

   * not only the six family-enriched seeds

2. **Family-level rows for the six enriched seeds**

   * backed by v1 family rows and v3 strength read

3. **Explicit evidence tier**

   * every seed row must say whether its read is:

     * `family_enriched`
     * or `stop_only`

4. **Budget policy output**

   * not just labels
   * must include an explicit recommended portfolio split

5. **Reason codes**

   * every seed row and family row must have short reason codes
   * not just one free-text explanation paragraph

6. **No gating**

   * no row may recommend zero budget
   * even the weakest case must keep a non-zero exploration share

7. **No inherited decision dependence**

   * earlier labels may be used as inputs
   * but the main triage decision must be derived inside this study

8. **Clear fallback for non-enriched seeds**

   * seeds without v1/v2/v3 family-quality rows must still get a seed triage row
   * but with lower-confidence evidence tier

---

## Inputs to read

### From stop harness

#### From `run_shadow_summary.jsonl`

Read:

* `artifact_path`
* `key_seed`
* `run_type`
* `target_panel_name`
* `target_panel_role`
* `would_dump`
* `would_stop`
* `shadow_rule_id`

#### From `case_explanations.jsonl`

Read:

* `key_seed`
* `case_shape_label`
* `decision_axis_label`
* `primary_explanation`

### From family quality v1

#### From `family_quality_rows.jsonl`

Read:

* `key_seed`
* `family_id`
* `study_role`
* `family_role_label`
* `best_truth`
* `best_trust`
* `best_archive_uplift`
* `best_full_uplift`
* `boundary_count`
* `boundaries_seen`
* `family_persistence_count`
* `family_reaches_archive`
* `truth_trend_label`
* `trust_trend_label`
* `archive_uplift_trend_label`
* `full_uplift_trend_label`

#### From `family_quality_case_digest.jsonl`

Read:

* `key_seed`
* `truth_winner_family_id`
* `trust_winner_family_id`
* `archive_uplift_winner_family_id`
* `full_uplift_winner_family_id`
* `persistence_winner_family_id`
* `family_quality_read_label`

### From family quality v2

#### From `seed_agreement_rows.jsonl`

Read:

* `key_seed`
* `winner_pattern_key`
* `pattern_bucket_label`
* `unique_winner_family_count`
* `truth_agreement_count`

### From family quality v3

#### From `pattern_strength_rows.jsonl`

Read:

* `key_seed`

* `winner_pattern_key`

* `split_pattern_label`

* `pattern_strength_read_label`

* `truth_winner_strength_label`

* `trust_winner_strength_label`

* `archive_winner_strength_label`

* `full_uplift_winner_strength_label`

* `persistence_winner_strength_label`

* `truth_minus_trust_winner_best_truth`

* `truth_minus_archive_winner_best_truth`

* `truth_minus_full_uplift_winner_best_truth`

* `truth_minus_persistence_winner_best_truth`

* `truth_minus_trust_winner_persistence_count`

* `truth_minus_archive_winner_persistence_count`

* `truth_minus_full_uplift_winner_persistence_count`

* `truth_minus_persistence_winner_persistence_count`

* `truth_vs_trust_boundary_overlap_label`

* `truth_vs_archive_boundary_overlap_label`

* `truth_vs_full_uplift_boundary_overlap_label`

* `truth_vs_persistence_boundary_overlap_label`

#### From `truth_relative_pair_rows.jsonl`

Read:

* `key_seed`
* `pair_name`
* `pair_read_label`

Use this as a cross-check, not as the only source of family ranking.

---

## Seed-level output fields

Create one `seed_triage_rows.jsonl` row per seed.

### Identity

* `key_seed`
* `run_type`
* `target_panel_name`
* `target_panel_role`

### Evidence tier

* `triage_evidence_tier`

Allowed values:

* `family_enriched`
* `stop_only`

Rule:

* `family_enriched` for seeds in `TRIAGE_FAMILY_ENRICHED_SEEDS`
* `stop_only` otherwise

### Current stop state

* `would_dump`
* `would_stop`
* `shadow_rule_id`
* `case_shape_label`
* `decision_axis_label`
* `primary_explanation`

### Family-quality context, if available

* `family_quality_read_label`
* `winner_pattern_key`
* `split_pattern_label`
* `pattern_strength_read_label`
* `truth_winner_strength_label`
* `unique_winner_family_count`
* `truth_agreement_count`

### Main seed-level triage fields

* `seed_priority_band`
* `seed_priority_score`
* `seed_budget_policy_label`
* `recommended_primary_budget_share`
* `recommended_secondary_budget_share`
* `recommended_exploration_budget_share`
* `seed_reason_codes`

`seed_reason_codes` must be a short list of stable codes, not free text.

---

## Seed-level labels

### `seed_priority_band`

Allowed values:

* `high`
* `medium`
* `low`
* `unclear`

### `seed_budget_policy_label`

Allowed values:

* `focus_with_exploration`
* `balanced_portfolio`
* `exploration_heavy`
* `observe_only`

### Portfolio share rules

All recommendations must sum to `1.0`.

Allowed default profiles:

#### `focus_with_exploration`

* primary: `0.60`
* secondary: `0.25`
* exploration: `0.15`

#### `balanced_portfolio`

* primary: `0.45`
* secondary: `0.35`
* exploration: `0.20`

#### `exploration_heavy`

* primary: `0.30`
* secondary: `0.30`
* exploration: `0.40`

#### `observe_only`

* primary: `0.20`
* secondary: `0.20`
* exploration: `0.60`

### Important rule

No seed gets zero exploration.
No seed gets zero total budget.
This is a shadow allocator, not a kill switch.

---

## Seed-level decision rules

These are the main v1 rules.
Keep them deterministic and blunt.

### `high`

Use if any of these are true:

#### Family-enriched strong positive

* `pattern_strength_read_label` is one of:

  * `accepted_miss_reference_like`
  * `reference_like_strong`

#### Stop-only strong positive fallback

* `triage_evidence_tier == "stop_only"`
* `would_dump == 1`
* `case_shape_label` is **not**:

  * `trust_false_fire`
  * `archive_false_fire`

This is mainly for seeds like `511` or `711` where family enrichment is not available in v1.

### `medium`

Use if any of these are true:

* `pattern_strength_read_label == "reference_like_partial"`
* `pattern_strength_read_label == "pattern_only_reference_like_but_strength_weak"`
* `family_quality_read_label` is positive-looking but v3 is unavailable
* stop-only seed dumps cleanly but with no enriched evidence

### `low`

Use if:

* `would_dump == 0`
* and stop-side read is quiet reject-like
* and there is no positive family-enriched evidence

This is mainly for seeds like `811`, `911`, `1211`, `1511`.

### `unclear`

Use if:

* family-enriched seed is still mixed or inconclusive
* or stop-only seed has too little evidence to call it high or low
* especially for:

  * `1311`
  * `1411`

### `seed_priority_score`

Add a simple numeric mapping:

* `high` -> `3`
* `medium` -> `2`
* `unclear` -> `1`
* `low` -> `0`

This is only for sorting summaries.
It is not a promoted control score.

---

## Required seed reason codes

Use only stable codes from this set:

* `reference_like_strong`
* `accepted_miss_reference_like`
* `pattern_only_but_weak`
* `stop_dump_clean`
* `stop_dump_false_fire_like`
* `quiet_reject`
* `pattern_inconclusive`
* `family_strength_inconclusive`
* `stop_only_fallback`
* `same_family_archive_case`
* `truth_family_strong`
* `truth_family_partial`
* `truth_family_weak`

Each seed row should have 1–4 codes.

---

## Family-level output fields

Create one `family_priority_rows.jsonl` row per family for seeds in `TRIAGE_FAMILY_ENRICHED_SEEDS`.

### Identity

* `key_seed`
* `family_id`
* `study_role`
* `family_role_label`

### Family metrics

* `best_truth`
* `best_trust`
* `best_archive_uplift`
* `best_full_uplift`
* `boundary_count`
* `boundaries_seen`
* `family_persistence_count`
* `family_reaches_archive`
* `truth_trend_label`
* `trust_trend_label`
* `archive_uplift_trend_label`
* `full_uplift_trend_label`

### Winner-role flags

* `is_truth_winner`
* `is_trust_winner`
* `is_archive_winner`
* `is_full_uplift_winner`
* `is_persistence_winner`

### Strength context

* `family_strength_label`
* `family_priority_band`
* `family_priority_rank`
* `recommended_family_budget_share`
* `family_reason_codes`

### Allowed `family_strength_label`

* `strong`
* `partial`
* `weak`

Rule:

* same logic as v3 truth-winner strength:

  * strong if persistence count >= 2 and reaches archive == 1
  * partial if exactly one of those is true
  * weak otherwise

### Allowed `family_priority_band`

* `high`
* `medium`
* `low`
* `explore_only`

---

## Family-level priority rules

These are required and must be implemented.

### `high`

Use if:

* family is the truth winner
* and `family_strength_label` is `strong` or `partial`

### `medium`

Use if:

* family is not the truth winner
* but is one of:

  * trust winner
  * archive winner
  * full-uplift winner
  * persistence winner
* and is not clearly weak

### `low`

Use if:

* family is an alternative winner
* but clearly weaker than the truth winner by available gaps
* or it is not any winner family and has weak strength

### `explore_only`

Use if:

* family is neither the truth winner nor a clear strong alternative
* but still exists in the seed and deserves some diversity budget

### Important rule

Every enriched seed must keep at least one non-truth family in:

* `medium`
  or
* `explore_only`

Do not let the study collapse into single-family tunnel vision.

---

## Family budget-share rules

For each enriched seed, the family budget shares must sum to `1.0`.

Use this simple policy:

* total share on all `high` families:

  * target around `0.50` to `0.60`
* total share on all `medium` families:

  * target around `0.20` to `0.35`
* total share on all `explore_only` families:

  * target at least `0.15`
* `low` families may still get a small share if needed for balancing, but they are last priority

Within a band:

* sort by:

  1. truth-winner flag
  2. family strength label
  3. best truth
  4. boundary count
  5. lexicographically smaller family id

This must be deterministic.

---

## Outputs

### 1. `seed_triage_rows.jsonl`

One row per seed in `TRIAGE_REVIEW_SEEDS`.

### 2. `family_priority_rows.jsonl`

One row per family for seeds in `TRIAGE_FAMILY_ENRICHED_SEEDS`.

### 3. `budget_recommendation_rows.jsonl`

One row per seed summarising the family-level budget split for enriched seeds.

Fields:

* `key_seed`
* `primary_family_id`
* `secondary_family_ids`
* `exploration_family_ids`
* `recommended_primary_budget_share`
* `recommended_secondary_budget_share_total`
* `recommended_exploration_budget_share_total`
* `budget_policy_label`
* `budget_reason_codes`

### 4. `triage_summary.json`

Include:

* input bundle dirs
* `review_seed_count`
* `family_enriched_seed_count`
* `seed_priority_band_counts`
* `seed_budget_policy_counts`
* `family_priority_band_counts`
* `seeds_by_priority_band`
* `seeds_by_budget_policy`

### 5. `triage_cases.md`

Human-readable report.

For each seed, include:

#### Header

* seed
* panel
* evidence tier
* current stop verdict
* current family-quality / pattern-strength reads if available

#### Seed triage summary

Show:

* priority band
* budget policy
* recommended seed-level portfolio split
* reason codes

#### Family table for enriched seeds

Columns:

* family
* winner roles
* strength
* best truth
* persistence
* boundary count
* reaches archive
* priority band
* recommended share

#### Short read

Exactly three bullets:

* why the seed is high / medium / low / unclear
* whether family evidence is helping or not
* what the shadow budget recommendation is trying to do

Keep it short.

---

## Main v1 triage decision labels

This is the main point of the study.

Do **not** invent lots of fancy labels.
The important fields are:

* `seed_priority_band`
* `seed_budget_policy_label`
* `family_priority_band`
* `reason_codes`

That is enough for v1.

---

## Determinism requirements

This study must be fully deterministic.

Required rules:

* fixed input bundle paths
* fixed seed contracts
* no auto-discovery of latest bundles
* no dependence on input row order
* deterministic sorting inside seed and family ranking
* no random sampling
* no hidden use of external state

---

## Missing-data handling

### If a required review seed is missing from stop input

* raise a clear error
* do not continue silently

### If a family-enriched seed is missing from any required v1/v2/v3 input

* raise a clear error
* do not silently fall back to stop-only

### If a non-enriched seed has no family-quality data

* this is expected
* set `triage_evidence_tier = "stop_only"`

### If some family metric fields are missing

* keep the family row
* carry null / missing
* degrade the affected label to a weaker or `explore_only` read if needed

Do not silently drop families or seeds.

---

## Test plan

Create:

* `tests/tools/test_no_wli_seed_family_triage_shadow_v1.py`

Minimum tests:

### Seed and input contract

* `test_triage_shadow_v1_review_seed_contract_is_fixed`
* `test_triage_shadow_v1_family_enriched_seed_contract_is_fixed`
* `test_triage_shadow_v1_requires_explicit_input_bundle_files`

### Seed priority rules

* `test_seed_priority_high_for_reference_like_strong_case`
* `test_seed_priority_high_for_accepted_miss_reference_like_case`
* `test_seed_priority_medium_for_pattern_only_but_weak_case`
* `test_seed_priority_low_for_quiet_reject_case`
* `test_seed_priority_unclear_for_inconclusive_family_case`

### Budget policy rules

* `test_budget_policy_focus_with_exploration_for_high_case`
* `test_budget_policy_balanced_portfolio_for_medium_case`
* `test_budget_policy_exploration_heavy_for_unclear_case`
* `test_budget_policy_observe_only_for_low_case`
* `test_seed_level_budget_shares_sum_to_one`

### Family priority rules

* `test_family_priority_high_for_truth_winner_with_strong_or_partial_strength`
* `test_family_priority_medium_for_non_truth_alt_winner`
* `test_family_priority_explore_only_keeps_non_truth_family_alive`
* `test_family_budget_shares_sum_to_one_per_enriched_seed`

### Fallback / evidence tier

* `test_stop_only_seed_gets_seed_triage_row_without_family_outputs`
* `test_family_enriched_seed_requires_family_inputs`

### Determinism

* `test_seed_triage_rows_are_deterministic_under_input_reordering`
* `test_family_priority_rows_are_deterministic_under_input_reordering`

### Markdown smoke

* `test_triage_cases_markdown_includes_all_review_seeds`

This is a real branch and should have a fuller test surface than v2.

---

## Patch order

1. Add the spec and experiment-plan docs.
2. Create the new analysis folder and script skeleton.
3. Add fixed input validation for all four frozen bundles.
4. Add seed-contract validation.
5. Implement stop-side seed-row ingestion.
6. Implement family-quality enrichment ingestion.
7. Implement seed-priority rules.
8. Implement seed-level budget policy rules.
9. Implement family-strength and family-priority rules.
10. Implement family budget-share recommendations.
11. Implement summary and markdown writers.
12. Add tests.
13. Run once against the frozen inputs.
14. Update planning docs only after the first real output exists.

---

## First real output location

Write outputs under:

* `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/<timestamp>__seed_family_triage_shadow_v1/`

Expected files:

* `seed_triage_rows.jsonl`
* `family_priority_rows.jsonl`
* `budget_recommendation_rows.jsonl`
* `triage_summary.json`
* `triage_cases.md`

Keep naming consistent with the existing no-WLI analysis branches.

---

## Success condition

v1 is a success if it does all of these clearly:

* assigns sensible seed priority bands across the 12 review seeds
* gives richer triage on the six family-enriched seeds
* produces budget recommendations that are visibly different for:

  * `1111`
  * `1311`
  * `1411`
  * strong reference wins
  * quiet rejects
* stays shadow-only and non-gating
* gives you a plausible way to choose which seeds and families deserve more time

It does **not** need to be ready to control the solver.

---

## Failure condition

v1 is a failure if:

* the seed-priority bands are too vague to guide anything
* the family-priority rows collapse into one trivial “truth winner always high, everything else low” rule
* the budget policies do not differ meaningfully across the review seeds
* the study ends up restating earlier labels without adding practical prioritisation value

That is still useful.
It would mean this line is not yet mature enough to feed into pipeline triage.

---

## Explicit non-drift rule

This study must not modify:

* `score_stop_shadow_v2`
* `late_family_quality_v1`
* `late_family_quality_v2`
* `late_family_quality_v3`
* any thresholds or bundle semantics from those branches

All four are frozen inputs for this study.

---

## Short dev handoff note

Build `seed_family_triage_shadow_v1` as a frozen-input shadow triage and budget-allocation study on top of:

* `score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2`
* `late_family_quality_v1/20260408T152322Z__late_family_quality_v1`
* `late_family_quality_v2/20260408T154637Z__late_family_quality_v2`
* `late_family_quality_v3/20260408T162219Z__late_family_quality_v3`

Use:

* all 12 review-panel seeds for seed-level rows
* the six family-enriched seeds for family-level rows

Emit:

* one seed triage row per review seed
* one family priority row per family for enriched seeds
* one budget recommendation row per enriched seed
* one summary json
* one short markdown report

Do not mutate stop logic.
Do not widen the seed set.
Do not gate or stop runs.
Do not let any recommendation assign zero exploration budget.

The question is:

**can we turn the current stop and family-quality pack into a useful shadow layer for choosing which seeds and families deserve more budget, without pretending we can stop early yet?**

---

If you want, next I can write the matching `EXPERIMENT_PLAN.md` too.
