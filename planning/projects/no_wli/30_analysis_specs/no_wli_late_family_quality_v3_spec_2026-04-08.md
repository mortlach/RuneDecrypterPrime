# No-WLI late-family-quality v3 spec

Date: 2026-04-08

## Purpose

Build `late_family_quality_v3` as a new **offline-only pattern-plus-strength
reconciliation study**.

v2 was useful, but it was intentionally thin. It showed that:

* `1111` matches a real-win winner-family split pattern exactly
* `1311` and `1411` do not match any reference-win pattern
* accepted wins still span multiple acceptable patterns

That is enough to justify v3.

But v2 also left important things too thin:

* it mostly worked from the frozen **v1 case digest**, not the richer family rows
* it did **not** independently carry family strength into the main read
* it did **not** compute truth-relative gap fields in a first-class way
* it did **not** compute truth-vs-alternative boundary overlap in a first-class way
* it partly relied on inherited `case_shape_label` framing from v1
* its tests were light for the strength of the new claim

So v3 must **include the missing pieces that are actually needed**.

The purpose of v3 is:

**test whether “matches an acceptable pattern” plus “truth-winning family still
looks strong enough” is a better offline discriminator than pattern membership
alone, without pretending this is already a promoted score head.**

---

## Why this is the next move

v1 showed:

* family-level information helps
* but accepted wins still split across different winner families

v2 showed:

* the split patterns themselves are informative
* `1111` is reference-like by pattern
* `1311` and `1411` are not

That means the next question is no longer:

* “does pattern membership help?”

It is:

* “does pattern membership stay useful once we force it to reconcile with the
  actual strength of the truth-winning family and the gap to the alternative
  winners?”

That is the right v3 question.

---

## Study stance

This study is:

* offline only
* deterministic
* based on frozen v1 and v2 bundles
* seed-level, but backed by family-row data
* explanatory and comparative
* still non-promotive

This study is **not**:

* a new stop-rule branch
* a live-policy step
* a replay-score redesign
* a family re-clustering effort
* a new live-seed campaign
* a promoted family-quality head

---

## Recommended code location

Create a new analysis branch:

* `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/`

with:

* `SPEC.md`
* `EXPERIMENT_PLAN.md`
* `extract_late_family_quality_v3.py`

Add tests in:

* `tests/tools/test_no_wli_late_family_quality_v3.py`

Keep v3 separate from:

* `score_stop_shadow_v2`
* `late_family_quality_v1`
* `late_family_quality_v2`

v3 should consume frozen outputs, not import evolving helpers from those
branches.

---

## Frozen input contract

### Required frozen input bundles

#### v1 bundle

Use:

```python
INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v1/20260408T152322Z__late_family_quality_v1"
)
```

Required v1 files:

* `family_quality_rows.jsonl`
* `family_quality_case_digest.jsonl`
* `family_quality_summary.json`

#### v2 bundle

Use:

```python
INPUT_LATE_FAMILY_QUALITY_V2_BUNDLE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v2/20260408T154637Z__late_family_quality_v2"
)
```

Required v2 files:

* `seed_agreement_rows.jsonl`
* `winner_pairwise_rows.jsonl`
* `agreement_summary.json`

### Important rule

Do **not** auto-discover “latest” bundles.

Reason:

* v3 must be reviewable and deterministic
* we do not want input drift
* we want the exact relationship between v1, v2, and v3 to stay explicit

---

## Frozen seed contract

Use exactly the same six seeds.

### Discriminator trio

* `1111`
* `1311`
* `1411`

### Reference wins

* `411`
* `611`
* `1011`

### Constants

```python
LATE_FAMILY_QUALITY_V3_DISCRIMINATOR_SEEDS = (1111, 1311, 1411)
LATE_FAMILY_QUALITY_V3_REFERENCE_WIN_SEEDS = (411, 611, 1011)
LATE_FAMILY_QUALITY_V3_STUDY_SEEDS = (
    1111, 1311, 1411,
    411, 611, 1011,
)
```

Lock these in tests.

Do not widen the set in v3.

---

## Main questions

1. Does `1111` remain reference-like once we require the truth-winning family to
   also look strong enough?

2. Does `1311` remain suspicious once we compare its trust-winning family
   directly against the truth-winning family on:

   * best truth
   * persistence
   * boundary overlap
   * archive reach
   * family role

3. Does `1411` remain suspicious once we compare its archive-winning family
   directly against the truth-winning family on the same family-strength axes?

4. Which acceptable patterns on the win side are only acceptable because the
   truth-winning family is still strong?

5. Can we define one or two **combined offline reads** that are stronger than
   v2 pattern membership alone, but still not over-promoted?

---

## Non-goals

Do not do any of these in v3:

* no stop-rule mutation
* no threshold changes anywhere
* no replay-score changes
* no family re-clustering
* no new seed additions
* no live seeds
* no promoted score head
* no attempt to collapse all wins into one universal pattern
* no use of v1 `case_shape_label` as a decision input

That last point matters.
v3 may carry earlier labels as context, but it must derive its main read from
its own fields.

---

## What v3 must include that v2 left too thin

This section is deliberate.
It is here to stop silent dropping of necessary work.

### v2 was useful, but v3 must add all of these

1. **Use the family rows**

   * v2 mostly worked from `family_quality_case_digest.jsonl`
   * v3 must read and use `family_quality_rows.jsonl` directly

2. **Truth-relative gap fields**

   * compare each alternative winner directly against the truth winner on:

     * best truth
     * persistence count
     * boundary count
     * archive reach

3. **Boundary overlap**

   * compute truth-vs-alternative boundary overlap explicitly
   * do not leave this as future work again

4. **Truth-family strength**

   * compute a first-class truth-winner strength label
   * do not leave v3 as pattern-only

5. **Alternative-family strength**

   * same for trust / archive / full uplift / persistence winners

6. **Independence from inherited v1 labels**

   * v3 may carry `case_shape_label` and v2 labels as annotations
   * but the main v3 read must not depend on them

7. **A stronger test surface**

   * v2 only had 8 tests
   * v3 must have a fuller synthetic test set covering the new logic

These are required, not optional.

---

## Inputs to read

### From `family_quality_rows.jsonl` (v1)

Read these fields:

#### Identity

* `artifact_path`
* `run_id`
* `key_seed`
* `study_role`
* `target_panel_name`
* `target_panel_role`
* `family_view_id`
* `family_id`

#### Family coverage / role

* `member_count`
* `boundaries_seen`
* `boundary_count`
* `has_phasec_start`
* `has_stage35_seed`
* `has_stage35_archive`
* `family_role_label`

#### Family peaks

* `best_truth`
* `best_trust`
* `best_archive_uplift`
* `best_full_uplift`
* `best_xent`

#### Persistence / archive reach

* `family_persistence_count`
* `family_persistence_boundaries`
* `family_reaches_archive`

#### Trend labels

* `truth_trend_label`
* `trust_trend_label`
* `archive_uplift_trend_label`
* `full_uplift_trend_label`

### From `family_quality_case_digest.jsonl` (v1)

Read these fields:

* `key_seed`

* `study_role`

* `target_panel_name`

* `run_type`

* `would_dump`

* `would_stop`

* `shadow_rule_id`

* `case_shape_label`

* `truth_winner_family_id`

* `trust_winner_family_id`

* `archive_uplift_winner_family_id`

* `full_uplift_winner_family_id`

* `persistence_winner_family_id`

### From `seed_agreement_rows.jsonl` (v2)

Read these as annotations / cross-checks:

* `winner_pattern_key`
* `pattern_bucket_label`
* `unique_winner_family_count`
* `truth_agreement_count`

Do **not** use these as the sole basis of the main v3 decision label.

### From `winner_pairwise_rows.jsonl` (v2)

These are optional cross-check scaffolding only.
Do not make them the source of truth if the same comparison can be derived more
cleanly from v1 family rows.

---

## Unit of analysis

The main unit of analysis is:

**one seed**

But unlike v2, every seed-level row must be backed by:

* the truth-winning family row
* the trust-winning family row
* the archive-winning family row
* the full-uplift-winning family row
* the persistence-winning family row

This is a seed-level study with family-level support data.

---

## Derived family-strength fields

For the truth-winning family, carry:

* `truth_winner_family_id`
* `truth_winner_best_truth`
* `truth_winner_best_trust`
* `truth_winner_best_archive_uplift`
* `truth_winner_best_full_uplift`
* `truth_winner_boundary_count`
* `truth_winner_boundaries_seen`
* `truth_winner_family_persistence_count`
* `truth_winner_family_reaches_archive`
* `truth_winner_family_role_label`
* `truth_winner_truth_trend_label`
* `truth_winner_trust_trend_label`
* `truth_winner_archive_uplift_trend_label`
* `truth_winner_full_uplift_trend_label`

Repeat the same pattern for:

* `trust_winner_*`
* `archive_winner_*`
* `full_uplift_winner_*`
* `persistence_winner_*`

Use consistent names.

---

## Gap fields relative to the truth winner

For each alternative winner, compute:

### Truth gap

* `truth_minus_trust_winner_best_truth`
* `truth_minus_archive_winner_best_truth`
* `truth_minus_full_uplift_winner_best_truth`
* `truth_minus_persistence_winner_best_truth`

### Persistence gap

* `truth_minus_trust_winner_persistence_count`
* `truth_minus_archive_winner_persistence_count`
* `truth_minus_full_uplift_winner_persistence_count`
* `truth_minus_persistence_winner_persistence_count`

### Boundary-count gap

* `truth_minus_trust_winner_boundary_count`
* `truth_minus_archive_winner_boundary_count`
* `truth_minus_full_uplift_winner_boundary_count`
* `truth_minus_persistence_winner_boundary_count`

### Archive-reach difference

* `truth_vs_trust_archive_reach_diff`
* `truth_vs_archive_archive_reach_diff`
* `truth_vs_full_uplift_archive_reach_diff`
* `truth_vs_persistence_archive_reach_diff`

Interpretation:

* positive truth gap means the truth winner has better truth
* positive persistence gap means the truth winner persists more
* positive boundary gap means the truth winner spans more boundaries
* archive reach diff should be an integer comparison

These are required.

---

## Boundary-overlap fields

For each truth-vs-alternative comparison, compute:

* `truth_vs_trust_boundary_overlap_count`
* `truth_vs_archive_boundary_overlap_count`
* `truth_vs_full_uplift_boundary_overlap_count`
* `truth_vs_persistence_boundary_overlap_count`

And labels:

* `truth_vs_trust_boundary_overlap_label`
* `truth_vs_archive_boundary_overlap_label`
* `truth_vs_full_uplift_boundary_overlap_label`
* `truth_vs_persistence_boundary_overlap_label`

Allowed overlap labels:

* `identical`
* `partial`
* `none`

Rule:

* identical if overlap count equals both families’ boundary counts
* partial if overlap count > 0 but not identical
* none if overlap count == 0

This must be implemented in v3, not left as future scaffolding.

---

## Strength labels

### Truth-winner strength label

Define:

* `truth_winner_strength_label`

Allowed values:

* `strong`
* `partial`
* `weak`

Rule:

* `strong` if `family_persistence_count >= 2` and `family_reaches_archive == 1`
* `partial` if exactly one of those is true
* `weak` otherwise

### Alternative-winner strength labels

Also define:

* `trust_winner_strength_label`
* `archive_winner_strength_label`
* `full_uplift_winner_strength_label`
* `persistence_winner_strength_label`

using the same rule.

These labels must be first-class v3 fields.

---

## Pattern and split fields

Carry forward from v2:

* `winner_pattern_key`
* `unique_winner_family_count`
* `truth_agreement_count`

Also compute:

* `split_pattern_label`

Allowed values:

* `all_agree`
* `truth_trust_split`
* `truth_archive_split`
* `truth_full_uplift_split`
* `truth_persistence_split`
* `multi_split`
* `inconclusive`

Rule:

* `all_agree` if all winner families are the same
* named split if exactly one alternative differs
* `multi_split` if more than one alternative differs
* `inconclusive` if required data is missing

Keep this deterministic and blunt.

---

## Main v3 decision labels

This is the main new output of v3.

Define:

* `pattern_strength_read_label`

Allowed values:

* `reference_like_strong`
* `reference_like_partial`
* `accepted_miss_reference_like`
* `trust_false_fire_suspicious`
* `archive_false_fire_suspicious`
* `pattern_only_reference_like_but_strength_weak`
* `inconclusive`

### Required constants

```python
CLEAR_TRUTH_GAP = 0.10
CLEAR_PERSISTENCE_GAP = 1
```

These are descriptive thresholds for v3 only.
They are **not** promotion thresholds.

### Rule logic

#### `accepted_miss_reference_like`

Use if all are true:

* `key_seed == 1111`
* `winner_pattern_key` matches at least one reference-win pattern
* `truth_winner_strength_label` is `strong` or `partial`
* the truth winner is not clearly dominated by the trust or archive winner on truth

Operationally:

* pattern is reference-like
* truth winner is not weak
* `truth_minus_trust_winner_best_truth > -CLEAR_TRUTH_GAP`
* `truth_minus_archive_winner_best_truth > -CLEAR_TRUTH_GAP`

#### `trust_false_fire_suspicious`

Use if all are true:

* `key_seed == 1311`
* truth winner and trust winner differ
* `truth_minus_trust_winner_best_truth >= CLEAR_TRUTH_GAP`
* and either:

  * `truth_minus_trust_winner_persistence_count >= CLEAR_PERSISTENCE_GAP`
  * or `truth_vs_trust_boundary_overlap_label == 'none'`
  * or `trust_winner_strength_label == 'weak'`

#### `archive_false_fire_suspicious`

Use if all are true:

* `key_seed == 1411`
* truth winner and archive winner differ
* `truth_minus_archive_winner_best_truth >= CLEAR_TRUTH_GAP`
* and either:

  * `truth_minus_archive_winner_persistence_count >= CLEAR_PERSISTENCE_GAP`
  * or `truth_vs_archive_boundary_overlap_label == 'none'`
  * or `archive_winner_strength_label == 'weak'`

#### `reference_like_strong`

Use for reference wins if:

* the seed is one of `411`, `611`, `1011`
* pattern is reference-like by membership
* `truth_winner_strength_label == 'strong'`

#### `reference_like_partial`

Use for reference wins if:

* pattern is reference-like
* `truth_winner_strength_label == 'partial'`

#### `pattern_only_reference_like_but_strength_weak`

Use if:

* pattern is reference-like
* but `truth_winner_strength_label == 'weak'`

#### `inconclusive`

Use otherwise.

This is intentionally conservative.
Do not overfit it.

---

## Outputs

### 1. `pattern_strength_rows.jsonl`

One row per seed.

This is the main machine-readable output.

It must contain:

* identity
* current stop-harness read
* v1 family-quality read
* v2 pattern fields
* truth-winner strength fields
* alternative-winner strength fields
* gap fields
* boundary-overlap fields
* `split_pattern_label`
* `pattern_strength_read_label`

### 2. `truth_relative_pair_rows.jsonl`

One row per seed and per truth-vs-alternative pair:

* `truth_vs_trust`
* `truth_vs_archive`
* `truth_vs_full_uplift`
* `truth_vs_persistence`

Fields:

* `key_seed`
* `pair_name`
* `truth_family_id`
* `alt_family_id`
* `same_family`
* `truth_winner_strength_label`
* `alt_winner_strength_label`
* `truth_minus_alt_best_truth`
* `truth_minus_alt_persistence_count`
* `truth_minus_alt_boundary_count`
* `archive_reach_diff`
* `boundary_overlap_count`
* `boundary_overlap_label`
* `pair_read_label`

Allowed `pair_read_label` values:

* `same_family`
* `truth_advantaged`
* `alt_not_clearly_weaker`
* `weak_alt_but_same_pattern`
* `inconclusive`

This file is required.
Do not skip it.

### 3. `pattern_strength_summary.json`

Include:

* `input_v1_bundle_dir`
* `input_v2_bundle_dir`
* `study_seed_count`
* `study_role_counts`
* `split_pattern_counts`
* `truth_winner_strength_counts`
* `pattern_strength_read_counts`
* `seeds_by_pattern_strength_read`

### 4. `pattern_strength_cases.md`

Human-readable report.

For each seed, include:

#### Header

* seed
* study role
* current stop-harness verdict
* v1 family-quality read
* v2 winner-pattern key

#### Winner-family table

Columns:

* winner type
* family id
* strength
* best value
* best truth
* persistence
* boundary count
* reaches archive
* role
* trend
* boundaries seen

Rows:

* truth
* trust
* archive uplift
* full uplift
* persistence

For `best value`, use the metric-appropriate value:

* truth -> `best_truth`
* trust -> `best_trust`
* archive uplift -> `best_archive_uplift`
* full uplift -> `best_full_uplift`
* persistence -> `family_persistence_count`

#### Truth-relative comparison table

Rows:

* truth vs trust
* truth vs archive
* truth vs full uplift
* truth vs persistence

Columns:

* same family
* truth gap
* persistence gap
* boundary gap
* archive reach diff
* overlap
* read

#### Short read

Exactly three bullets:

* whether the seed is only pattern-reference-like or also strength-reference-like
* whether the truth winner still looks strong enough
* the simplest present interpretation

Keep this short.

---

## Recommended script structure

Main script:

* `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/extract_late_family_quality_v3.py`

Recommended helpers:

* `_read_family_quality_rows(...)`
* `_read_family_quality_case_digest(...)`
* `_read_seed_agreement_rows(...)`
* `_select_study_seed_rows(...)`
* `_index_family_rows_by_seed_and_family(...)`
* `_label_family_strength(...)`
* `_compute_truth_relative_pair(...)`
* `_label_pair_read(...)`
* `_label_split_pattern(...)`
* `_label_pattern_strength_read(...)`
* `_build_pattern_strength_rows(...)`
* `_build_truth_relative_pair_rows(...)`
* `_write_cases_markdown(...)`
* `_write_summary_json(...)`

Keep helpers small and pure.

Do not import internal v1 or v2 helpers.

---

## Determinism requirements

This study must be fully deterministic.

Required rules:

* fixed input bundle paths
* fixed seed set
* no auto-discovery of latest bundles
* no dependence on input row order
* fixed tie-break behaviour
* no random sampling
* no hidden dependence on inherited labels for the main decision field

---

## Missing-data handling

If a required seed is missing from either v1 or v2 inputs:

* raise a clear error
* do not continue silently

If a winner family id from the case digest cannot be found in the v1 family rows:

* raise a clear error

If some family fields are missing:

* keep the seed
* carry null / missing fields
* let the final label become `inconclusive` if needed

Do not silently drop seeds or family rows.

---

## Test plan

Create:

* `tests/tools/test_no_wli_late_family_quality_v3.py`

Minimum tests:

### Seed and input contract

* `test_late_family_quality_v3_seed_contract_is_fixed`
* `test_late_family_quality_v3_requires_explicit_input_bundle_files`

### Strength labels

* `test_label_family_strength_strong`
* `test_label_family_strength_partial`
* `test_label_family_strength_weak`

### Boundary overlap

* `test_boundary_overlap_label_identical`
* `test_boundary_overlap_label_partial`
* `test_boundary_overlap_label_none`

### Pair-read labels

* `test_label_pair_read_truth_advantaged`
* `test_label_pair_read_same_family`
* `test_label_pair_read_inconclusive`

### Main decision labels

* `test_pattern_strength_read_marks_1111_style_case_as_accepted_miss_reference_like`
* `test_pattern_strength_read_marks_1311_style_case_as_trust_false_fire_suspicious`
* `test_pattern_strength_read_marks_1411_style_case_as_archive_false_fire_suspicious`
* `test_pattern_strength_read_handles_reference_like_strong_case`
* `test_pattern_strength_read_handles_pattern_only_but_weak_case`

### Builder behaviour

* `test_build_pattern_strength_rows_carries_v1_and_v2_reads`
* `test_build_truth_relative_pair_rows_writes_expected_pairs`
* `test_pattern_strength_rows_are_deterministic_under_input_reordering`

### Markdown smoke

* `test_pattern_strength_cases_markdown_includes_all_study_seeds`

This should be a noticeably stronger test surface than v2.

---

## Patch order

1. Add the v3 spec and experiment-plan docs.
2. Create the new analysis folder and script skeleton.
3. Add fixed input validation for both v1 and v2 bundles.
4. Implement family-row indexing from v1 family rows.
5. Implement family-strength labels.
6. Implement truth-relative gap and boundary-overlap helpers.
7. Implement pair-read labels.
8. Implement split-pattern labels.
9. Implement main pattern-strength read labels.
10. Implement seed rows and truth-relative pair rows.
11. Add markdown writer and summary writer.
12. Add tests.
13. Run once against the frozen v1 and v2 bundles.
14. Update planning docs only after the first real output exists.

---

## First real output location

Write outputs under:

* `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/<timestamp>__late_family_quality_v3/`

Expected files:

* `pattern_strength_rows.jsonl`
* `truth_relative_pair_rows.jsonl`
* `pattern_strength_summary.json`
* `pattern_strength_cases.md`

Keep naming consistent with the existing no-WLI analysis branches.

---

## Success condition

v3 is a success if it gives at least one clearly stronger read than v2 alone.

Examples:

* `1111` is not just pattern-reference-like, but also strength-compatible with the win side
* `1311` and `1411` are not just pattern mismatches, but clearly truth-disadvantaged or weak by family strength
* the combined read is sharper than pattern membership alone, while still staying offline and non-promotive

It does **not** need to justify a promoted head.

---

## Failure condition

v3 is a failure if:

* the combined pattern-plus-strength read adds little or nothing beyond v2
* the new labels are too brittle to trust
* the study still depends too heavily on inherited v1 labels
* the truth-family strength view does not sharpen the distinction between `1111` and the false-fire cases

That is still useful.
It would mean this line is approaching its limit.

---

## Explicit non-drift rule

This study must not modify:

* `score_stop_shadow_v2`
* `late_family_quality_v1`
* `late_family_quality_v2`
* their thresholds
* their output semantics
* their seed contracts

All three are frozen inputs or references for v3.

