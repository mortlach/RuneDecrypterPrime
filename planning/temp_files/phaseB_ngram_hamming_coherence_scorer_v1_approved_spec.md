# PhaseB Robust N-Gram Hamming Coherence Scorer v1

Short name: `ngram_hamming_coherence_v1`

Status: approved design spec, pre-repo-inspection draft  
Date: 2026-05-14  
Scope: no-WLI, FWD-first, production-style scorer design

## 0. Summary

Build a robust no-WLI phrase/order evidence layer for damaged candidate text.

The scorer answers:

> After the word-Hamming scorer has found candidates with local damaged-word evidence, do those damaged word-like regions line up into plausible ordered phrases?

This is a second-stage coherence scorer. It is not intended to replace the word-Hamming scorer. It is intended to sit after the word-Hamming layer and before, or inside, a joint scorer that also uses the current character/language scorer.

Expected damage regime:

- primary test range: 20% to 50% damaged text
- target difficult case: around 50% damaged text
- less damaged cases are included to check scaling and calibration
- damage profiles should reuse the same damage definitions already used by the word-Hamming scorer

The scorer must be production-shaped from the start:

- independent C++ backend
- explicit score contract
- exact counting of all eligible hits
- no silent fallback
- no hit caps
- deterministic outputs
- full manifests
- tests before full benchmark runs

The existing span/word-Hamming C++ layer may be used as an implementation guide, but this scorer gets its own backend.

---

## 1. Scientific aim

### 1.1 Problem

Hard-pair testing showed that word/span-Hamming evidence is real, but local word-like fragments alone are not enough. Bad candidates can contain plausible local words. The missing layer is order and phrase coherence.

The earlier exact filtered n-gram scanner was too strict. It looked for exact joined phrase strings and found very few hits. That is expected for damaged no-WLI candidate text.

The new scorer must allow Hamming damage at the word/phrase level.

### 1.2 Main question

Can filtered n-gram phrase evidence, with Hamming damage allowed, improve hard-pair ranking and suppress local-word-only false positives?

### 1.3 Specific questions

1. Do damaged word-like spans form real filtered n-grams more often in truth-better candidates?
2. Which n-gram orders help most: 2, 3, 4, and diagnostic 5?
3. Does normal dominate, or does strict add useful precision?
4. Does word-structured phrase Hamming beat joined-phrase Hamming?
5. Does n-gram Hamming preserve word-Hamming rescues?
6. Does n-gram Hamming suppress word-Hamming breaks?
7. Does the signal remain useful across 20%, 30%, 40%, and 50% damage settings?
8. Can the final scorer act as a positive support layer in a joint scorer?

---

## 2. Role in the wider scorer stack

The intended scoring stack is:

1. Word-Hamming scorer  
   Finds candidates with enough local damaged-word evidence.

2. N-gram Hamming coherence scorer  
   Checks whether local damaged-word evidence forms plausible phrase/order evidence.

3. Joint scorer  
   Combines word-Hamming evidence, n-gram coherence, and current character/language score.

The n-gram coherence layer should mostly be a positive support signal. In v1, absence of n-gram evidence should not be treated as strong negative evidence, because highly damaged true candidates may only contain sparse islands of phrase coherence.

---

## 3. Scope

### 3.1 In scope

- FWD no-WLI candidates
- filtered strict and normal n-gram assets
- n-gram orders 2, 3, and 4 as core
- n-gram order 5 as diagnostic/stress only
- word-structured Hamming phrase scoring
- 20% to 50% damaged-text evaluation
- two 500-token chunks per candidate, where available
- hard-pair rescue/break reporting
- comparison with:
  - current scorer baseline
  - word/span-Hamming rows
  - coherence proxy
  - exact filtered n-gram scanner
- production-style scorer contract
- independent C++ backend
- Python reference implementation for tiny tests
- deterministic manifests and tests

### 3.2 Out of scope for v1

- changing production default ranking weights
- mixing FWD and REV in one calibration
- WLI scoring
- edit-distance matching with insertions/deletions
- black-box learned scorer
- fitted weights on the hard-pair set
- top-k scoring
- hit-count caps
- silent narrowing of a requested profile

### 3.3 Direction rule

FWD and REV must never be combined silently.

v1 is FWD only.

REV may be a separate later report with a separate manifest and separate score definitions.

---

## 4. Input data

### 4.1 Candidate data

Use the same hard-pair candidate set as the recent no-WLI road tests, subject to repo verification:

- 2594 hard pairs
- 604 resolved FWD candidate token streams
- 1000 tokens per candidate
- 2 chunks per candidate
- 500 tokens per chunk

Candidate streams are no-WLI token streams. They do not contain word separators.

### 4.2 Damage data

Reuse the existing damage definitions from the word-Hamming scorer.

Required damage levels for this scorer:

- 20%
- 30%
- 40%
- 50%

Optional diagnostic levels may be included if already present in the word-scorer framework, but the approved v1 range is 20% to 50%.

Each output must record:

- damage model name
- damage level
- random seed or deterministic damage identifier, if applicable
- candidate source
- chunk id
- token count
- whether damage was applied before or after chunking
- whether the same damaged stream was used for word-Hamming and n-gram Hamming evaluation

No new damage model should be invented inside this scorer unless it is approved separately.

### 4.3 Filtered n-gram assets

Assume filtered assets exist for:

- `normal_fwd`
- `strict_fwd`
- `normal_rev`
- `strict_rev`

Orders:

- 2
- 3
- 4
- 5

Core v1 uses:

- 2
- 3
- 4

5-grams are diagnostic only.

### 4.4 Asset mode

The n-gram assets may be sample-mode or full-mode assets. Every output must record:

- `NGRAM_ASSET_MODE`
- `SAMPLE_LINE_LIMIT_PER_ORDER`
- `FULL_ASSET_AVAILABLE`
- `NGRAM_ASSET_BUILD_ID`
- `NGRAM_ASSET_PATHS`

The readout must clearly say whether results use sample or full n-gram assets.

### 4.5 Critical token field

Use:

- `rune_token_ids`

Do not use:

- `rune_key_hex`

Reason:

- `rune_key_hex` contains separator material.
- candidate streams do not contain word boundaries.
- scanning with the wrong field silently changes the problem.

---

## 5. Main design decision

The scorer uses word-structured phrase Hamming.

It does not use exact joined phrase scanning as the main method.

Exact joined phrase scanning asks:

> Does `OFTHE` occur exactly?

Damaged no-WLI candidates may contain:

- `OFXHE`
- `OFTXE`

or similar partial damage. Exact phrase scanning misses these.

Joined phrase Hamming improves this, but still treats:

> `OF THE`

as:

> `OFTHE`

and loses word structure.

The robust scorer asks:

> Can adjacent damaged word spans form a filtered n-gram phrase?

Example:

```text
offset 100: OF   matched HD0
offset 102: THE  matched HD1
sequence: OF THE
filtered 2-gram exists
total phrase HD = 1
```

That is the coherence signal.

---

## 6. Backend decision

Build a new independent C++ backend for `ngram_hamming_coherence_v1`.

The existing word/span-Hamming C++ backend may be used as a guide for:

- pybind style
- build pattern
- test style
- deterministic output conventions
- performance expectations

But it must not constrain this scorer and must not be changed in a way that risks existing word/span-Hamming behaviour.

Reasons for a new backend:

1. This scorer needs phrase-aware matching.
2. It needs word-structured phrase verification.
3. It needs exact counting of all eligible phrase hits.
4. It needs production manifests and deterministic fail behaviour.
5. It must avoid the hit-cap mistakes from earlier word-Hamming work.
6. It should not add risk to an existing working backend.

---

## 7. No-hit-cap rule

This is a hard rule.

The scorer must not use hit caps as part of the score.

For any fixed scoring profile, the backend must either:

1. evaluate all eligible phrase hits exactly, or
2. fail clearly and report why the requested profile is too large or invalid.

It must not silently keep only the first, best, top-k, or otherwise capped subset of hits.

### 7.1 Allowed eligibility rules

Allowed:

- direction
- dictionary cut
- n-gram order
- minimum total phrase token length
- maximum total phrase token length
- total phrase HD threshold
- maximum per-word HD threshold
- normalised phrase HD threshold
- damage level
- sample/full asset mode
- candidate subset for pilot runs

These define the scientific question.

### 7.2 Disallowed score behaviour

Disallowed:

- keep only best N hits
- max phrase hits per offset
- max phrase hits per chunk
- max word hits per offset/length
- top-k weighted scoring
- top-k phrase scoring
- capped per-order score values
- silently dropping matches for speed
- silently disabling an order
- silently switching strict/normal
- silently switching sample/full assets
- silently switching FWD/REV
- silently switching from word-structured Hamming to joined-string Hamming

### 7.3 Debug examples

Bounded top examples are allowed for human inspection only.

They must be labelled as examples.

They must never feed back into score values.

---

## 8. Phrase eligibility profiles

The scorer is configured by named phrase eligibility profiles.

A profile defines:

- allowed n-gram orders
- dictionary cut
- minimum total phrase token length
- optional maximum total phrase token length
- maximum total phrase HD
- maximum per-word HD
- optional normalised HD ceiling
- damage levels to evaluate
- whether the profile is core or diagnostic

No profile may use hit-count caps.

### 8.1 Approved initial profiles

#### P0_exact_short

Purpose: exact baseline.

```text
orders: 2, 3, 4
cuts: normal, strict
min_phrase_token_length: 5
max_total_phrase_hd: 0
max_word_hd: 0
normalised_hd_ceiling: 0.0
damage_levels: 20, 30, 40, 50
role: baseline
```

#### P1_word_analogue_len7_hd2

Purpose: direct analogue of the useful word-Hamming result.

```text
orders: 2, 3, 4
cuts: normal, strict
min_phrase_token_length: 7
max_total_phrase_hd: 2
max_word_hd: 2
normalised_hd_ceiling: none
damage_levels: 20, 30, 40, 50
role: core
```

#### P2_conservative_len8_hd2

Purpose: reduce short-phrase false positives.

```text
orders: 2, 3, 4
cuts: normal, strict
min_phrase_token_length: 8
max_total_phrase_hd: 2
max_word_hd: 1
normalised_hd_ceiling: none
damage_levels: 20, 30, 40, 50
role: core
```

#### P3_longer_phrase_len10_hd3

Purpose: test longer damaged phrase support.

```text
orders: 3, 4
cuts: normal, strict
min_phrase_token_length: 10
max_total_phrase_hd: 3
max_word_hd: 2
normalised_hd_ceiling: none
damage_levels: 20, 30, 40, 50
role: core diagnostic
```

#### P4_strict_long_len10_hd2

Purpose: test strict high-precision support.

```text
orders: 3, 4
cuts: strict
min_phrase_token_length: 10
max_total_phrase_hd: 2
max_word_hd: 1
normalised_hd_ceiling: none
damage_levels: 20, 30, 40, 50
role: diagnostic/support
```

#### P5_order5_diagnostic_len12_hd3

Purpose: stress test high-order support.

```text
orders: 5
cuts: normal, strict
min_phrase_token_length: 12
max_total_phrase_hd: 3
max_word_hd: 2
normalised_hd_ceiling: none
damage_levels: 20, 30, 40, 50
role: diagnostic only
```

### 8.2 Profile tuning rule

v1 may compare named fixed profiles.

v1 must not fit profile parameters on the hard-pair set and then report the fitted result as if it were independent evidence.

Allowed:

- compare fixed profiles
- report performance by profile
- recommend a profile for later validation

Not allowed:

- optimise many thresholds against hard-pair performance
- learn weights
- silently revise profiles after seeing full results

---

## 9. Architecture

### 9.1 Python layer

The Python layer handles:

- asset validation
- phrase index building
- tiny reference implementation
- scorer config
- scorer manifests
- report writing
- hard-pair analysis
- damage-level comparisons
- production-style acceptance tests

### 9.2 C++ layer

The C++ layer handles:

- fast candidate scanning
- phrase-aware matching
- word-structured phrase verification
- exact aggregation of all eligible hits
- deterministic summary counters
- optional bounded debug examples

### 9.3 No unbounded word-hit lattice in production mode

The production scorer should not materialise a large word-hit lattice and then trim it.

Instead, it should stream through eligible phrase checks and aggregate exact counts.

A debug mode may emit word-hit and phrase-hit examples, but only for small pilot runs.

### 9.4 Matching design

Preferred runtime structure:

1. Load phrase index for direction/cut/order/profile.
2. Scan candidate chunk for possible phrase placements.
3. Verify each phrase word by word at fixed adjacent offsets.
4. Compute phrase Hamming fields.
5. If the phrase satisfies the active profile, count it exactly.
6. Update chunk features.
7. Emit bounded examples only for readout/debug.

Implementation may use anchor-and-verify or another exact method, provided the output is identical to the Python reference implementation on tests.

---

## 10. Phrase index

### 10.1 Index keys

Build phrase index keyed by:

```text
direction
dictionary_cut
ngram_order
word_token_sequence_per_word
```

If stable word IDs are verified later, they may be stored as metadata, but matching should be safe by rune token sequence.

### 10.2 Phrase entry fields

Each phrase entry should include:

```text
phrase_id
ngram_order
dictionary_cut
direction
word_texts, if available
rune_words, if available
rune_token_ids_by_word
joined_rune_token_ids
word_lengths
phrase_token_length
count
log_count
phrase_count
top_latin_count
top_latin_ngram
latin_examples
duplicate_row_count
sum_count
max_count
source_asset_ids
```

### 10.3 Duplicate handling

If multiple n-gram rows map to the same word/token sequence:

- collapse for matching
- preserve duplicate count
- preserve summed count
- preserve max count
- preserve top examples
- write duplicate summary

Matching identity is the rune-token word sequence, not the Latin display text.

---

## 11. Phrase-hit rule

A phrase hit is valid if:

1. the candidate contains adjacent fixed-length word spans matching the phrase word lengths;
2. the phrase word-token sequence exists in the filtered n-gram phrase index;
3. each word is within the profile's per-word HD threshold;
4. the total phrase HD is within the profile threshold;
5. the phrase token length satisfies the profile length rule;
6. the phrase direction, cut, and order match the active profile.

For each phrase hit compute:

```text
candidate_id
chunk_id
damage_level
profile_id
ngram_order
dictionary_cut
phrase_id
phrase_count
phrase_log_count
phrase_token_length
word_lengths
word_hds
total_phrase_hd
max_word_hd
mean_word_hd
normalised_phrase_hd
hit_start
hit_end
```

---

## 12. Feature definitions

Features are grouped by:

- damage level
- profile id
- dictionary cut
- n-gram order
- phrase length bucket
- weighting mode

### 12.1 Core chunk features

For each chunk:

```text
phrase_hit_count
unique_phrase_hit_count
binary_phrase_presence
weighted_hit_sum
max_phrase_weight
mean_phrase_weight
token_coverage
opportunity_count
hit_rate
weighted_hit_rate
unique_phrase_rate
mean_total_phrase_hd
min_total_phrase_hd
mean_normalised_phrase_hd
best_normalised_phrase_hd
```

### 12.2 Diagnostic chunk features

```text
nonoverlap_phrase_hit_count
nonoverlap_weighted_hit_sum
positive_span_count
positive_span_fraction
best_phrase_order
best_phrase_length
best_phrase_total_hd
```

Non-overlap features are diagnostic unless implemented exactly and tested.

### 12.3 Removed feature types

Do not use:

```text
top_k_weighted_hit_sum
top_k_log_count
capped_hit_sum
capped_order_score
best_N_phrase_score
```

### 12.4 Weighting modes

Core:

```text
unweighted
binary_presence
log_count_weighted
```

Diagnostic:

```text
max_count_weighted
sum_count_weighted
```

If assets are sample-mode, unweighted and binary features must be treated as first-class. Count weighting may be misleading in sample mode and must be labelled accordingly.

---

## 13. Opportunity count

The spec must define opportunity count before coding.

Approved v1 definition:

For a given chunk, profile, order, and cut:

```text
opportunity_count = number of candidate start offsets at which at least one phrase in the active phrase index could fit within the chunk length and profile length limits
```

This is a placement opportunity count, not a word-hit count.

If later implementation uses anchors internally, anchor attempts must be reported separately as backend diagnostics, not as the primary opportunity denominator.

Required counters:

```text
candidate_tokens_scanned
candidate_start_offsets_considered
phrase_entries_considered
phrase_verification_attempts
phrase_verification_passes
phrase_hits
opportunity_count
```

---

## 14. Candidate aggregation

Each candidate has two 500-token chunks where available.

For each chunk feature, compute candidate-level values:

```text
chunk0_value
chunk1_value
mean_chunk_value
max_chunk_value
min_chunk_value
positive_chunk_count
positive_chunk_fraction
```

Primary v1 aggregation:

```text
mean_chunk_value
```

Diagnostic aggregation:

```text
max_chunk_value
positive_chunk_fraction
```

Because the text may be 20% to 50% damaged, max and positive-chunk diagnostics are important. A good candidate may have sparse phrase islands.

---

## 15. Score families

All score families are transparent and fixed before full reporting.

### H0 — current scorer baseline

Existing current score preference.

### H1 — normal P1 order-specific

Normal cut, profile P1, orders reported separately:

```text
H1_2gram
H1_3gram
H1_4gram
```

### H2 — strict P1 order-specific

Strict cut, profile P1, orders reported separately.

### H3 — normal P1 combined

Mean of order-normalised scores for orders 2, 3, and 4.

No caps.

### H4 — normal P2 combined

Mean of order-normalised scores for orders 2, 3, and 4 using conservative P2.

No caps.

### H5 — strict P2 combined

Strict equivalent of H4.

### H6 — normal plus strict confirmation

Normal P2 support with a separate strict confirmation diagnostic.

Strict support must be reported separately as well as combined.

### H7 — long phrase support

Profiles P3 and P4, orders 3 and 4 only.

### H8 — word-Hamming analogue

Profile P1:

```text
phrase_total_token_length >= 7
total_phrase_hd <= 2
```

### H9 — low-damage support

Exact plus conservative damaged phrase evidence.

Use P0 and P2.

### H10 — word-Hamming plus n-gram coherence

Combine the approved word-Hamming row with n-gram coherence.

The initial named word-Hamming row should be verified from the current repo/results before coding. The draft candidate is:

```text
normal length 7 HD2 exact_count_norm
```

Do not hard-code this until verified.

### H11 — S5 plus n-gram coherence

Use the approved S5 word-Hamming signal plus n-gram coherence.

The exact S5 row name must be verified from current files before coding.

### H12 — conservative support rule

Apply only when both:

- word-Hamming margin exceeds fixed threshold
- n-gram coherence margin exceeds fixed threshold

Threshold sweep is allowed as reporting, not as fitted production selection.

### H13 — 5-gram diagnostic

Profile P5 only.

Diagnostic, not core.

---

## 16. Damage-level reporting

Every score family must be reported by damage level:

- 20%
- 30%
- 40%
- 50%

Required comparisons:

```text
20_vs_30
30_vs_40
40_vs_50
20_to_50_trend
```

Readout questions:

1. Does the signal degrade smoothly with damage?
2. Does any profile only work at low damage?
3. Does any profile remain useful at 50% damage?
4. Does strict collapse earlier than normal?
5. Do longer phrase profiles survive better or worse at high damage?
6. Is the n-gram layer still useful after word-Hamming prefiltering?

---

## 17. Hard-pair evaluation

Evaluate on all hard pairs after pilot gates pass.

For each score family:

```text
truth_better_preference_count
truth_better_preference_rate
95pct_confidence_interval
rescues
breaks
net_rescues
mean_gap
median_gap
gap_q05
gap_q25
gap_q75
gap_q95
```

Split by:

```text
damage_level
current scorer correct
current scorer misranked
candidate label
source family, if available
profile_id
dictionary_cut
ngram_order
```

### 17.1 Margin sweep

Thresholds:

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

```text
applied_count
rescues
breaks
net
precision_of_applied_overrides
misrank_recall
```

### 17.2 Correlation

Compute correlations with:

```text
current score margin
Panel A margin
approved word-Hamming margin
S5 margin, if verified
coherence_proxy_v1 margin
C7 proxy combined margin, if verified
exact filtered n-gram scanner v1
```

Any row names copied from older reports must be verified against current local files before coding.

---

## 18. Comparison to prior evidence

The report must compare against:

```text
Panel A baseline
approved word-Hamming scorer row
S5_local_null_positive_selected, if still current
normal length 7 HD2 exact_count_norm, if still current
coherence_proxy_v1
C7_len7_hd2_exact_support_plus_coherence, if still current
C8_span_plus_coherence_conservative, if still current
exact filtered n-gram scanner v1
```

Main comparison questions:

1. Does n-gram Hamming beat exact n-gram scanning?
2. Does it match or improve on proxy coherence?
3. Does it preserve word-Hamming rescues?
4. Does it suppress word-Hamming breaks?
5. Does it remain useful at 50% damage?
6. Does it add information independent of the current scorer?

---

## 19. Required implementation files

Proposed target files, pending repo verification:

### Planning file

```text
planning/projects/no_wli/20_active_plans/
  phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md
```

Purpose:

- main active plan
- approved scorer contract
- acceptance checklist

### Asset validation script

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  validate_phaseB_ngram_hamming_assets_v1.py
```

Purpose:

- validate filtered n-gram assets before scoring

### Phrase index builder

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  build_phaseB_ngram_hamming_phrase_index_v1.py
```

Purpose:

- build lookup index from filtered n-gram assets

### Python reference implementation

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  reference_phaseB_ngram_hamming_matcher_v1.py
```

Purpose:

- tiny, clear, slow reference matcher for tests

### Backend wrapper / scorer runner

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  run_phaseB_ngram_hamming_pilot_v1.py
```

Purpose:

- small exact pilot on damaged candidates

### Hard-pair report

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  run_phaseB_ngram_hamming_hard_pair_report_v1.py
```

Purpose:

- full hard-pair evaluation after gates pass

### Tests

```text
tests/tools/test_phaseB_ngram_hamming_coherence_v1.py
```

Purpose:

- lock the scorer contract before full runs

The actual C++ and pybind file paths must be chosen after inspecting the repo ZIP.

---

## 20. Asset validation

### 20.1 Goal

Prove that n-gram assets are usable before scoring.

### 20.2 Checks

For each:

```text
direction: fwd, rev
dictionary_cut: strict, normal
ngram_order: 2, 3, 4, 5
```

Report:

```text
row_count
unique_phrase_count
unique_word_sequence_count
unique_rune_token_ids_sequence_count
duplicate_encoded_sequence_count
phrase_token_length_quantiles
word_length_pattern_counts
count_quantiles
log_count_quantiles
top_phrases_by_count
top_examples_by_order_cut
missing_rune_token_ids_rows
invalid_token_values
empty_token_sequences
sample_or_full_mode
```

### 20.3 Required outputs

```text
config.json
ngram_asset_manifest.json
ngram_asset_validation_summary.json
ngram_asset_counts_by_order.csv
ngram_asset_word_length_patterns.csv
ngram_asset_token_length_quantiles.csv
ngram_asset_duplicate_report.csv
ngram_asset_top_examples.csv
readout.md
```

### 20.4 Acceptance

Do not proceed unless:

- `rune_token_ids` is present
- FWD assets are present
- strict and normal are present
- orders 2, 3, and 4 are present
- asset mode is clearly recorded
- duplicate handling policy is recorded
- token values are valid
- empty token sequences are rejected

---

## 21. Backend diagnostics

The C++ backend must report:

```text
candidate_tokens_scanned
candidate_start_offsets_considered
phrase_entries_considered
phrase_verification_attempts
phrase_verification_passes
phrase_hits
unique_phrase_hits
runtime_ms
memory_estimate_bytes, if available
```

If the run fails, it must report:

```text
requested_profile
loaded_assets
candidate_subset
damage_level
last_completed_stage
failure_reason
```

Failure is better than silent narrowing.

---

## 22. Required outputs

Output folder:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  phaseB_ngram_hamming_hard_pair_report_v1/
```

Required files:

```text
config.json
input_manifest.json
damage_manifest.json
ngram_asset_manifest.json
phrase_index_manifest.json
backend_manifest.json
score_definition_manifest.json

candidate_ngram_hamming_chunk_features.csv.gz
candidate_ngram_hamming_candidate_features.csv.gz
candidate_ngram_hamming_debug_examples.jsonl.gz

score_family_pairwise_summary.csv
score_family_margin_sweep.csv
pairwise_score_gaps.csv.gz
correlation_summary.csv

damage_level_summary.csv
ngram_order_summary.csv
dictionary_cut_summary.csv
profile_summary.csv
phrase_length_bucket_summary.csv
weighting_mode_summary.csv

proxy_vs_ngram_hamming_comparison.csv
word_hamming_vs_ngram_hamming_comparison.csv
top_ngram_hamming_rescues.csv
top_ngram_hamming_breaks.csv
top_ngram_hamming_false_positives.csv
top_ngram_hamming_false_negatives.csv

readout.md
```

---

## 23. Readout requirements

`readout.md` must answer:

1. Was this sample or full n-gram asset mode?
2. Which damage levels were tested?
3. Were the damage profiles reused from the word-Hamming scorer?
4. How many phrase assets were used by order/cut/profile?
5. How many phrase verification attempts were made?
6. How many phrase Hamming hits were found?
7. Were any scoring hits dropped? The required answer is no.
8. Did any requested profile fail? If yes, why?
9. Which order helped most: 2, 3, 4, diagnostic 5?
10. Does strict add precision?
11. Does normal dominate?
12. Which phrase eligibility profile helped most?
13. Does n-gram Hamming beat exact n-gram scanning?
14. Does it beat or match proxy coherence?
15. Does it preserve word-Hamming rescues?
16. Does it suppress word-Hamming breaks?
17. Does any conservative rule give positive net with low breaks?
18. Is it independent from the current scorer or strongly correlated?
19. Does performance degrade smoothly from 20% to 50% damage?
20. Is there useful signal at 50% damage?

---

## 24. Acceptance gates

### Gate 1 — asset validation

Pass asset validation before scoring.

### Gate 2 — Python reference tests

Build tiny examples and verify:

- exact phrase hit
- one damaged word
- multiple damaged words
- below minimum phrase length rejected
- above total HD rejected
- above per-word HD rejected
- duplicate phrase collapse
- FWD/REV separation
- `rune_key_hex` rejection
- debug example limits do not affect scores

### Gate 3 — backend parity

C++ backend must match the Python reference on small fixed examples.

### Gate 4 — exact no-cap pilot

Run a small exact pilot.

Suggested first pilot:

```text
candidates: 10
chunks: 20
direction: FWD
cuts: normal
orders: 2, 3
profiles: P0, P1, P2
damage_levels: 20, 30, 40, 50
```

Pass if:

- phrase hits are non-zero for at least one non-exact profile
- all eligible hits are counted
- no scoring caps are used
- runtime is recorded
- repeat run is deterministic
- debug examples are clearly labelled as examples only

### Gate 5 — expanded pilot

Add:

- strict
- order 4
- P3
- P4

Pass if:

- exact counting still completes
- no profile silently changes
- no hits are dropped
- damage-level trends are inspectable

### Gate 6 — full hard-pair report

Run full 604-candidate / 2594-pair report only after the earlier gates pass.

### Gate 7 — review before production weighting

No production ranking change before review.

---

## 25. Tests

Minimum tests:

```text
test_asset_validation_requires_rune_token_ids
test_rune_key_hex_is_rejected_for_scanning
test_phrase_index_deduplicates_token_sequences
test_word_structured_phrase_hit_exact
test_word_structured_phrase_hit_with_damage
test_joined_phrase_and_word_structured_phrase_can_differ
test_phrase_min_length_rule
test_total_phrase_hd_rule
test_max_word_hd_rule
test_damage_level_manifest_is_written
test_candidate_two_chunk_aggregation
test_fwd_and_rev_cannot_be_combined
test_score_manifest_records_asset_mode
test_debug_example_limit_does_not_change_scores
test_backend_matches_python_reference
test_repeated_run_is_deterministic
test_impossible_profile_fails_loudly
```

---

## 26. Main risks

### Risk 1 — configuration too broad

Some profiles may be too large to evaluate exactly.

Mitigation:

- small pilots first
- exact opportunity counts
- exact attempt counts
- runtime diagnostics
- fail loudly if too large
- narrow the scientific profile rather than dropping hits

### Risk 2 — short phrase false positives

2-grams may hit too often.

Mitigation:

- report orders separately
- require phrase length thresholds
- use 2-grams as support, not sole driver
- compare P1 and P2

### Risk 3 — sample asset weakness

Sample assets may not cover enough phrases.

Mitigation:

- record sample/full mode
- keep unweighted and binary features first-class
- do not over-interpret count weighting in sample mode

### Risk 4 — overfitting hard pairs

Mitigation:

- fixed profiles
- report-only first
- no fitted weights in v1
- later held-out/source-family split

### Risk 5 — silent behaviour changes

Mitigation:

- full score manifests
- explicit failure manifests
- tests for impossible profiles
- no fallback from word-structured to joined matching

### Risk 6 — existing backend assumptions leaking in

Mitigation:

- independent backend
- existing backend used only as guide
- reference tests define behaviour

---

## 27. No silent score changes

The scorer must never silently change the requested scoring profile.

It must not:

- drop eligible phrase hits
- switch from full assets to sample assets
- switch from strict to normal
- switch from FWD to REV
- use `rune_key_hex` when `rune_token_ids` was requested
- disable an n-gram order because runtime is high
- replace exact counting with top-k examples
- change HD thresholds inside a run
- change phrase length thresholds inside a run
- change damage level inside a run

If the requested profile cannot be evaluated, the run must fail with a clear error and write a failure manifest.

---

## 28. Immediate next task

Do not start with the full hard-pair report.

Next task sequence:

1. Inspect local repo ZIP.
2. Identify existing word/span-Hamming backend build pattern.
3. Identify n-gram asset schema.
4. Write the planning file.
5. Build asset validation.
6. Build phrase index builder.
7. Build tiny Python reference matcher.
8. Add reference tests.
9. Build independent C++ backend.
10. Add C++ parity tests.
11. Run exact no-cap pilot.
12. Only then run full hard-pair report.

---

## 29. What remains unverified until repo inspection

The following must not be hard-coded until local repo files are inspected:

- exact C++ backend file paths
- pybind module name
- existing word-Hamming row names
- exact S5 row name
- current hard-pair input file names
- current n-gram asset file names
- actual schema for filtered n-gram assets
- exact damage model config names
- test helper names
- build helper names

No guessing.
