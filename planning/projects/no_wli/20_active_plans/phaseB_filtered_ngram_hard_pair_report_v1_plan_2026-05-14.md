# PhaseB Filtered N-Gram Hard-Pair Report v1 Plan - 2026-05-14

Status: closed / superseded
Work status: implemented_report_run_closed
Project: no_wli
Owner: agent
Last updated: 2026-05-14
Superseded by:
- planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md
Supersedes:
- planning/temp_files/temp_new_ngram_scorer.txt
- planning/projects/no_wli/20_active_plans/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_plan_2026-05-14.md

Source-of-truth parents:
- planning/projects/no_wli/20_active_plans/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_plan_2026-05-14.md
- planning/projects/no_wli/40_review_summaries/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_review_note_2026-05-14.md
- output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1/readout.md
- output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1/readout.md

## Purpose

Build a report-only hard-pair analysis using the filtered strict/normal n-gram
assets.

The aim is to test whether true filtered phrase/ngram evidence improves on the
previous simple coherence proxy and helps suppress span-Hamming breaks.

This is not a production scorer change.

Do not change:

- production scorer weights
- default scorer config
- candidate ranking policy
- span-Hamming calibration outputs

## Evidence Status

The currently available n-gram assets are built in sample mode:

```text
NGRAM_ASSET_MODE = "sample"
SAMPLE_LINE_LIMIT_PER_ORDER = 25000
FULL_ASSET_AVAILABLE = false
```

This is acceptable for a pilot/report, but it is not final full-corpus n-gram
calibration.

Every manifest and readout must record the asset mode and line limit. The final
readout must clearly say:

```text
This report uses filtered sample n-gram assets. Results are pilot evidence, not final full-corpus n-gram calibration.
```

## Available Assets

Asset root:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1
```

Orders available:

- 2-grams
- 3-grams
- 4-grams
- 5-grams

For v1:

- core score: 2-, 3-, and 4-grams
- diagnostic/stress only: 5-grams

Do not include 5-grams in the main combined v1 score unless a separate score
family explicitly says it is testing 5-gram diagnostics.

Dictionary cuts:

- strict
- normal

They are content-distinct. Approximate FWD aggregate row counts:

| Order | Normal | Strict |
|---:|---:|---:|
| 2g | 3489 | 1163 |
| 3g | 15226 | 8609 |
| 4g | 21175 | 13090 |
| 5g | 19850 | 15740 |

Keep strict and normal separate in all feature rows and summaries.

Directions available:

- normal_fwd
- normal_rev
- strict_fwd
- strict_rev

For v1, use FWD only. The hard-pair candidate corpus is FWD, and FWD/REV must
never be combined.

Rows include:

- count
- log_count
- phrase_count
- top_latin_count
- rune_token_ids
- rune_joined
- rune_words
- top_latin_ngram
- latin_examples

If any field is missing in implementation, record it explicitly.

## Critical Scanning Rule

For no-WLI candidate scanning, use:

```text
rune_token_ids
```

Do not use:

```text
rune_key_hex
```

Reason: `rune_key_hex` includes `0xff` word separators. No-WLI candidate
streams do not have word boundaries.

The scanner must compare candidate token slices against encoded phrase token
sequences parsed from `rune_token_ids`.

## Candidate Stream Shape

The hard-pair candidate corpus contains:

- 604 candidates
- 1000 tokens per candidate
- 1208 chunks
- 2 chunks per candidate
- 500 tokens per chunk
- direction = fwd

Therefore v1 must support candidate-level aggregation across chunks. Do not
assume one candidate equals one 500-token chunk.

Score each 500-token chunk independently. For each candidate, aggregate across
its two chunks.

For each score family, report at least:

- chunk_0_score
- chunk_1_score
- candidate_mean_score
- candidate_max_score
- candidate_min_score
- candidate_median_score
- candidate_positive_chunk_count
- candidate_positive_chunk_fraction

For pairwise comparison, choose and report the aggregation used.

For v1:

- primary candidate score = mean of chunk scores
- secondary diagnostic = max chunk score

## Asset Validation

Before scoring hard pairs, validate the assets.

Required outputs:

- ngram_asset_validation_summary.json
- ngram_asset_counts_by_order.csv
- ngram_asset_token_length_quantiles.csv
- ngram_asset_duplicate_report.csv
- ngram_asset_top_examples.csv
- readout_asset_validation.md

Validation must check:

- asset mode = sample
- orders present = 2, 3, 4, 5
- cuts present = strict, normal
- directions present = fwd, rev
- `rune_token_ids` present
- no empty token sequences
- duplicate encoded sequences counted
- frequency/count fields present
- normal and strict are content-distinct

## Duplicate Handling

Duplicate encoded token sequences exist but are not common.

Collapse duplicate encoded sequences for scanning, but preserve metadata.

For each encoded sequence, keep:

- encoded_token_sequence
- dictionary_cut
- direction
- ngram_order
- phrase_count
- sum_count
- max_count
- max_log_count
- top_latin_ngram
- latin_examples
- all_rune_joined_examples if manageable

Feature extraction should count encoded-token hits consistently. Do not
double-count the same encoded sequence merely because multiple Latin phrases map
to it, unless a named multiplicity-weighted feature explicitly does that.

## Scanner Design

For each 500-token candidate chunk:

```text
for each start offset:
  check possible encoded n-gram token lengths
  count exact phrase-token hits
```

Use an efficient index keyed by something like:

```text
direction
dictionary_cut
ngram_order
encoded_token_length
first_token
token_tuple
```

Do not brute-force compare every n-gram against every offset.

## Chunk-Level Features

For each candidate/chunk/cut/order/weighting mode, compute:

- hit_count
- unique_hit_count
- binary_presence
- unweighted_hit_density
- log_count_weighted_hit_sum
- log_count_weighted_hit_density
- top_k_log_count_sum
- max_log_count
- mean_hit_token_length
- max_hit_token_length
- nonoverlap_hit_count
- nonoverlap_log_count_weighted_sum
- nonoverlap_token_coverage

Weighting modes:

- unweighted
- log_count_weighted
- binary_presence

Optional later:

- rank_weighted
- multiplicity_weighted

## Top-Hit Output

Write a compact top-hit file:

```text
candidate_ngram_top_hits.jsonl.gz
```

Each record should include:

- candidate_id
- chunk_id
- dictionary_cut
- ngram_order
- hit_start
- hit_end
- encoded_token_length
- rune_joined
- top_latin_ngram
- latin_examples
- count
- log_count

This is required for manual review.

## Score Families

Create explicit report-only score families and save definitions in:

```text
score_definition_manifest.json
```

N0 - current scorer baseline:

- current scorer preference

N1 - normal 2-gram coherence:

- normal FWD 2-gram features only

N2 - normal 3-gram coherence:

- normal FWD 3-gram features only

N3 - normal 4-gram coherence:

- normal FWD 4-gram features only

N4 - normal 2-4 combined core:

- main v1 normal n-gram score
- use per-order normalisation/capping so 2-grams do not dominate
- `N4 = mean(capped N1, capped N2, capped N3)`

N5 - strict 2-4 combined core:

- strict-only equivalent of N4

N6 - normal plus strict support:

- normal 2-4 combined
- smaller strict support term

N7 - longest/highest-order phrase support:

- rewards 3/4-gram hits more than many 2-gram hits

N8 - non-overlap coverage score:

- uses non-overlapping phrase-hit coverage over each 500-token chunk

N9 - 5-gram diagnostic:

- use 5-grams only as a diagnostic/stress family
- do not include this in the main 2-4 combined score

N10 - span support plus n-gram core:

- `normal length 7 HD2 exact_count_norm`
- plus normal 2-4 n-gram coherence

N11 - S5 span-Hamming plus n-gram core:

- `S5_local_null_positive_selected`
- plus normal 2-4 n-gram coherence

N12 - current-margin support policy:

- use n-gram support only when current-score margin is small

N13 - conservative support policy:

- only apply when n-gram plus span support margin is above a threshold

## Proxy Comparisons

The report must include prior reference score families:

- Panel A baseline
- `S5_local_null_positive_selected`
- `normal length 7 HD2 exact_count_norm`
- `coherence_proxy_v1`
- `C7_len7_hd2_exact_support_plus_coherence`
- `C8_span_plus_coherence_conservative`

Key question:

```text
Does real filtered n-gram evidence beat, match, or explain the simple coherence proxy?
```

## Pairwise Evaluation

Evaluate every score family on the same 2594 hard pairs.

For each score, report:

- n_pairs
- truth_better_preference_count
- truth_better_preference_rate
- 95% confidence interval
- rescues
- breaks
- net_rescues
- mean_gap
- median_gap
- gap_q05
- gap_q25
- gap_q75
- gap_q95

Split by:

- current scorer correct
- current scorer misranked
- candidate label if available
- source family if available

## Margin Sweep

For each score family, run a margin sweep at:

```text
0.0
0.01
0.025
0.05
0.10
0.20
0.30
0.40
0.50
0.75
1.00
1.50
2.00
```

Report:

- threshold
- applied_count
- rescues
- breaks
- net
- precision_of_applied_overrides
- misrank_recall

## Correlation Report

Report correlations against:

- current score margin
- Panel A margin
- S5 margin
- normal length 7 HD2 exact support margin
- coherence_proxy_v1 margin
- C7 proxy-combined margin

This matters because the previous proxy result was useful but still highly
correlated with current/span-Hamming signals.

## Required Outputs

Create:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_hard_pair_report_v1
```

Required files:

- config.json
- input_manifest.json
- ngram_asset_manifest.json
- ngram_asset_validation_summary.json
- score_definition_manifest.json
- candidate_ngram_feature_rows.csv.gz
- candidate_ngram_chunk_summary.csv
- candidate_ngram_candidate_summary.csv
- candidate_ngram_top_hits.jsonl.gz
- score_family_pairwise_summary.csv
- score_family_margin_sweep.csv
- pairwise_score_gaps.csv.gz
- ngram_order_summary.csv
- dictionary_cut_summary.csv
- weighting_mode_summary.csv
- correlation_summary.csv
- proxy_vs_filtered_ngram_comparison.csv
- top_ngram_rescues.csv
- top_ngram_breaks.csv
- top_ngram_false_positives.csv
- top_ngram_false_negatives.csv
- readout.md

Optional plots can come later. First priority is correct CSV/readout output.

## Readout Requirements

`readout.md` must answer:

- Is this sample or full n-gram evidence?
- Which n-gram orders were used?
- Was 5-gram used only diagnostically?
- Does true filtered n-gram evidence beat the proxy coherence score?
- Which order helps most: 2, 3, 4, or 5 diagnostic?
- Does strict add precision?
- Does normal dominate?
- Does chunk mean or chunk max work better?
- Does filtered n-gram evidence preserve span-Hamming rescues?
- Does it suppress span-Hamming breaks?
- Does any conservative rule give positive net rescues with low breaks?
- How correlated is it with current score and span-Hamming scores?

## Success Criteria

v1 succeeds if it gives a clear answer to:

```text
Do sample filtered n-gram assets provide useful phrase/order evidence on the hard-pair set?
```

A positive result could be:

- true filtered n-grams match or outperform proxy coherence

A still useful result could be:

- sample filtered n-grams underperform proxy coherence
- but reveal which orders/cuts need full assets

## Follow-Up After v1

If v1 is promising:

- build full n-gram assets
- rerun filtered n-gram hard-pair report
- run held-out/source-family split simulation
- then consider a report-only combined scorer package

If v1 is not promising:

- inspect top hits and failure cases
- decide whether sample mode is too small
- decide whether exact no-WLI phrase scanning is too brittle
- try segmentation-aware n-gram matching using span-Hamming word-hit sequences

## Implementation Recommendation

For the first implementation, use:

- FWD only
- sample n-gram assets
- orders 2, 3, 4 as core
- 5-grams as diagnostic only
- strict and normal separately
- `rune_token_ids` scanning only
- two 500-token chunks per candidate
- candidate score = mean chunk score, with max chunk score as diagnostic
- hard-pair rescue/break evaluation
- comparison against proxy coherence and span-Hamming support

This should give a clean first answer without adding too many moving parts.

## Guardrails

- Keep the work report-only.
- Do not use CLI arguments; use hardcoded constants.
- Resolve repo root from script location.
- Keep output paths repo-relative.
- Do not change production scorer weights/defaults/ranking policy.
- Do not change span-Hamming calibration outputs.
- Do not launch a long-running benchmark or investigation without a written
  runtime budget and stop condition.
- Do not use REV data in the FWD v1 report.

## Implementation Status - 2026-05-14

Implemented and ran:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_filtered_ngram_hard_pair_report_v1.py
```

Output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_hard_pair_report_v1
```

Run facts:

- candidates: `604`
- hard pairs: `2594`
- asset mode: `sample`
- sample line limit per order: `25000`
- elapsed: about `20s`
- FWD-only scoring; REV assets were validated but not used for the hard-pair
  score

Key result:

- exact sample filtered n-gram support was too sparse for the damaged no-WLI
  hard-pair set
- `N4_normal_2_4_combined_core`: truth preference `2 / 2594`, rescues `0`,
  breaks `0`, net `0`
- `N6_normal_plus_strict_support`: truth preference `2 / 2594`, rescues `0`,
  breaks `0`, net `0`
- `N10_span_len7_support_plus_ngram_core` matched the existing span-Hamming
  carry-forward signal rather than adding useful exact n-gram evidence:
  truth preference `2016 / 2594`, rescues `286`, breaks `240`, net `+46`

Conclusion:

- this exact joined-phrase n-gram line answered its v1 question and is closed
- the next approved live line is robust word-structured n-gram Hamming coherence
- do not reopen exact filtered n-gram scanning unless the Hamming scorer needs it
  as a baseline rerun or field-compatibility check

Successor:

```text
planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md
```
