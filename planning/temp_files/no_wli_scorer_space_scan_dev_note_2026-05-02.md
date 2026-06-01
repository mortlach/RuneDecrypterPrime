# No-WLI S1e scorer-space parameter scan dev note

Date: 2026-05-02  
Proposed stage: `S1e scorer_parameter_space_scan_v1`  
Runtime status: report-only; no solver/runtime behaviour change  
Primary goal: understand scorer settings, robustness, and cost before Stage 2 gate simulation

## Why this stage exists

S0/S1/S1b/S1c/S1d support the scorer/ranking bottleneck, but they do not yet prove that the current span-Hamming and word-ngram defaults are the right settings for a checkpoint gate.

The next step should not be gate design. It should be a scorer-space scan:

```text
Which scorer settings separate current-score failures from controls?
How sensitive are those findings to dictionary policy, span length, Hamming tolerance, and word-ngram activation threshold?
How expensive are the scorer calls at realistic attack lengths, especially 300 and 500 chars?
```

The starter script is:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_scorer_parameter_space_v1.py
```

I have provided it as `scan_scorer_parameter_space_v1.py` for copy-paste into that path.

## Main evidence source

Use the S1 current-rescored pair data:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv
```

Use numeric rune/base-29 token sequences from:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/historical_partial_text_review_v1/unique_partial_text_rows.csv
```

All partial text must remain numeric tokens in `0..28`. Do not use English renderings.

## Important interpretation rule

Pairwise rescue/break metrics should be computed on full S1 candidate texts only, because the truth/match label is a whole-candidate label.

300/500-character chunks are very useful for timing and feature-distribution benchmarking, but they are not independent labelled examples.

So split the study into:

```text
full candidate texts:
  pairwise scorer evidence, rescues, breaks, controls

300/500/1000 chunks:
  timing, feature distribution, cost estimates
```

## Target benchmark lengths

Use:

```text
300 chars
500 chars
1000 chars
```

Reason:

```text
300/500 chars are closer to the text sizes we expect to attack.
1000 chars preserves direct comparability with the current S1 pair dataset.
```

For each token sequence, take deterministic chunks:

```text
prefix
middle
suffix
```

Do not random-sample chunks unless a fixed seed and explicit sampling contract are added.

## Span-Hamming settings to scan

The S1b default was:

```text
len_min=3
len_max=14
max_hd=2
max_candidates_per_window=256
require_selected=True
wordlist_dir=assets/hamming_raw_1g
```

That is a good broad diagnostic, but it may be too permissive for a gate.

The first scan should include:

```text
raw_selected_len3_14_hd2_cap256__s1b_default
raw_selected_len3_14_hd0_exact
raw_selected_len3_14_hd1
raw_selected_len4_14_hd1
raw_selected_len5_8_hd2_fixture_like
raw_selected_len6_14_hd2_longer
raw_selected_len3_14_hd2_cap512
policy_strict_len3_14_hd2
policy_normal_len3_14_hd2
policy_broad_len3_14_hd2
```

Questions this answers:

```text
Does the span signal survive exact-only or one-mismatch settings?
Are short approximate spans causing noisy coverage?
Does the char4-overfit fixture-like length range help on S1 data?
Does candidate-cap pressure change the result?
Do strict/normal/broad dictionaries change rescues and breaks?
```

## Dictionary policy question

Yes, we should test truncated/policy dictionaries. But do not switch defaults blindly.

A stricter dictionary may be better for checkpoint gating because broad dictionaries can increase chance span matches. The scan should compare dictionary policies by rescues, breaks, unique-pair results, active word-ngram coverage, and timing.

If `research` dictionaries exist, treat them as diagnostic only until proven safe.

## Word-ngram settings to scan

Word-ngram depends on exact span-Hamming intervals. It must be rerun under each relevant span config.

First scan:

```text
min_positions = 6, 9, 12, 18, 24
alpha = 0.4
miss_logp = -20.0
```

Optional second scan if xent/backoff looks useful:

```text
alpha = 0.2, 0.4, 0.7, 1.0
miss_logp = -10, -15, -20
```

Interpretation rules:

```text
word_ngram_trust_score:
  positive-confidence signal only
  inactive candidate means zero confidence, but neither-active means no-decision

word_ngram_xent / backoff_xent / miss_rate:
  compare only when both sides are active
  inactive means no-decision, not score 20.0 or zero
```

## Timing requirements

For each config and sample kind, record:

```text
build time
score time mean
score time median
score time p95
score time max
sample count
```

Separate:

```text
span-Hamming backend build time
span-Hamming score time
word-ngram SQLite/runtime build time
word-ngram score time
```

This matters because high-cost scorers may be acceptable at checkpoints but not in inner loops.

## Outputs expected from S1e

Output folder:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/scorer_parameter_space_scan_v1/
```

Files:

```text
scorer_parameter_space_candidate_features.csv
scorer_parameter_space_config_summary.csv
scorer_parameter_space_timing_summary.csv
scorer_parameter_space_pair_feature_summary.csv
scorer_parameter_space_pair_flags_and_active_states.csv
scorer_parameter_space_summary.json
scorer_parameter_space_readout.md
```

## Required summary metrics

For each span/word config and feature:

```text
pair_count
current_misranked_pair_count
current_correct_control_pair_count
prefers_truth_better
prefers_truth_worse
ties
no_decision
rescues
breaks
net = rescues - breaks
unique text-pair preference counts
```

For word-ngram active state:

```text
both active
winner only active
challenger only active
neither active
same split for current-score failures and controls
```

For timing:

```text
component
sample_kind
count
mean_ms
median_ms
p95_ms
max_ms
```

## Tests to add

Add focused tests for the pure logic before trusting the scan:

```text
tests/tools/test_no_wli_scorer_parameter_space_scan_v1.py
```

Minimum tests:

```text
numeric token parser rejects values outside 0..28
chunk builder produces deterministic prefix/middle/suffix chunks
full candidate samples are marked separately from timing chunks
truth-labelled pair metrics ignore timing chunks
word xent/backoff/miss features are no-decision unless both candidates are active
word trust neither-active is no-decision
span candidate cap pressure is reported
rescues/breaks are counted from current-score failure/control split
config summary records span and word settings explicitly
```

## Char-LM scan note

The starter script does not implement a char-LM parameter scan. That should be added only after the full LMPrime/Torch scorer construction path and assets are cross-checked in the full repo.

The char scan should eventually include:

```text
char3 only
char4 only
char3/4 = 0.2/0.8
char3/4 = 0.5/0.5
char3/4 = 0.8/0.2
pct.logp.win5
pct.logp.win10
pct.logp.win20
avg/global objective if already supported
```

Do not guess the builder API. Read the actual current repo files before wiring char-LM scanning.

## Stage 2 remains on hold

Do not start Stage 2 gate simulation until S1e answers:

```text
Are useful span/word signals robust to reasonable parameter changes?
Are they dominated by one config or permissive defaults?
Are they too slow for the intended checkpoint use?
Which settings give useful rescues with low control breakage?
```

Only after that should Stage 2 simulate cautious checkpoint gates.
