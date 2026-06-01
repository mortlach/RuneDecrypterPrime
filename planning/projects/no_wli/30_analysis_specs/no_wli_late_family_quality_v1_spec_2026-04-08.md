# No-WLI late-family-quality v1 spec

Date: 2026-04-08

## Purpose

Build a new **offline-only family-level analysis** on top of the now-frozen
`score_stop_shadow_v2` bundle.

The purpose is to test whether **family-level late behaviour** can separate:

* the accepted miss shape: `1111`
* the trust false-fire shape: `1311`
* the archive false-fire shape: `1411`

using these accepted wins as reference families:

* `411`
* `611`
* `1011`

This is **not** a new stop-rule branch.
This is **not** a live policy change.
This is a bounded study intended to answer whether family-level signals are
more useful than the current row-level trust / uplift rules.

---

## Why this is the next move

`score_stop_shadow_v2` has now crossed the useful threshold.

It is no longer mainly telling us:

* “the harness is under-instrumented”

It is now telling us:

* “the current late-state model is incomplete”

That is a real milestone.

The stop harness now already shows three important facts:

* `1111` is an accepted win that still sits outside the current trust-led and
  archive-rescue shapes
* `1311` is a genuine trust false fire
* `1411` is a genuine archive-uplift false fire

So the next useful question is no longer:

* “can we add one more stop rule?”

It is:

* “does family-level late behaviour contain a clearer discriminator than the
  current row-level trust / uplift view?”

That is what this study is for.

---

## Study stance

This study is:

* offline only
* downstream of a frozen `score_stop_shadow_v2` input bundle
* explanatory and comparative
* family-level rather than row-threshold-level

This study is **not**:

* a rewrite of `score_stop_shadow_v2`
* a mutation of stop logic
* a live heuristic promotion
* a replay-score redesign
* a global atlas or connectivity project
* a new live-seed campaign

---

## Recommended code location

Create a new analysis branch:

* `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/`

with:

* `SPEC.md`
* `EXPERIMENT_PLAN.md`
* `extract_late_family_quality_v1.py`

Add tests in:

* `tests/tools/test_no_wli_late_family_quality_v1.py`

Keep this separate from `score_stop_shadow_v2`.
Do not grow the stop harness into this study.

---

## Frozen input contract

### Input source

This study reads from one **explicit frozen** `score_stop_shadow_v2` output
bundle.

Use a hard-coded path constant near the top of the script:

```python
INPUT_SCORE_STOP_BUNDLE_DIR = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "score_stop_shadow_v2/20260408T041415Z__score_stop_shadow_v2"
)
```

Required input files:

* `row_scores.jsonl`
* `run_shadow_summary.jsonl`
* `case_explanations.jsonl`

Optional input file:

* `threshold_matrix_rows.jsonl`

### Important rule

Do **not** auto-discover “latest” bundles in v1.

Reason:

* we want deterministic and reviewable behaviour
* we do not want the study to drift each time a new stop bundle appears

If the input bundle changes later, that should be an explicit edit and a new
study run.

---

## Frozen seed contract

### Discriminator trio

Ordered seed contract:

* `1111`
* `1311`
* `1411`

Role:

* accepted miss
* trust false fire
* archive false fire

### Reference wins

Ordered seed contract:

* `411`
* `611`
* `1011`

Role:

* accepted win comparators

### Optional reject comparator

Not in v1 by default:

* `1511`

Reason:

* it may be useful later as a quiet reject comparator
* but v1 should stay tight and focused

### Study seed list

The study must use exactly:

```python
FAMILY_QUALITY_DISCRIMINATOR_SEEDS = (1111, 1311, 1411)
FAMILY_QUALITY_REFERENCE_WIN_SEEDS = (411, 611, 1011)
FAMILY_QUALITY_STUDY_SEEDS = (
    1111, 1311, 1411,
    411, 611, 1011,
)
```

Lock these in tests.

---

## Unit of analysis

The unit of analysis is:

**one family within one run**

A family is identified using the existing frozen fields already present in
`row_scores.jsonl`:

* `artifact_path`
* `run_id`
* `key_seed`
* `family_view_id`
* `family_id`

Do **not** recluster families in v1.
Do **not** redefine family ids in v1.
Do **not** merge families across runs in v1.

This study is about extracting family-level behaviour from the current frozen
family contract, not replacing it.

---

## Boundaries to compare

Use this fixed late-boundary order:

```python
LATE_BOUNDARY_ORDER = {
    "phaseC_start": 1,
    "stage35_seed": 2,
    "stage35_archive": 3,
}
```

### Inclusion rule

A family does **not** need all three boundaries to be included.

Reason:

* dropping partial families silently would hide exactly the failure modes we
  want to inspect

Instead, every family row must carry explicit presence flags:

* `has_phasec_start`
* `has_stage35_seed`
* `has_stage35_archive`

and explicit boundary lists:

* `boundaries_seen`
* `boundary_count`

---

## Main questions the study must answer

1. Does `1111` contain a family that looks good at the family level even though
   the current row-level trust / uplift logic still misses it?

2. Does `1311` look weaker at the family level than its trust-led firing row
   suggests?

3. Does `1411` show positive archive uplift on a family that is still poor by
   truth when viewed across late boundaries?

4. Do the accepted reference wins `411`, `611`, and `1011` share any
   family-level traits that the three problem cases lack?

5. Do truth, trust, and uplift point at the same family within a run, or do
   they split across different families?

That last question is especially important.

---

## Non-goals

Do not do any of these in v1:

* no new stop-rule branch
* no threshold changes
* no replay-score changes
* no family re-clustering
* no atlas rewrites
* no selector-policy changes
* no live seeds
* no broad “family quality framework”
* no attempt to generalise to all seeds

This is a targeted study on a fixed six-seed set.

---

## Inputs to read from `row_scores.jsonl`

Use these frozen fields as the base data contract:

### Identity / provenance

* `artifact_path`
* `run_id`
* `key_seed`
* `run_type`
* `target_panel_name`
* `target_panel_role`
* `family_view_id`
* `family_id`
* `stage_boundary`
* `candidate_hash`
* `source`
* `lane`
* `selected`
* `eligible`
* `distance_to_anchor`

### Truth / score

* `replay_truth_match`
* `replay_full_score`
* `replay_search_score`
* `replay_word_ngram_trust_score`
* `replay_word_ngram_report_xent`

### Existing late-family signals

* `shadow_late_family_persistence_count`
* `shadow_late_family_persistence_boundaries`
* `shadow_late_family_reaches_archive`
* `shadow_late_family_search_uplift`
* `shadow_late_family_full_uplift`
* `shadow_late_family_phasec_search_score`
* `shadow_late_family_phasec_full_score`
* `shadow_late_family_current_boundary_best_search_score`
* `shadow_late_family_current_boundary_best_full_score`

### Existing row diagnostics

* `shadow_high_score_would_dump`
* `shadow_high_score_rule_id`
* `shadow_nearest_pass_rule_id`
* `shadow_nearest_pass_blocker`

Do not recompute these if they already exist in the frozen input bundle.

---

## Derived family metrics

For each family, compute the following.

### Family identity and coverage

* `artifact_path`
* `run_id`
* `key_seed`
* `target_panel_name`
* `target_panel_role`
* `study_role` (`discriminator` or `reference`)
* `family_view_id`
* `family_id`
* `member_count`
* `boundaries_seen`
* `boundary_count`
* `has_phasec_start`
* `has_stage35_seed`
* `has_stage35_archive`

### Family role / shape

* `anchor_row_count`
* `challenger_row_count`
* `blank_lane_row_count`
* `min_distance_to_anchor`
* `max_distance_to_anchor`
* `family_role_label`

`family_role_label` values:

* `anchor_like`
* `challenger_like`
* `mixed`
* `unknown`

Rule:

* `anchor_like` if anchor rows > 0 and challenger rows == 0
* `challenger_like` if challenger rows > 0 and anchor rows == 0
* `mixed` if both anchor and challenger rows are present
* `unknown` otherwise

### Overall family peaks

* `best_truth`

* `best_truth_candidate_hash`

* `best_truth_stage_boundary`

* `best_truth_boundary_rank`

* `best_trust`

* `best_trust_candidate_hash`

* `best_trust_stage_boundary`

* `best_trust_boundary_rank`

* `best_archive_uplift`

* `best_archive_uplift_candidate_hash`

* `best_archive_uplift_stage_boundary`

* `best_archive_uplift_boundary_rank`

* `best_full_uplift`

* `best_full_uplift_candidate_hash`

* `best_full_uplift_stage_boundary`

* `best_full_uplift_boundary_rank`

* `best_xent`

* `best_xent_candidate_hash`

* `best_xent_stage_boundary`

### Boundary-specific peaks

For each of the three late boundaries, compute:

* `<boundary>_best_truth`
* `<boundary>_best_trust`
* `<boundary>_best_archive_uplift`
* `<boundary>_best_full_uplift`
* `<boundary>_member_count`

Where `<boundary>` is one of:

* `phasec_start`
* `stage35_seed`
* `stage35_archive`

### Persistence and archive reach

* `family_persistence_count`
* `family_persistence_boundaries`
* `family_reaches_archive`

Use the frozen row fields if present.
Do not infer these from scratch differently in v1.

### Trend labels

For each of these metrics:

* truth
* trust
* archive uplift
* full uplift

compute a trend label across observed late boundaries:

* `improves`
* `degrades`
* `flat`
* `mixed`
* `insufficient_data`

Use boundary-specific best values in late-boundary order.

Rule:

* fewer than two observed finite values → `insufficient_data`
* all step deltas > `TREND_EPS` → `improves`
* all step deltas < `-TREND_EPS` → `degrades`
* all absolute deltas <= `TREND_EPS` → `flat`
* otherwise → `mixed`

Set:

```python
TREND_EPS = 1e-9
```

Deterministic and simple.

---

## Deterministic winner selection

Within a seed, the study must identify these winning families:

* `truth_winner_family_id`
* `trust_winner_family_id`
* `archive_uplift_winner_family_id`
* `full_uplift_winner_family_id`
* `persistence_winner_family_id`

### Selection rule

For each metric:

1. highest metric value
2. larger `boundary_count`
3. larger `member_count`
4. lexicographically smaller `family_id`

Do not rely on input row order.

Use one pure helper for this, with tests.

---

## Family agreement signals

For each seed, compute:

* `truth_equals_trust_family`
* `truth_equals_archive_uplift_family`
* `truth_equals_full_uplift_family`
* `truth_equals_persistence_family`
* `trust_equals_archive_uplift_family`

Also compute:

* `winner_family_agreement_label`

Allowed values:

* `all_agree`
* `truth_trust_agree_only`
* `truth_archive_agree_only`
* `truth_only`
* `split`
* `insufficient_data`

This is one of the main outputs of the study.

---

## Study outputs

### 1. `family_quality_rows.jsonl`

One row per `(artifact_path, family_id)` for all study seeds.

This is the main machine-readable output.

### 2. `family_quality_case_digest.jsonl`

One row per seed, comparing the winner families and the most important family
signals.

Fields should include:

* identity:

  * `key_seed`
  * `study_role`
  * `target_panel_name`
  * `run_type`

* current stop-harness verdict:

  * `would_dump`
  * `would_stop`
  * `shadow_rule_id`
  * `case_shape_label` if available from `case_explanations.jsonl`

* winner families:

  * `truth_winner_family_id`
  * `trust_winner_family_id`
  * `archive_uplift_winner_family_id`
  * `full_uplift_winner_family_id`
  * `persistence_winner_family_id`

* winner-family agreement:

  * `winner_family_agreement_label`
  * `truth_equals_trust_family`
  * `truth_equals_archive_uplift_family`
  * `truth_equals_persistence_family`

* key family traits:

  * `truth_winner_best_truth`

  * `truth_winner_best_trust`

  * `truth_winner_family_persistence_count`

  * `truth_winner_family_role_label`

  * `truth_winner_truth_trend_label`

  * `truth_winner_trust_trend_label`

  * `truth_winner_archive_uplift_trend_label`

  * same fields for the trust winner if it differs

  * same fields for the archive-uplift winner if it differs

* explanation label:

  * `family_quality_read_label`

Allowed `family_quality_read_label` values:

* `accepted_miss_family_looks_real`
* `trust_false_fire_family_looks_weak`
* `archive_false_fire_family_looks_weak`
* `truth_trust_split`
* `truth_uplift_split`
* `family_level_signal_inconclusive`

Keep this label deterministic and blunt.
It is a study digest, not a theorem.

### 3. `family_quality_summary.json`

Include:

* `input_bundle_dir`
* `study_seed_count`
* `family_row_count`
* `study_role_counts`
* `winner_family_agreement_counts`
* `family_quality_read_counts`
* `seeds_by_read_label`

### 4. `family_quality_cases.md`

Human-readable output.

For each seed, include:

#### Header

* seed
* study role
* current stop-harness verdict
* current stop-harness case label if available

#### Winner-family table

Columns:

* metric
* family id
* best value
* role label
* persistence count
* boundaries seen
* trend label

Rows:

* truth
* trust
* archive uplift
* full uplift
* persistence

#### Short read

Exactly three bullets:

* whether truth / trust / uplift agree or split across families
* whether the truth-winning family looks more like a real late family or a weak one
* the simplest family-level interpretation

Keep it short.

---

## Recommended script structure

Main script:

* `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/extract_late_family_quality_v1.py`

Recommended helper layout:

* `_read_row_scores(...)`
* `_read_run_shadow_summary(...)`
* `_read_case_explanations(...)`
* `_select_study_rows(...)`
* `_build_family_rows(...)`
* `_pick_family_winner_by_metric(...)`
* `_build_family_quality_case_digest(...)`
* `_label_family_quality_read(...)`
* `_write_case_markdown(...)`
* `_write_summary_json(...)`

Keep helpers small and pure where possible.

Do not import stop-rule evaluation helpers from `score_stop_shadow_v2`.
This study should consume frozen outputs, not reuse evolving internal logic.

---

## Determinism requirements

This study must be fully deterministic.

### Required rules

* fixed input bundle path
* fixed seed set
* fixed boundary order
* fixed tie-break rules
* no auto-discovery of latest bundle
* no dependence on JSONL row order
* no random sampling
* no time-based output naming inside tests

### Test requirement

Add explicit tests that prove stable selection under ties.

---

## Missing-data handling

Do not silently drop families or seeds because of missing boundaries.

For any missing boundary:

* keep the family
* set the boundary presence flag to `0`
* set boundary-specific values to `null` / missing
* let the trend label become `insufficient_data` if needed

If an entire study seed is missing from the input bundle:

* raise a clear error
* do not continue with a partial study silently

Lock this in tests.

---

## Test plan

Create:

`tests/tools/test_no_wli_late_family_quality_v1.py`

Minimum tests:

### Seed contract

* `test_family_quality_study_seed_contract_is_fixed`

### Input contract

* `test_family_quality_requires_explicit_input_bundle_files`

### Boundary handling

* `test_family_quality_keeps_partial_families_and_sets_missing_boundary_flags`

### Family role label

* `test_family_role_label_anchor_like`
* `test_family_role_label_challenger_like`
* `test_family_role_label_mixed`

### Trend labels

* `test_metric_trend_label_improves`
* `test_metric_trend_label_degrades`
* `test_metric_trend_label_flat`
* `test_metric_trend_label_mixed`
* `test_metric_trend_label_insufficient_data`

### Deterministic family winner selection

* `test_pick_family_winner_by_metric_uses_stable_tiebreaks`

### Agreement labels

* `test_winner_family_agreement_label_all_agree`
* `test_winner_family_agreement_label_split`

### Case digest

* `test_family_quality_case_digest_carries_stop_verdict_and_case_label`
* `test_family_quality_case_digest_detects_truth_trust_split`
* `test_family_quality_case_digest_handles_reference_wins`

### Markdown smoke

* `test_family_quality_cases_markdown_includes_all_study_seeds`

Keep tests focused and synthetic.
Do not depend on the full real bundle in unit tests.

---

## Patch order

1. Add the spec and experiment-plan docs.
2. Create the new analysis folder and script skeleton.
3. Add input validation and fixed seed contract.
4. Implement family-row builder.
5. Implement trend labels and family role labels.
6. Implement deterministic winner-family selectors.
7. Implement case digest and read labels.
8. Add markdown writer and summary writer.
9. Add tests.
10. Run once against the frozen input bundle and save the first real output bundle.
11. Update planning docs only after the first real output exists.

---

## First real output location

Write outputs under:

* `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/<timestamp>__late_family_quality_v1/`

Expected files:

* `family_quality_rows.jsonl`
* `family_quality_case_digest.jsonl`
* `family_quality_summary.json`
* `family_quality_cases.md`

Keep output naming consistent with existing no-WLI analysis branches.

---

## Success condition

v1 is a success if it gives at least one clear family-level read that is more
useful than the current row-level stop explanation.

Examples:

* `1111` truth family looks persistent and coherent even though row-level trust stays weak
* `1311` truth family looks weaker than its trust-winning family suggests
* `1411` archive-uplift winner family still looks poor by family-level truth behaviour

The study does **not** need to solve the whole problem.
It needs to tell us whether family-level late behaviour is worth promoting into
the next offline score head.

---

## Failure condition

v1 is a failure if:

* truth / trust / uplift winner families still do not separate the accepted miss
  from the false-fire cases in any clearer way than the current stop harness
* family-level persistence / trend signals are too noisy or too flat to help
* the study only restates the current stop-harness labels without adding new
  discrimination

That is still useful.
It would tell us not to spend more time on family-level promotion and to look
elsewhere.

---

## Explicit non-drift rule relative to `score_stop_shadow_v2`

This study must not modify:

* `score_stop_shadow_v2` code
* its thresholds
* its panel contracts
* its output semantics

The only allowed change there, if still pending, is the tiny
`shadow_nearest_pass_margin` naming / signedness cleanup.

Otherwise, `score_stop_shadow_v2` should now be treated as a frozen input and
benchmark explanation tool.

---

## Recommended first follow-up after v1

If v1 finds a useful family-level discriminator, the next step should be:

* one new **offline** score head built from that discriminator
* tested against the frozen core and pressure panels
* without any live promotion

If v1 does **not** find a useful discriminator, then do not keep forcing the
family-quality line. Move to a different offline study.

