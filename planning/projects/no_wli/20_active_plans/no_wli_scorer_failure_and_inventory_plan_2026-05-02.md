# No-WLI Scorer Failure, Inventory, and Evaluation Plan

Date: 2026-05-02
Status: proposed active plan
Scope: scorer diagnosis and design support for no-WLI solver development
Primary aim: improve candidate ranking and acceptance before adding more runtime policies

## 1. Executive summary

The current no-WLI work has repeatedly shown the same pattern:

```text
good candidates sometimes exist
then
the solver does not always rank or accept them correctly
then
late rescue can recover some score
then
posthoc review finds that the better candidate was available, but not selected
```

This strongly suggests that the next major improvement should focus on scorer
and reranker quality, not another broad local-rescue runtime branch.

The scorer work should proceed in three stages:

```text
Stage 1:
  Existing scorer inventory

Stage 2:
  Current scorer failure study

Stage 3:
  New scorer / reranker evaluation harness
```

Stages 1 and 2 should be completed before attempting Stage 3.

The reason is simple: before designing a new scorer, we need to know:

```text
what we already built
what the current scorer actually does wrong
which existing components can be reused
which failure modes matter most
```

This plan is deliberately conservative. It avoids creating a new abstraction
layer and fits inside the existing RDP / no-WLI structure.

## 2. Plain-English goal

The main question is:

```text
When the solver already has a better candidate available, why does the current
scorer or acceptance logic sometimes choose the worse candidate?
```

If we can answer that, we can design a better scorer, reranker, or
candidate-admission rule.

The important distinction is:

```text
more seeds may generate more candidates

but a better scorer is needed if the solver cannot recognise the good ones
```

## 3. Three-stage plan

### Stage 1 - Existing scorer inventory

Purpose:

```text
Find out what scorer-related work already exists, what each component does,
and whether it should be reused, hardened, or discarded.
```

This includes current RDP scorer code and older scorer projects, such as
Hamming, span-Hamming, n-gram, word-n-gram, Project Runeberg, ECDF, or
scorer-report work.

Stage 1 answers:

```text
What do we already have?
What problem was each scorer component meant to solve?
Which components are inner-loop scorers?
Which are better suited as final judges or rerankers?
Which old work should not be reinvented?
```

Deliverable:

```text
a scorer component inventory and reuse recommendation
```

### Stage 2 - Current scorer failure study

Purpose:

```text
Use known truth-gap / oracle-gap cases to diagnose why the current scorer
chooses the wrong candidate.
```

Stage 2 answers:

```text
Is the current scorer failing because of local n-gram overfit?
Is it ignoring bad windows?
Is it missing word/span structure?
Is one component weighted too strongly?
Is the good candidate absent, or merely mis-ranked?
```

Deliverable:

```text
a current-scorer failure table and failure-mode summary
```

### Stage 3 - New scorer / reranker evaluation harness

Purpose:

```text
Compare candidate scorer or reranker designs against truth-gap pairs,
corruption ladders, and adversarial false positives.
```

Stage 3 should not be designed in detail until Stages 1 and 2 are complete.

Possible Stage 3 work includes:

```text
truth-gap pairwise scorer evaluation
500-character corruption ladder
Project Runeberg calibration chunks
top-K shadow reranking
gated final judge scorer
anti-motif / worst-window penalties
```

Deliverable:

```text
a report-only scorer/reranker evaluation showing whether any candidate scorer
improves truth-ranking without creating new false positives
```

## 4. What this is not

This branch is not:

```text
a runtime scorer replacement
a new solver policy
a new framework
a new abstraction layer
a training-first machine-learning project
a broad seed sweep
a local-rescue runtime batch
```

No runtime behaviour should change during Stages 1 and 2.

# Stage 1 in detail - Existing scorer inventory

## 5. Stage 1 question

```text
Which scorer components and scoring-related tools already exist, and which are
worth reusing for the no-WLI scorer failure and reranker work?
```

## 6. Stage 1 inputs

Inputs should include current RDP source plus older scorer project source.

Current RDP areas to inspect:

```text
src/rune_decrypter_prime/scoring/
src/rune_decrypter_prime/scoring/language_model/
src/rune_decrypter_prime/scoring/span_hamming/
src/rune_decrypter_prime/scoring/word_ngrams/

tools/benchmarks/periodic_sub_trans/no_wli/
tools/benchmarks/periodic_sub_trans/no_wli/analysis/

tests/
tests/tools/
```

Older project inputs may include source or notes for:

```text
Hamming scorer
span-Hamming scorer
character n-gram scorer
word n-gram scorer
Project Runeberg processing
ECDF / percentile calibration
combined scorer objects
scorer report builders
old scorer comparisons
old notebooks or CSV outputs
```

If old projects are supplied as zips, do not integrate them into the repo
first. Review them as external source material and record what is worth
reusing.

## 7. Stage 1 proposed planning file

```text
planning/projects/no_wli/20_active_plans/
no_wli_scorer_failure_and_inventory_plan_2026-05-02.md
```

The planning file should include:

```text
Question
Suspicion
Main alternative
Mechanism layer
Inputs
Outputs
Decision rule
```

Suggested question:

```text
Which current and historical scorer components are available, what failure
modes do they address, and which should be reused for no-WLI scorer diagnosis?
```

Suggested suspicion:

```text
Useful scorer components already exist, especially around n-grams, span/Hamming
evidence, Project Runeberg corpus processing, ECDF calibration, and scorer
reports. The next scorer branch should reuse and evaluate these rather than
starting from scratch.
```

Suggested main alternative:

```text
The older scorer work is either too specialised, not compatible with the
current RDP scoring path, or lacks tests/evidence, so only the design lessons
should be reused.
```

Mechanism layer:

```text
score calibration / candidate selection
```

## 8. Stage 1 proposed implementation file

Suggested file:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
export_scorer_component_inventory_v1.py
```

This should be a simple inventory/export script. It should not modify solver
behaviour.

The script should inspect known source roots and produce a CSV/JSON summary of
scorer components.

It can be partly manual and partly automatic. For old external projects, it is
acceptable to record manually reviewed entries.

## 9. Stage 1 output folder

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_component_inventory_v1/
```

Expected files:

```text
scorer_component_inventory_rows.csv
scorer_component_inventory_rows.jsonl
scorer_component_inventory_summary.json
scorer_component_inventory_readout.md
```

## 10. Stage 1 row schema

Each inventory row should include:

```text
component_id
component_name
source_project
source_path
component_type
input_type
output_type
needs_plaintext
needs_runes
needs_spaces
needs_word_boundaries
uses_truth_or_oracle
runtime_safe
inner_loop_safe
reranker_safe
final_judge_safe
expected_text_length
known_failure_mode_addressed
known_failure_mode_created
test_file_paths
has_tests
evidence_paths
reuse_recommendation
notes
```

Allowed `component_type` examples:

```text
char_ngram
word_ngram
hamming
span_hamming
ecdf_calibrator
combined_scorer
scorer_report
corpus_builder
normaliser
reranker
diagnostic
```

Allowed `reuse_recommendation` values:

```text
reuse_directly
reuse_as_report_feature
reuse_after_hardening
design_reference_only
discard
unknown_pending_review
```

## 11. Stage 1 summary fields

The summary JSON should include:

```text
component_count
current_rdp_component_count
old_project_component_count

reuse_directly_count
reuse_as_report_feature_count
reuse_after_hardening_count
design_reference_only_count
discard_count
unknown_pending_review_count

inner_loop_safe_count
reranker_safe_count
final_judge_safe_count
runtime_safe_count
uses_truth_or_oracle_count

components_missing_tests_count
components_with_tests_count
```

## 12. Stage 1 readout structure

The readout should be plain English:

```text
# Scorer Component Inventory v1

## Summary

## Components recommended for direct reuse

## Components recommended as report-only features

## Components requiring hardening

## Components that must not be used at runtime

## Missing tests / documentation

## Recommended scorer-failure study inputs
```

## 13. Stage 1 tests

Suggested test file:

```text
tests/tools/test_no_wli_scorer_component_inventory_v1.py
```

Minimum tests:

```text
inventory rows contain required fields
reuse recommendation values are from the allowed set
components marked runtime_safe cannot use truth/oracle fields
components marked inner_loop_safe must have deterministic outputs
summary counts match rows
missing test paths are reported clearly
unknown components are allowed but marked unknown_pending_review
```

These tests do not need to test every scorer. They test the inventory logic and
prevent silent misclassification.

## 14. Stage 1 decision rule

Advance to Stage 2 if:

```text
inventory exists
important current scorer components are listed
older scorer projects are either included or explicitly marked pending
runtime-safe versus report-only components are separated
truth/oracle-using components are clearly marked
```

Hold if:

```text
old scorer projects are not yet available
current scorer components cannot be identified
components using truth/oracle data are not clearly separated
```

Close / defer if:

```text
there is not enough scorer source material to inventory
```

# Stage 2 in detail - Current scorer failure study

## 15. Stage 2 question

```text
Why does the current scorer rank known truth-positive candidates below worse
candidates, and which failure mode is most common?
```

## 16. Stage 2 inputs

Primary inputs:

```text
existing no-WLI truth-gap / oracle-gap rows
candidate rows where current score-selected winner differs from truth-better challenger
current scorer reports, if available
candidate plaintext / rune text where available
candidate hashes and source metadata
stage and run metadata
```

Potential source areas:

```text
tools/benchmarks/periodic_sub_trans/no_wli/phasec_truth_gap_dataset.py
tools/benchmarks/periodic_sub_trans/no_wli/analysis/export_phasec_truth_gap_dataset.py
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/
```

Also include any known Stage 3.5 or Phase-C rows where the candidate was
available but under-ranked.

## 17. Stage 2 proposed implementation file

Suggested file:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
analyse_current_scorer_failure_v1.py
```

This should be report-only.

It must not change scorer code or runtime behaviour.

## 18. Stage 2 output folder

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
current_scorer_failure_v1/
```

Expected files:

```text
current_scorer_failure_rows.csv
current_scorer_failure_rows.jsonl
current_scorer_failure_summary.json
current_scorer_failure_readout.md
```

Optional files:

```text
current_scorer_failure_pair_details/
current_scorer_failure_component_scores.csv
```

## 19. Stage 2 row schema

Each row should represent a comparison pair:

```text
fixture_seed
search_seed
stage
run_id
bundle_path

winner_candidate_hash
challenger_candidate_hash

winner_truth_match
challenger_truth_match
truth_gap_challenger_minus_winner

winner_current_score
challenger_current_score
score_gap_challenger_minus_winner

current_scorer_chose_truth_better
truth_better_candidate_hash

winner_source
winner_source_rank
challenger_source
challenger_source_rank

winner_text_length
challenger_text_length

failure_type
failure_notes

winner_char_lm_score
challenger_char_lm_score

winner_window_mean
challenger_window_mean
winner_window_worst
challenger_window_worst
winner_window_lower_quartile
challenger_window_lower_quartile
winner_window_variance
challenger_window_variance

winner_span_score
challenger_span_score
winner_word_ngram_score
challenger_word_ngram_score

winner_repeated_ngram_rate
challenger_repeated_ngram_rate
winner_low_diversity_penalty
challenger_low_diversity_penalty
```

If some component scores are not available yet, leave them blank and add:

```text
component_scores_available = 0
missing_component_score_reason
```

Do not silently set missing component scores to zero.

## 20. Stage 2 failure-type labels

Suggested labels:

```text
local_ngram_overfit
bad_window_hidden_by_average
missing_word_or_span_signal
component_weighting_failure
calibration_failure
candidate_generation_failure
truth_positive_present_but_under_scored
truth_positive_not_present
short_or_medium_text_length_mismatch
motif_false_positive
unknown
```

Rows may have more than one failure label if needed, but there should be one
primary label.

## 21. Stage 2 summary fields

Summary JSON should include:

```text
pair_count
current_scorer_correct_count
current_scorer_wrong_count
current_scorer_pairwise_accuracy

mean_truth_gap_when_wrong
median_truth_gap_when_wrong
max_truth_gap_when_wrong

mean_score_gap_when_wrong
median_score_gap_when_wrong

failure_type_counts
stage_counts
source_counts

component_scores_available_count
component_scores_missing_count

largest_truth_gap_rows
worst_score_gap_rows
most_instructive_rows
```

## 22. Stage 2 readout structure

The readout should answer:

```text
# Current Scorer Failure Study v1

## Summary

## What the current scorer gets right

## What the current scorer gets wrong

## Largest truth-gap mistakes

## Common failure modes

## Component-level clues

## What existing scorer components may help

## Recommendation for Stage 3 design
```

## 23. Stage 2 important rule: no truth leakage into candidate features

Truth/oracle fields are allowed only for evaluation.

They must not be used as candidate scorer inputs.

The script should keep a clear separation:

```text
evaluation fields:
  truth_match
  truth_gap
  current_scorer_chose_truth_better

candidate feature fields:
  char LM
  window scores
  span / word evidence
  motif / diversity diagnostics
  source / rank / stage metadata
```

## 24. Stage 2 tests

Suggested test file:

```text
tests/tools/test_no_wli_current_scorer_failure_v1.py
```

Minimum tests:

```text
pairwise truth-ranking metric is correct
truth gap is challenger_truth - winner_truth
score gap is challenger_score - winner_score
current_scorer_chose_truth_better is computed correctly
missing truth labels make row invalid / excluded from accuracy
missing component scores are blank or marked missing, not zero
failure_type must be from allowed labels
summary counts match row counts
truth/oracle fields are not included in candidate feature list
```

## 25. Stage 2 decision rule

Advance to Stage 3 if:

```text
there are enough valid truth-gap pairs to diagnose scorer failures
current scorer failure modes are grouped clearly
at least one existing scorer component appears relevant to the dominant failure mode
Stage 3 can be designed around a specific scorer hypothesis
```

Hold if:

```text
truth-gap rows are too few
candidate texts are unavailable
component scores cannot be computed
dominant failure mode is unclear
```

Close / pivot if:

```text
truth-positive candidates are usually absent, not mis-ranked
```

In that case, the next work is candidate generation / supply, not scorer design.

# 26. Stage 3 outline only

Stage 3 should wait until Stages 1 and 2 are complete.

Possible Stage 3 title:

```text
no_wli_scorer_truth_gap_eval_v1
```

Possible Stage 3 question:

```text
Can a report-only scorer/reranker improve truth ranking on known no-WLI
truth-gap pairs without increasing adversarial false positives?
```

Possible Stage 3 components:

```text
Project Runeberg 500-character corpus chunks
controlled corruption ladder
adversarial false-positive candidates
candidate scorer comparison
top-K shadow reranking
```

But Stage 3 should not be implemented until the Stage 1 inventory and Stage 2
failure study say which scorer designs are worth testing.

# 27. Immediate dev instruction

```text
Please start with Stage 1 and Stage 2 only.

Stage 1:
  Inventory existing current and historical scorer components.
  Do not reinvent scorer code.
  Separate runtime-safe, reranker-safe, report-only, and truth/oracle-only components.

Stage 2:
  Diagnose current scorer failures on truth-gap rows.
  Identify whether the current scorer is failing due to n-gram overfit, bad-window hiding,
  missing word/span evidence, weighting, calibration, or candidate absence.

Do not start Stage 3 until these two outputs exist and have been reviewed.
```

# 28. Final status to carry

```text
Main hypothesis:
  score / ranking / acceptance is now the highest-leverage bottleneck

Immediate work:
  scorer inventory + current scorer failure study

Runtime status:
  no change

New scorer status:
  not designed yet

Reason:
  we need to understand existing components and current failure modes before
  building or evaluating a new scorer
```

# 29. Addendum - wider historical pair mining before scorer design

Date: 2026-05-02

The historical partial-text review pack showed that the existing output archive
can support a wider report-only pairwise dataset before any new long solve run.
This directly addresses the overfitting concern: the next scorer evidence should
not depend only on the small Stage 2 truth-gap slice.

Local cross-check output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
historical_pairwise_candidate_mining_v1/
```

The cross-check used this strict definition:

```text
artifact_path present
candidate_hash present
numeric rune/base-29 token_sequence_text present
stored historical score present
stored truth/match ratio present
dedupe by artifact_path + candidate_hash + partial_text_hash
pair only same artifact and same token length
truth_gap >= 0.05
remove stored-score ties
```

Result:

```text
candidate partial-text occurrences in historical inventory: 69,112
labelled artifact rows: 3,704
after artifact/candidate/text dedupe: 2,128
same-artifact same-length pairs after score ties: 2,594

stored-score correct row pairs: 1,970
stored-score misranked row pairs: 624

unique numeric text pairs: 954
unique score-correct numeric text pairs: 704
unique misranked numeric text pairs: 250
unique candidate-hash pairs: 1,006
artifacts represented: 80
fixture/search cells represented: 16

dominant misranked text-pair fraction: 0.0321
dominant misranked candidate-hash-pair fraction: 0.0192
```

Important caveat:

```text
These are stored historical scores from prior artifacts, not a frozen
recomputation through one current scorer version. This is not global current
scorer accuracy.
```

Repetition diagnostic result on unique numeric text pairs:

```text
Misranked:
  lower repeated 3-gram rate favoured truth-better: 164/250 = 0.656
  lower repeated 4-gram rate favoured truth-better: 111/250 = 0.444
  lower repeated 5-gram rate favoured truth-better: 102/250 = 0.408
  lower repeated 6-gram rate favoured truth-better:  39/250 = 0.156

Score-correct controls:
  lower repeated 3-gram rate favoured truth-better: 134/704 = 0.190
  lower repeated 4-gram rate favoured truth-better: 176/704 = 0.250
  lower repeated 5-gram rate favoured truth-better:  94/704 = 0.134
  lower repeated 6-gram rate favoured truth-better:  40/704 = 0.057
```

Interpretation:

```text
Repetition / motif structure is enriched in scorer failures.
It is not a standalone scorer.
The useful motif length varies.
The next scorer work should compare a small family of repetition,
bad-window, and period-lane diagnostics.
```

Updated stage sequence:

```text
S0 - Historical pair mining
  Build pairwise candidate datasets from existing historical numeric partial
  texts. Keep truth labels evaluation-only. Do not change runtime.

S1 - Current-scorer rescore
  Re-score historical numeric partials through one frozen current scorer/report
  stack. Separate stored historical score from current recomputed score.

S2 - Synthetic and key-neighbour calibration
  Generate controlled numeric partial texts from many plaintexts. Include
  random, window, motif, and period-lane damage families. Label synthetic data
  separately.

S3 - Held-out scorer validation
  Split by plaintext / fixture / cipher family, not by row. Report unique-pair
  and fixture/search counts.

S4 - Shadow selector only
  Run any proposed scorer beside current selection and compare what it would
  have selected. Still no runtime promotion.

S5 - Runtime gate
  Only after controls and held-out examples pass.
```

Next concrete evidence question:

```text
When historical candidate partial texts are re-scored with the same current
scorer components, which feature families consistently rank truth-better
numeric rune sequences above truth-worse numeric rune sequences, by unique pair
and by held-out fixture/search split?
```

# 30. Current status and S1 next action

Date: 2026-05-02

Current status:

```text
S0 is complete as a report-only historical pair-mining addendum.

The scorer/ranking direction is better supported across a wider historical
pairwise dataset, but this still does not justify a broad scorer redesign.

The repeated-4gram idea is downgraded from possible scorer feature to one
diagnostic among several. Repetition / motif structure appears enriched in
stored-score failures, but useful motif length varies.
```

Broader pairwise evidence now available:

```text
2,594 same-artifact same-length labelled comparisons
624 stored-score misranks
954 unique numeric text pairs
250 unique misranked numeric text pairs
704 unique score-correct controls
80 artifacts
16 fixture/search cells
```

Important distinction:

```text
S0 = stored historical score versus truth
S1 = recomputed current score versus truth
```

S1 question:

```text
When the same historical numeric rune/base-29 partial texts are rescored
through one frozen current scorer/report stack, do the same broad misranking
patterns remain?
```

Interpretation rule:

```text
If S1 agrees with S0, scorer/ranking failure is more likely to be real and
current.

If S1 disagrees with S0, part of the scorer-failure diagnosis may be an
old-score or version artifact.
```

S1 required outputs:

```text
historical_pairwise_rescore_summary.json
historical_pairwise_rescore_pairs.csv
historical_pairwise_rescore_feature_summary.csv
historical_pairwise_rescore_readout.md
historical_pairwise_rescore_missingness.csv
```

S1 pair-table fields should include:

```text
artifact_path
fixture_id
fixture_seed
search_seed
token_length

winner_candidate_hash
challenger_candidate_hash
winner_token_hash
challenger_token_hash

winner_truth_match
challenger_truth_match
truth_gap

winner_stored_score
challenger_stored_score
stored_score_margin
stored_score_correct

winner_current_score
challenger_current_score
current_score_margin
current_score_correct

stored_current_agree

winner_repeated_3gram_rate
challenger_repeated_3gram_rate
winner_repeated_4gram_rate
challenger_repeated_4gram_rate
winner_repeated_5gram_rate
challenger_repeated_5gram_rate
winner_repeated_6gram_rate
challenger_repeated_6gram_rate

current_feature_fields_present
current_feature_fields_missing
```

Naming rule:

```text
winner means truth-better, not scorer-winner.
```

S1 tests must lock:

```text
numeric token validation rejects values outside 0..28
stored score and recomputed score stay separated
current_score is not copied from stored_score
truth / oracle fields are evaluation labels only
truth / oracle fields do not enter scorer feature inputs
pair construction uses same artifact and same length
truth-gap threshold is applied
score ties are handled explicitly
missing scorer components are reported, not coerced to zero
row counts and unique-pair counts are summarized
dominant-pair frequency and fraction are reported
same input rows produce stable summary counts
```

S1 non-goals:

```text
No new scorer.
No learned weights.
No runtime policy.
No feature selection based on the answer.
No English rendering.
No truth fields in scorer input.
```

Next action:

```text
Build a report-only historical rescoring harness that takes the S0 numeric
rune/base-29 candidate-pair dataset and recomputes all available current
scorer/report features under one frozen scorer stack.

The goal is to separate historical stored-score behavior from current scorer
behavior. Truth/match fields are evaluation labels only and must not enter any
scorer input.
```

Required S1 summary:

```text
row counts
unique numeric text-pair counts
unique candidate-hash-pair counts
fixture/search coverage
dominant-pair fraction
stored-score accuracy
recomputed current-score accuracy
stored/current agreement
score-correct controls
score-misranked cases
feature missingness
repeated 3/4/5/6-gram diagnostics
no runtime behavior change
```

Current honest read:

```text
The evidence now strongly suggests a scorer/ranking bottleneck is present
across more than the original narrow slice. The next required check is whether
the same diagnosis survives recomputing all candidate scores with one frozen
current scorer stack. Only after that should scorer design begin.
```

# 31. S1 result - frozen current scorer rescore

Date: 2026-05-02

S1 output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
historical_pairwise_rescore_v1/
```

Frozen current scorer stack:

```text
label: DEFAULT_SCORER_FULL_2026-05-02
objective: pct.logp.win10
include_char: true
use_word_breaks: false
char_weights: {3: 0.2, 4: 0.8}
wli_weights: {}
impl: torch
```

S1 result:

```text
pair count: 2,594
current-score available pairs: 2,594
current-score missing pairs: 0

stored-score correct: 1,970
stored-score misranked: 624
stored-score pairwise accuracy: 0.7594

current-score correct: 1,992
current-score misranked: 602
current-score pairwise accuracy: 0.7679

stored/current agreement: 2,556 / 2,594 = 0.9854

unique numeric text pairs: 954
unique candidate-hash pairs: 1,006
artifacts represented: 80
fixture/search cells represented: 16

dominant text-pair fraction: 0.0077
dominant candidate-hash-pair fraction: 0.0046
```

Interpretation:

```text
The scorer/ranking failure diagnosis survives recomputing scores with one
frozen current scorer stack.

The current frozen scorer is slightly better than stored historical scores on
this dataset, but the result is very close and agreement is high.

This means the S0 stored-score signal was not mainly an old-score/version
artifact.
```

Repetition diagnostic after current rescore, unique numeric text pairs:

```text
Current-score misranked:
  lower repeated 3-gram rate favoured truth-better: 162/244 = 0.6639
  lower repeated 4-gram rate favoured truth-better: 111/244 = 0.4549
  lower repeated 5-gram rate favoured truth-better:  96/244 = 0.3934
  lower repeated 6-gram rate favoured truth-better:  38/244 = 0.1557

Current-score correct controls:
  lower repeated 3-gram rate favoured truth-better: 136/710 = 0.1915
  lower repeated 4-gram rate favoured truth-better: 176/710 = 0.2479
  lower repeated 5-gram rate favoured truth-better: 100/710 = 0.1408
  lower repeated 6-gram rate favoured truth-better:  41/710 = 0.0577
```

Updated honest read:

```text
The broader scorer/ranking bottleneck is now credible against both stored
historical scores and one frozen current scorer stack.

Repetition / motif diagnostics remain enriched in current-score misranks,
especially repeated 3-gram rate, but they are still diagnostics rather than a
scorer replacement.

The next step should remain report-only: compare diagnostic families on the
current-rescored pairs, including bad-window and period-lane features, before
designing any reranker or runtime selector.
```

# 32. S1b result - scorer component feature audit

Date: 2026-05-02

S1b output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_component_feature_audit_v1/
```

S1b source:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
audit_scorer_component_features_v1.py
```

S1b test:

```text
tests/tools/test_no_wli_scorer_component_feature_audit_v1.py
```

Dataset:

```text
candidate feature rows: 604
pair rows: 2,594
pair feature rows: 134,888
current-score misranked pairs: 602
current-score correct controls: 1,992
unique numeric text pairs: 954
unique candidate-hash pairs: 1,006
artifacts represented: 80
fixture/search cells represented: 16
dominant text-pair fraction: 0.0077
dominant candidate-hash-pair fraction: 0.0046
```

Feature availability:

```text
span-Hamming available candidates: 604 / 604
word-ngram available candidates: 604 / 604
word-ngram active candidates: 333 / 604
word-ngram inactive candidates: 271 / 604
word-ngram inactive reason: min_positions_not_met
```

Top row-occurrence S1b feature results:

```text
word_ngram_trust_score:
  rescues: 28
  breaks: 0
  net: +28

span_raw_score:
  rescues: 346
  breaks: 322
  net: +24

span_quality:
  rescues: 300
  breaks: 370
  net: -70

repeated_3gram_rate:
  rescues: 432
  breaks: 1,432
  net: -1,000
```

Top unique numeric text-pair S1b feature results:

```text
span_raw_score:
  rescues: 142
  breaks: 121
  net: +21

word_ngram_trust_score:
  rescues: 10
  breaks: 0
  net: +10

span_quality:
  rescues: 135
  breaks: 127
  net: +8
```

S1b interpretation:

```text
Existing scorer/report components do contain useful signal, but no single
component is safe to promote.

span_raw_score has broad separation but also many control breaks.

word_ngram_trust_score is much cleaner but small.

Motif/repetition and period-lane features are diagnostic, but direct
single-feature preference breaks too many controls.

This supports continuing to S1 overlap/correlation review before S2 gate
simulation.
```

# 33. S1c result - scorer feature overlap

Date: 2026-05-02

S1c output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_feature_overlap_v1/
```

S1c source:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
analyse_scorer_feature_overlap_v1.py
```

S1c test:

```text
tests/tools/test_no_wli_scorer_feature_overlap_v1.py
```

Purpose:

```text
Measure overlap between S1b single-feature rescues and breaks.
This is still S1 report-only analysis, not a gate simulation and not a runtime
scorer design.
```

Selected overlap findings, row occurrences:

```text
span_raw_score vs word_ngram_trust_score:
  span rescues: 346
  word-trust rescues: 28
  both rescue: 28
  span-only rescue: 318
  word-only rescue: 0
  either rescue: 346

  span breaks: 322
  word-trust breaks: 0
  both break: 0
```

```text
span_raw_score vs repeated_3gram_rate:
  span rescues: 346
  repeated-3gram rescues: 432
  both rescue: 220
  span-only rescue: 126
  repeated-only rescue: 212
  either rescue: 558

  span breaks: 322
  repeated-3gram breaks: 1,432
  both break: 166
```

S1c interpretation:

```text
word_ngram_trust_score rescues are a small subset of span_raw_score rescues in
this row-occurrence analysis. It may be useful as a confidence signal, but it
does not expand rescue coverage beyond span_raw_score here.

repeated_3gram_rate covers many additional misranked pairs beyond span_raw_score,
but it also breaks a very large number of controls. It is not suitable as a
direct preference rule.

The S1 evidence supports S2 diagnostic-family gate simulation, but only with
cautious rules that explicitly measure controls and no-decision behavior.
```

# 34. S1d result - scorer component contract audit

Date: 2026-05-02

S1d output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_component_contract_audit_v1/
```

S1d source:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
audit_scorer_component_contracts_v1.py
```

S1d test:

```text
tests/tools/test_no_wli_scorer_component_contracts_v1.py
```

Purpose:

```text
Verify scorer/report component contracts before Stage 2 gate simulation.
This is report-only and does not change runtime behavior.
```

Length policy:

```text
benchmark minimum token length: 500
token length min/max: 1000 / 1000
below-min pair count: 0
below-min candidate count: 0
```

Artifact context:

```text
direction counts: {"ltr": 2594}
period counts: {"7": 112, "9": 2482}
columns counts: {"1": 156, "3": 2438}
alphabet size counts: {"29": 2594}
order counts: {"col_then_sub": 2594}

hard-coded LTR word call safe for S1: true
```

Cache-key policy:

```text
token-hash-only cache unsafe token count: 0
token-hash-only cache safe for S1: true
```

Span-Hamming contract:

```text
debug_return_intervals: true
len_min: 3
len_max: 14
max_hd: 2
start_stride: 1
max_windows_total: 0
overlap_policy: non_overlapping
max_candidates_per_window: 256
max_intervals_considered_per_start: 4
min_quality_threshold: 1e-9

score direction: higher is better for span_raw / coverage / quality
wordlist source: assets/hamming_raw_1g
wordlist files: 15
```

Word-ngram contract:

```text
sqlite asset:
  output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/
  20260308T024914Z__build_word_ngram_sqlite_asset_phase2_v1/
  word_ngrams_tokenized64_phase2_v1.sqlite

sqlite bytes: 1,051,463,680
orders: [3, 4, 5]
book count: 64
alpha: 0.4
miss_logp: -20.0
min_positions: 12
prefix_total_thresholds: [1, 10, 100]

inactive policy for Stage 2:
  inactive must be no-decision for xent / backoff / miss-rate features

trust-score policy:
  trust_score may be used only as positive confidence;
  inactive is zero confidence, not a normal score
```

Word-ngram active pair states:

```text
both_active: 248
  current-misranked: 126
  controls: 122

winner_only_active: 1096
  current-misranked: 34
  controls: 1062

challenger_only_active: 186
  current-misranked: 180
  controls: 6

neither_active: 1064
  current-misranked: 262
  controls: 802
```

Active-only word feature result:

```text
word trust active-pair rescues: 28
word trust active-pair breaks: 0

word xent both-active rescues: 0
word xent both-active breaks: 0
```

S1d interpretation:

```text
The specific S1b implementation contracts are now explicit enough for review.

The hard-coded LTR word-ngram direction is safe for the S1 dataset because every
audited pair is LTR. This must not be generalized to future non-LTR datasets.

Token-hash-only feature caching is safe for the S1 dataset because each token
hash appears under a single artifact context. Future runs should keep validating
this or move to token_hash + context/config cache keys.

Word-ngram trust is confirmed as a cautious positive-confidence signal, not a
general word-score. Inactive word-ngram xent/backoff/miss-rate values must be
treated as no-decision in Stage 2.

Stage 2 remains on hold until this S1d contract audit is reviewed.
```

## 36. S1e scorer parameter-space scan integration and canary

Date updated: 2026-05-02

Runtime status:

```text
report-only
no solver runtime behaviour change
Stage 2 still on hold
```

S1e source:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scan_scorer_parameter_space_v1.py
```

S1e tests:

```text
tests/tools/test_no_wli_scorer_parameter_space_scan_v1.py
```

S1e output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_parameter_space_scan_v1/
```

Integrated defaults for the first canary:

```text
TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 20
RUN_WORD_NGRAM_ON_TIMING_CHUNKS = False
TIMING_REPEATS_PER_SAMPLE = 1
PROGRESS_EVERY_SAMPLES = 25
```

Reason:

```text
The full scan is a materially new investigation batch. It must be sized from a
same-family canary before widening to all 604 S1 token hashes.
```

Focused tests run:

```text
tests/tools/test_no_wli_scorer_parameter_space_scan_v1.py
tests/tools/test_no_wli_scorer_component_contracts_v1.py
tests/tools/test_no_wli_scorer_component_feature_audit_v1.py

result: 19 passed
```

Canary command:

```text
C:\Python\Python311\python.exe
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scan_scorer_parameter_space_v1.py
```

Canary log:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_parameter_space_scan_v1/scorer_parameter_space_scan_v1_canary.log
```

Canary headline counts:

```text
input_pair_count: 2594
all_required_token_hash_count: 604
selected_token_hash_count: 20
loaded_token_hash_count: 20
token_sample_count: 140
metric pair_count: 4

span_config_count: 10
word_config_count: 5
word chunks enabled: false

span_candidate_feature_row_count: 1400
word_candidate_feature_row_count: 1000
pair_summary_row_count: 500
```

Important interpretation:

```text
This canary is useful for timing, output contract, missingness, and smoke
validation only.

It is not evidence for scorer effectiveness because only 4 pair rows had both
sides inside the 20-token canary selection.
```

Canary runtime:

```text
elapsed wallclock: about 343 seconds
```

Observed full-text span-Hamming mean timings on the canary:

```text
raw_selected_len3_14_hd2_cap512:              ~1702 ms/candidate
raw_selected_len3_14_hd2_cap256__s1b_default: ~1336 ms/candidate
raw_selected_len5_8_hd2_fixture_like:          ~805 ms/candidate
raw_selected_len6_14_hd2_longer:               ~592 ms/candidate
raw_selected_len3_14_hd1:                      ~210 ms/candidate
raw_selected_len4_14_hd1:                      ~163 ms/candidate
raw_selected_len3_14_hd0_exact:                 ~27 ms/candidate
```

Missing policy dictionary assets:

```text
assets/hamming_dictionary_policies/strict/hamming_raw_1g
assets/hamming_dictionary_policies/normal/hamming_raw_1g
assets/hamming_dictionary_policies/broad/hamming_raw_1g
```

Handling:

```text
These configs are explicitly marked unavailable.
Downstream word-ngram configs under those span configs are marked
missing_upstream_span, not treated as available word evidence.
```

Canary projection:

```text
The current 20-token canary took about 343 seconds.
Scaling the same scan shape to all 604 S1 token hashes is roughly 30.2x larger,
or about 2.9 hours, before adding word-ngram timing chunks or extra scorer
families.
```

S1e next decision:

```text
Do not launch the full S1e grid by inertia.

Either:
  1. keep the current grid and run a full 604-token batch with an explicit
     3.5-hour budget and stop condition, or
  2. reduce the grid first, especially by dropping missing policy configs and
     deciding whether cap512 is needed for the first full pass.
```

## 37. S1e full run launch record

Date updated: 2026-05-02

Decision:

```text
Proceed with full S1e run using the same grid as the canary.
```

Approved full-run configuration:

```text
TOKEN_HASH_LIMIT_FOR_DEV_SMOKE = 0
RUN_WORD_NGRAM_ON_TIMING_CHUNKS = False
TIMING_REPEATS_PER_SAMPLE = 1
PROGRESS_EVERY_SAMPLES = 25
```

Budget:

```text
Expected wallclock: about 2.9 hours from same-family canary scaling
Allowed budget: 3.5 hours
```

Stop condition:

```text
Stop/rescope if observed elapsed time exceeds 3.5 hours before completion,
or if the run errors before writing extractable partial output.
```

Run log:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_parameter_space_scan_v1/scorer_parameter_space_scan_v1_full.log
```

Launch status:

```text
started: 2026-05-02T17:19:32-07:00
launcher process pid: 2568
python child pid observed: 30188
```

Visible terminal log mirror:

```text
started after launch because the first launcher was hidden
mirror process pid: 31724
mirror script:
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  scorer_parameter_space_scan_v1/watch_scorer_parameter_space_scan_v1_full_log.ps1
mirror pid file:
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  scorer_parameter_space_scan_v1/scorer_parameter_space_scan_v1_full_log_mirror.pid

The mirror tails:
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  scorer_parameter_space_scan_v1/scorer_parameter_space_scan_v1_full.log
```

Future long-run launch rule:

```text
Long-running investigation runs should open a visible PowerShell terminal that
shows live stdout/stderr or a live log tail for human monitoring, in addition to
writing a repo-relative log file.
```

Completion:

```text
ended: 2026-05-02T19:11:49-07:00
exit_code: 0
elapsed_minutes: 112.27
```

Post-run correction:

```text
The first derived pair summary double-counted no_decision because no_decision
was both a preference bucket and an explicit counter.

Candidate feature rows were not affected.
The summary/flag/active-state files were regenerated from existing candidate
feature rows after patching the counter.

Regression test added:
tests/tools/test_no_wli_scorer_parameter_space_scan_v1.py
```

Post-run tests:

```text
tests/tools/test_no_wli_scorer_parameter_space_scan_v1.py
tests/tools/test_no_wli_scorer_component_contracts_v1.py
tests/tools/test_no_wli_scorer_component_feature_audit_v1.py

result: 20 passed
```

Analysis readout:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_parameter_space_scan_v1/scorer_parameter_space_analysis_readout.md
```

S1e high-level result:

```text
The scan supports report-only Stage 2 gate simulation, but not a direct runtime
scorer replacement.

Best span row-level feature:
  raw_selected_len3_14_hd2_cap512 span_raw
  rescues: 406 / 602
  breaks: 264 / 1992
  net: +142
  unique misranked rescues: 172
  unique control breaks: 112

S1b default span_raw:
  rescues: 346
  breaks: 322
  net: +24
  unique misranked rescues: 142
  unique control breaks: 121

Best cleaner word-trust default:
  raw_selected_len3_14_hd2_cap256__s1b_default
  word_min12_alpha04_miss20__s1b_default
  row rescues: 28
  row breaks: 0
  unique misranked rescues: 10
  unique control breaks: 0
```

S1e cautions:

```text
raw_selected_len3_14_hd2_cap512 is strongest but still cap-truncated:
  mean candidate-cap pruned rate: ~0.285

S1b default is also heavily cap-truncated:
  mean candidate-cap pruned rate: ~0.491

span_interval_count, span_coverage, span_candidate_cap_pruned_rate, and
span_mean_interval_length break too many controls.

word xent/backoff/miss-rate has no useful rescue signal here under both-active
policy.

dictionary policy configs remain unavailable because the policy wordlist assets
are missing.
```

S1e recommendation:

```text
Proceed to Stage 2 only as report-only gate simulation.

Initial Stage 2 gate families should test:
  span_raw / span_quality under small-current-margin conditions
  word_ngram_trust_score as positive-confidence support
  span + word trust conjunctions
  no-decision or downgrade when candidate-cap pressure is high
```

## 38. Stage 2 framing before implementation

Date updated: 2026-05-02

Stage 2 question:

```text
Can we find a conservative checkpoint rule that rescues at least some
current-score failures, breaks very few current-score controls, uses no
truth/oracle inputs, handles cap pressure and inactive word-ngram as
no-decision, and works by unique pair rather than repeated rows?
```

This is not a search for the best scorer.

Stage 2 success criterion:

```text
A candidate report-only checkpoint rule may advance only if it:
  rescues a meaningful number of current-score failures
  breaks very few current-score correct controls
  works by unique numeric text pair, not only row count
  uses no truth/oracle inputs at decision time
  treats high candidate-cap pressure as no-decision or risk
  treats inactive word-ngram as no-decision
  remains deterministic and report-only
```

Stage 2 failure criterion:

```text
Do not advance if apparent gains are mostly repeated rows, high-cap-pressure
artefacts, unavailable policy assets, or broad span settings that damage
controls.
```

Initial Stage 2 rule families:

```text
1. small current-score margin + span_raw/span_quality strongly favours the
   challenger
2. word_ngram_trust_score as positive support only
3. span support + word trust agreement
4. no-decision guardrails when span evidence has high cap pressure
```

Runtime status:

```text
No runtime change.
No learned weights.
No production scorer replacement.
Stage 2 remains report-only until reviewed.
```

## 39. S1f0 fast span-Hamming backend probe

Date updated: 2026-05-02

Before running full S1f span-Hamming calibration, add an optional fast backend
probe:

```text
S1f0 span_hamming_fast_backend_probe_v1
```

Reason:

```text
The current span-Hamming path uses Python LengthSplitIndex lookup plus Python
limited Hamming loops. The older C++ _hamming backend exists, but it is for
WLI/word-segmented Hamming and is not the no-WLI span scanner.
```

Implementation contract:

```text
Keep Python SpanHammingBackend as the reference.
Add an optional C++/pybind span-Hamming backend.
Match Python outputs exactly before using it for calibration.
Expose raw pre-selection intervals only as report-only calibration evidence.
Do not change solver runtime behaviour.
```

Implementation files:

```text
src/rune_decrypter_prime/scoring/span_hamming/FastSpanHamming.h
src/rune_decrypter_prime/scoring/span_hamming/fast_bindings.cpp
src/rune_decrypter_prime/scoring/span_hamming/setup_span_hamming_fast.py
src/rune_decrypter_prime/scoring/span_hamming/fast_backend.py
tests/scoring/span_hamming/test_fast_span_hamming_backend.py
planning/projects/no_wli/20_active_plans/span_hamming_fast_backend_probe_s1f0_2026-05-02.md
```

Build command:

```text
python src/rune_decrypter_prime/scoring/span_hamming/setup_span_hamming_fast.py
```

No CLI arguments are added; config remains hardcoded in source files.

Decision rule:

```text
Use the fast backend for S1f only if parity tests pass for selected intervals,
cap-pressure counts, aggregate stats, and deterministic tie-breaking.
```

S1f0 implementation result:

```text
Build command used:
  py -3.11 src/rune_decrypter_prime/scoring/span_hamming/setup_span_hamming_fast.py

Focused tests:
  py -3.11 -m pytest
    tests/scoring/span_hamming/test_span_hamming_backend.py
    tests/scoring/span_hamming/test_fast_span_hamming_backend.py

Result:
  20 passed

Probe command:
  py -3.11 tools/benchmarks/periodic_sub_trans/no_wli/analysis/
    benchmark_fast_span_hamming_probe_v1.py

Probe output:
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  span_hamming_fast_backend_probe_v1/

Probe result:
  token hashes tested: 20
  config count: 2
  result rows: 40
  parity failed rows: 0
  mean speedup: 3.714x
  median speedup: 3.687x
```

S1f0 status:

```text
Passed as a fast-backend probe.
Python SpanHammingBackend remains the reference.
Fast backend is acceptable for S1f calibration support if parity checks remain
enabled in the calibration script.
```

S1f0b parity/speed tightening:

```text
Initial fast backend speed was lower than desired (~3.7x mean on the small
probe). The C++ implementation was then speed-tuned:
  - packed integer split-bucket keys where slice width permits
  - stamp-array candidate union instead of unordered_set
  - direct continuous length-bin indexing
  - stronger compiler/link optimization flags

After tuning, the same 40-row probe reported:
  parity failed rows: 0
  mean speedup: 8.833x
```

Full S1 token parity sweep:

```text
An accidental first full-mode launch used all historical unique partials
(6979 token hashes) instead of the S1 pair-token set. It was stopped
immediately and the sweep script was patched to source token hashes from
historical_pairwise_rescore_pairs.csv.

Corrected full sweep:
  token hashes: 604
  configs: 9
  total parity rows: 5436
  visible terminal: yes
  log:
    output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
    fast_span_hamming_parity_sweep_v1/
    fast_span_hamming_parity_sweep_v1_s1tokens_full.log

Completed result:
  elapsed: 3065.98 seconds
  result rows: 5436
  parity failed rows: 0
  mean speedup: 12.300x
  median speedup: 11.848x
  min speedup: 4.806x
  max speedup: 17.267x
```

Fast backend speed status:

```text
The tuned backend now meets the hoped-for order of magnitude improvement on
the S1 parity sweep while preserving exact parity with Python on the tested
S1 span configs.
```

Per-config timing summary:

```text
raw_selected_len3_14_hd2_cap256__s1b_default:
  mean Python ms: 875.872
  mean fast ms: 75.061
  mean speedup: 11.724x

raw_selected_len3_14_hd0_exact:
  mean Python ms: 14.636
  mean fast ms: 2.375
  mean speedup: 6.210x

raw_selected_len3_14_hd1:
  mean Python ms: 113.397
  mean fast ms: 10.175
  mean speedup: 11.147x

raw_selected_len4_14_hd1:
  mean Python ms: 91.504
  mean fast ms: 8.042
  mean speedup: 11.383x

raw_selected_len5_8_hd2_fixture_like:
  mean Python ms: 430.701
  mean fast ms: 28.879
  mean speedup: 14.917x

raw_selected_len6_14_hd2_longer:
  mean Python ms: 326.505
  mean fast ms: 22.143
  mean speedup: 14.754x

raw_selected_len3_14_hd2_cap512:
  mean Python ms: 906.083
  mean fast ms: 64.005
  mean speedup: 14.159x

raw_selected_len3_14_hd2_cap1024:
  mean Python ms: 1041.375
  mean fast ms: 65.884
  mean speedup: 15.810x

raw_all_len3_14_hd2_cap256:
  mean Python ms: 900.735
  mean fast ms: 85.038
  mean speedup: 10.594x
```

Derived files:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
fast_span_hamming_parity_sweep_v1/
  fast_span_hamming_parity_sweep_config_summary.csv
  fast_span_hamming_parity_sweep_readout.md
  fast_span_hamming_parity_sweep_summary.json
```

## 40. S1f span-Hamming full calibration setup and canary

Date updated: 2026-05-02

S1f implementation:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
calibrate_span_hamming_full_space_v1.py

tests/tools/test_no_wli_span_hamming_full_calibration_v1.py
```

Contract:

```text
Report-only.
No runtime solver behaviour change.
Numeric rune/base-29 token sequences only.
Truth labels are used only for pair evaluation.
Chunk timing rows are not counted as truth-labelled examples.
Interval rows are aggregate buckets, not every dictionary-entry comparison.
Fast backend is anchored by Python parity spot checks.
```

Focused tests:

```text
py -3.11 -m pytest
  tests/tools/test_no_wli_span_hamming_full_calibration_v1.py
  tests/scoring/span_hamming/test_fast_span_hamming_backend.py

Result:
  13 passed
```

Canary:

```text
token hashes: 40
pairs covered: 758
configs requested: 243
configs run: 54
configs missing: 189
candidate rows: 2160
interval bucket rows: 45803
pair feature summary rows: 1350
parity spot-check failures: 0
elapsed: 3.33 minutes
```

Missing dictionary cuts:

```text
strict / normal / broad / research policy directories are not present under
assets/hamming_dictionary_policies/
```

Canary outputs were preserved under:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
span_hamming_full_calibration_v1/canary_40_token_hashes/
```

Full-run budget:

```text
Projected full S1f runtime from canary:
  about 50-60 minutes for 604 S1 token hashes and 54 runnable configs

Declared budget:
  90 minutes

Stop condition:
  completed run writes summary/readout, or parity failures / unexpected path
  errors cause stop and review.
```

Expected final output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
span_hamming_full_calibration_v1/
```

Interpretation rule:

```text
Full S1f is still report-only. It does not define a gate, does not fit weights,
and does not change solver runtime behaviour.
```

## 41. S1f span-Hamming full calibration completed

Date updated: 2026-05-02

Run status:

```text
Output:
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  span_hamming_full_calibration_v1/

Visible-terminal log:
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  span_hamming_full_calibration_v1/span_hamming_full_calibration_v1_full.log

Declared budget:
  90 minutes

Actual elapsed:
  2219.80 seconds
  37.00 minutes

Stop condition:
  completed normally with summary/readout written
```

Coverage:

```text
S1 pair rows: 2594
unique token hashes: 604
configs requested: 243
configs run: 54
configs missing: 189
candidate feature rows: 32616
interval bucket rows: 745263
pair feature summary rows: 1350
timing chunk rows: 1728
Python parity spot-check rows: 12
Python parity failures: 0
```

Missing dictionary-policy assets:

```text
assets/hamming_dictionary_policies/strict/hamming_raw_1g
assets/hamming_dictionary_policies/normal/hamming_raw_1g
assets/hamming_dictionary_policies/broad/hamming_raw_1g
assets/hamming_dictionary_policies/research/hamming_raw_1g
```

Therefore S1f can compare raw selected/all dictionary modes, but it cannot
support conclusions about strict / normal / broad / research dictionary-policy
cuts until those assets are present.

Key output files:

```text
span_hamming_full_calibration_summary.json
span_hamming_full_calibration_readout.md
span_hamming_full_calibration_analysis_readout.md
span_hamming_full_calibration_best_feature_slices.csv
span_hamming_full_calibration_pair_feature_summary.csv
span_hamming_full_calibration_candidate_features.csv
span_hamming_full_calibration_interval_rows.csv
span_hamming_full_calibration_timing_summary.csv
span_hamming_full_calibration_parity_spot_check.csv
```

Main result:

```text
Span-Hamming has real separating signal on the S1 pair dataset, but the
strongest row-count features are not conservative gates by themselves.

The best net features rescue many current-score failures, but also break a
non-trivial number of current-score controls.
```

Best top-net row-level examples:

```text
raw_selected__len1_14_hd0_exact__cap1024 / span_coverage_selected:
  rescues: 394
  breaks: 236
  net: 158
  unique misranked rescues: 167
  unique control breaks: 87

raw_selected__len3_14_hd2_s1b_shape__cap512 / span_raw_selected_current:
  rescues: 404
  breaks: 258
  net: 146
  unique misranked rescues: 171
  unique control breaks: 109

raw_selected__len1_4_hd2_short_noise__cap1024 / span_raw_selected_current:
  rescues: 412
  breaks: 288
  net: 124
  unique misranked rescues: 176
  unique control breaks: 117
```

Important caution:

```text
The low-break scan did not surface a strong standalone span feature. Short-span
features can score well by net, but they also break many controls and must be
treated as noisy unless constrained by other evidence.

Long-span low-error rows are cleaner in concept but weaker in this run, with
much lower net effect than broad exact/span coverage features.
```

Stage 2 implication:

```text
Do not promote a broad span-Hamming scorer.

Stage 2 may proceed only as report-only gate simulation, and should test
conservative rules such as:
  current score only baseline
  small current-score margin + exact-span evidence
  small current-score margin + long-span low-error evidence
  short-span/noise veto
  cap-pressure no-decision guardrail
  span evidence only in conjunction with word-ngram trust or other diagnostics

Stage 2 should prefer no-decision-heavy, low-break rules over raw top-net span
features.
```

## 42. Stage 2 report-only checkpoint gate simulation

Date updated: 2026-05-02

Implementation:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
simulate_scorer_checkpoint_gates_v1.py

tests/tools/test_no_wli_scorer_checkpoint_gate_simulation_v1.py
```

Output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_checkpoint_gate_simulation_v1/
```

Contract:

```text
Report-only shadow decision simulation.
No runtime selector, scorer, or acceptance behaviour changed.
Truth labels are used only to score rescues and breaks.
Rules are hand-declared diagnostics, not learned weights.
Inactive word-ngram selected side is no-decision.
Span rules use cap-pressure guardrails.
```

Inputs:

```text
S1 current-rescored pair rows:
  historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv

S1b candidate features:
  scorer_component_feature_audit_v1/scorer_component_feature_audit_candidate_features.csv

S1f span candidate features:
  span_hamming_full_calibration_v1/span_hamming_full_calibration_candidate_features.csv
```

Tests:

```text
py -3.11 -m pytest
  tests/tools/test_no_wli_scorer_checkpoint_gate_simulation_v1.py

Result:
  6 passed
```

Run result:

```text
pair count: 2594
current-score misranked pairs: 602
current-score correct controls: 1992
rules simulated: 86
decision rows: 223084
```

Top net rules:

```text
exact_span_coverage_m0.02_t0.005:
  rescues: 358
  breaks: 144
  net: 214
  unique misranked rescues: 149
  unique control breaks: 47

exact_span_coverage_m0.02_t0.01:
  rescues: 324
  breaks: 116
  net: 208
  unique misranked rescues: 136
  unique control breaks: 41
```

These top-net exact-span rules are useful diagnostically, but still break too
many controls for a conservative checkpoint gate.

Low-break rules:

```text
exact_span_and_repeated3_m0.02:
  rescues: 166
  breaks: 6
  net: 160
  unique misranked rescues: 55
  unique control breaks: 3
  dominant override pair fraction: 0.0349

long_span_count_m0.02_t5:
  rescues: 140
  breaks: 4
  net: 136
  unique misranked rescues: 45
  unique control breaks: 2
  dominant override pair fraction: 0.0417

long_span_count_m0.01_t5:
  rescues: 86
  breaks: 0
  net: 86
  unique misranked rescues: 36
  unique control breaks: 0

exact_span_and_word_trust_m0.01:
  rescues: 16
  breaks: 0
  net: 16
  unique misranked rescues: 8
  unique control breaks: 0
```

Interpretation:

```text
The conservative gate direction is now plausible as a report-only Stage 2
finding.

The strongest candidate families are not broad span-Hamming by itself. They are:
  exact-span plus repeated-3 agreement under small current-score margins
  long-span selected-count rules with stricter thresholds
  exact-span plus active word-trust as a sparse confirmation signal

The result still does not justify runtime promotion. It justifies review and,
if accepted, held-out / split validation before any shadow selector.
```

Next required review question:

```text
Are these low-break Stage 2 rules stable by unique pair, artifact, and
fixture/search split, or do they only look good on this S1 historical dataset?
```

## 43. Stage 2 split validation and dominance scan

Date updated: 2026-05-03

Implementation:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
validate_scorer_checkpoint_gate_splits_v1.py

tests/tools/test_no_wli_scorer_checkpoint_gate_split_validation_v1.py
```

Output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
scorer_checkpoint_gate_split_validation_v1/
```

Contract:

```text
Report-only.
No runtime solver behaviour changed.
No new scorer or selector.
Truth labels are evaluation-only.
All 86 Stage 2 rules remain in the output tables.
No Stage 2 decision rows are silently dropped.
```

Validation checks:

```text
row conservation
rule conservation
artifact split metrics
fixture/search split metrics
unique numeric text-pair counts
unique candidate-pair counts
dominant override pair fraction
dominant rescue artifact fraction
dominant rescue fixture/search fraction
leave-one-artifact minimum net / rescue / break
leave-one-fixture/search minimum net / rescue / break
```

Focused tests:

```text
py -3.11 -m pytest
  tests/tools/test_no_wli_scorer_checkpoint_gate_split_validation_v1.py

Result:
  7 passed
```

Run result:

```text
decision rows: 223084
expected decision rows: 223084
row conservation ok: true
rules: 86
rules with decisions: 86
missing summary rules: 0
dropped summary rules: 0
```

Review status counts:

```text
split_stable_candidate: 4
low_break_split_concentration_risk: 3
clean_but_sparse: 9
moderate_break_review: 6
dominance_risk: 11
no_signal: 7
too_many_breaks: 46
```

Split-stable candidates:

```text
exact_span_and_repeated3_m0.02:
  rescues: 166
  breaks: 6
  net: 160
  unique misranked rescues: 55
  unique control breaks: 3
  rescue artifacts: 16
  rescue fixture/search cells: 6
  max rescue artifact fraction: 0.193
  max rescue fixture/search fraction: 0.470
  leave-one-artifact min net: 128
  leave-one-fixture/search min net: 82

long_span_count_m0.02_t5:
  rescues: 140
  breaks: 4
  net: 136
  unique misranked rescues: 45
  unique control breaks: 2
  rescue artifacts: 16
  rescue fixture/search cells: 5
  max rescue artifact fraction: 0.179
  max rescue fixture/search fraction: 0.514
  leave-one-artifact min net: 111
  leave-one-fixture/search min net: 64

long_span_count_m0.05_t5:
  rescues: 140
  breaks: 6
  net: 134
  unique misranked rescues: 45
  unique control breaks: 3
  rescue artifacts: 16
  rescue fixture/search cells: 5
  max rescue artifact fraction: 0.179
  max rescue fixture/search fraction: 0.514
  leave-one-artifact min net: 109
  leave-one-fixture/search min net: 62

exact_span_and_repeated3_m0.01:
  rescues: 50
  breaks: 4
  net: 46
  unique misranked rescues: 17
  unique control breaks: 2
  rescue artifacts: 14
  rescue fixture/search cells: 5
  max rescue artifact fraction: 0.080
  max rescue fixture/search fraction: 0.480
  leave-one-artifact min net: 42
  leave-one-fixture/search min net: 22
```

Low-break but split-concentrated signals:

```text
long_span_count_m0.01_t5:
  rescues: 86
  breaks: 0
  max rescue artifact fraction: 0.291
  review status: low_break_split_concentration_risk

long_span_count_m0.005_t3:
  rescues: 36
  breaks: 0
  max rescue artifact fraction: 0.361
  max rescue fixture/search fraction: 0.722
  review status: low_break_split_concentration_risk

long_span_count_m0.005_t5:
  rescues: 30
  breaks: 0
  max rescue artifact fraction: 0.400
  max rescue fixture/search fraction: 0.800
  review status: low_break_split_concentration_risk
```

Interpretation:

```text
The strongest split-stable Stage 2 candidates are:
  exact_span_and_repeated3_m0.02
  long_span_count_m0.02_t5
  long_span_count_m0.05_t5
  exact_span_and_repeated3_m0.01

The zero-break long-span variants are not silently promoted because their rescue
evidence is too concentrated.

This remains report-only historical S1 validation, not fresh held-out solver
validation and not runtime approval.
```

Next stage:

```text
Run held-out / split validation outside the discovery rows, or run a shadow
selector on fresh candidate pools while keeping runtime selection unchanged.
```
