# Dev instruction pack: next phase after Lane 1 closure

## Objective

Lane 1 is now accepted as the full raw order-2/order-3 FWD normal/strict language-asset foundation.

The next phase is **Lane 2 gated diagnostic scoring evidence**.

Do not treat this as production scoring. Do not change production ranking. Do not promote bridge profiles into canonical scorer profiles. The aim is to generate controlled evidence that tells us whether the n-gram Hamming phrase-coherence scorer is worth carrying forward into report-only scoring, then later into tie-break or bounded-override evaluation.

## Where we are

Current accepted state:

```text
Lane 1:
  full raw order-2/order-3 FWD normal/strict language asset closed
  permanent asset manifest exists
  provenance review passed
  phrase/word length distributions present
  asset validation passed

Lane 2:
  preparation exists
  readiness machinery exists
  launch has remained blocked
  no real bridge scan has started
  no production scorer change has been made
```

This means we can now move from “asset/provenance readiness” to “diagnostic scoring evidence”.

## How far we are from scoring

We are close to **report-only scoring evidence**, but not yet close to **production scoring**.

Approximate state:

```text
Done:
  language asset foundation
  provenance checks
  profile metadata discipline
  normal/strict separation discipline
  no-production-change guard
  bridge preparation

Next:
  controlled diagnostic scans
  damaged-positive evaluation
  matched null evaluation
  cluster/concentration analysis
  score-candidate-vs-diagnostic separation evidence

Later:
  report-only scorer integration
  offline tie-break evaluation
  offline bounded-override evaluation
  order-4 sizing/build decision
  production ranking decision
```

The next aim is not to “make the scorer win” immediately. The next aim is to prove whether the proposed evidence behaves sensibly.

## Phase name

Use this phase name in plans and manifests:

```text
Phase B Lane 2: Gated Diagnostic Scoring Evidence
```

Short label:

```text
phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1
```

## Main question for this phase

This phase must answer:

```text
When candidate text contains real damaged phrase evidence, do the n-gram Hamming profiles produce stable, clustered, positive support above matched nulls?

And when candidate text is random, shuffled, badly damaged, or unrelated, do those same profiles stay low, sparse, or clearly flagged as fragile/noisy?
```

## What this phase is allowed to prove

This phase may prove:

```text
1. The Lane 2 bridge scanner can run against the permanent Lane 1 language asset.
2. Profile metadata is preserved correctly.
3. Normal and strict cuts remain separate.
4. Diagnostic and score-candidate outputs remain separate.
5. Damaged positive text produces stronger clustered evidence than matched nulls.
6. Order-3 evidence is more useful than order-2 evidence, or not.
7. Order-2 evidence is inflated, concentrated, or unsafe, or not.
8. The current cluster definitions and summary fields are sufficient for offline review, or not.
9. The next stage should either:
   a. proceed to report-only scorer integration,
   b. revise cluster/report definitions,
   c. build order 4,
   d. or stop/rethink the scorer.
```

## What this phase is not allowed to prove

This phase must not claim:

```text
1. Production ranking can change.
2. Bridge profiles are canonical scorer profiles.
3. Order 2 is score-bearing.
4. Counts/log-counts are score weights.
5. Raw hit volume is a score.
6. Order 4 is unnecessary.
7. Order 5 diagnostics are unnecessary.
8. S34C_main has been fully tested, because the current Lane 1 asset does not include order 4.
9. A broad candidate search is safe without a later gate.
```

## Core design rule

Keep this distinction everywhere:

```text
destination:
  the research-led phrase-coherence scorer

stage:
  the current partial implementation step

probe:
  a diagnostic run whose output may or may not become useful
```

Lane 2 is a stage/probe.

It is not the final scorer.

## Required profiles for this phase

Use the existing bridge diagnostics and canonical labels carefully.

For the current order-2/order-3 asset, this phase can run:

```text
BR_O2_soft
BR_O2_len8_conservative
BR_O2_len10_long
BR_O3_soft
BR_O3_conservative
```

Where applicable, map them explicitly to the canonical ladder:

```text
BR_O2_soft:
  canonical_profile_id: B2R
  score_authority: diagnostic_only

BR_O3_soft normal:
  canonical_profile_id: N3S_diag
  score_authority: diagnostic_only

BR_O3_conservative normal:
  canonical_profile_id: N3C
  score_authority: blocked_bridge_candidate or score_candidate_view_for_offline_review only

BR_O3_soft strict:
  canonical_profile_id: none
  score_authority: diagnostic_only

BR_O3_conservative strict:
  canonical_profile_id: none
  score_authority: blocked_bridge_candidate
  note: not S3W
```

Do not silently label `BR_O3_conservative strict` as `S3W`.

Do not silently use any order-2 output as score-bearing.

## Data plan

Yes, use damaged text from books, but do it as a controlled evaluation corpus.

Use repo-safe text only.

Preferred sources:

```text
1. Public-domain text fixtures.
2. Short hand-made synthetic phrase passages.
3. Existing repo-safe sample text if already present.
4. User-supplied private local text only if it is not committed into the repo.
```

Do not commit large copyrighted book text into the repo.

If using public-domain book text, store only what is needed for reproducible tests and document the source/licence in the manifest.

## Evaluation corpus structure

Create a small deterministic corpus first.

Recommended permanent or generated location:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/eval_corpora/ngram_hamming_lane2_v1/
```

If the corpus is committed:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/eval_corpora/ngram_hamming_lane2_v1/
  README.md
  corpus_manifest.json
  positive_passages.jsonl
  null_passages.jsonl
  damaged_cases.jsonl
```

If the corpus is generated locally:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_lane2_eval_corpus_v1/
  corpus_manifest.json
  positive_passages.jsonl
  null_passages.jsonl
  damaged_cases.jsonl
```

The manifest must say whether text is committed, generated, public-domain, synthetic, or private-local.

## Required corpus families

Create these case families:

```text
positive_clean:
  real phrase-like text, no damage

positive_damaged_20:
  same passages with deterministic 20% token damage

positive_damaged_35:
  same passages with deterministic 35% token damage

positive_damaged_50:
  same passages with deterministic 50% token damage

matched_random_same_length:
  random token streams with same token lengths as positives

matched_shuffle_same_tokens:
  same tokens as positives, shuffled order

matched_wordlike_wrong_order:
  local word-like spans but phrase order broken

hard_negative_book_text:
  coherent text from unrelated passages, not expected to match target phrase evidence

boundary_cases:
  very short candidates
  candidates below min phrase token length
  candidates with repeated tokens
  candidates with one dominant repeated phrase-like region
```

The 20/35/50 damage tiers are important because the intended scorer is meant to survive serious damage, not just tiny edits.

## Deterministic damage rules

Add a deterministic damage generator.

Required manifest fields:

```text
damage_mode
damage_rate
seed
alphabet_size
input_token_count
damaged_token_count
damage_positions_sha256
source_case_id
```

Damage should support at least:

```text
substitute:
  replace selected tokens with different valid tokens

delete:
  remove selected tokens

mixed_substitute_delete:
  deterministic mix, but keep the exact policy recorded
```

For the first phase, prefer substitution-only first because phrase Hamming is easier to interpret without alignment shifts.

Deletion/insertion damage can be a later extension unless the existing scanner already handles it safely.

## First diagnostic run scope

Start with a deliberately small post-review microbatch, not a broad scan.

Recommended first run:

```text
profiles:
  BR_O2_soft
  BR_O2_len8_conservative
  BR_O3_soft
  BR_O3_conservative

cuts:
  normal
  strict

direction:
  fwd

case families:
  positive_clean
  positive_damaged_20
  positive_damaged_35
  positive_damaged_50
  matched_random_same_length
  matched_shuffle_same_tokens
  matched_wordlike_wrong_order

candidate count:
  small but representative
```

This is a diagnostic launch, not production scoring.

## Outputs required from the diagnostic scanner

Each run must emit:

```text
run_manifest.json
profile_manifest_rows.csv
candidate_profile_summary_rows.csv
candidate_cluster_summary_rows.csv
hit_rows.csv or sampled_hit_rows.csv
null_comparison_rows.csv
concentration_rows.csv
damage_tier_summary_rows.csv
review_readout.md
```

If full hit rows are too large, emit full summary rows plus a bounded, clearly labelled hit sample. Do not silently cap without saying so.

## Required fields in `run_manifest.json`

Include:

```json
{
  "phase": "phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1",
  "run_scope": "post_review_microbatch",
  "run_authority": "diagnostic_only",
  "production_scorer_change": false,
  "real_candidate_scan_started": false,
  "uses_permanent_lane1_asset": true,
  "lane1_asset_id": "phaseB_ngram_hamming_full_raw_v1",
  "orders": [2, 3],
  "cuts": ["normal", "strict"],
  "directions": ["fwd"],
  "omitted_orders": [4, 5],
  "why_omitted": {
    "4": "not present in current Lane 1 asset tranche",
    "5": "future diagnostic only"
  },
  "unsafe_interpretations": [
    "does not approve production ranking",
    "does not prove order 4 unnecessary",
    "does not promote order 2 to score-bearing",
    "does not use count/log-count weighting"
  ]
}
```

## Cluster evidence rules

The scanner must keep these separate:

```text
all-profile diagnostic clusters
score-candidate-view clusters
diagnostic-only profile summaries
score-candidate-view summaries
```

Diagnostic-only profiles must not shape score-candidate summaries unless the output is explicitly labelled:

```text
cluster_scope = all_profiles_diagnostic
```

For candidate scoring evidence, prefer cluster support over raw hit count.

Required summary fields:

```text
candidate_id
case_family
damage_rate
profile_id
profile_origin
canonical_profile_id
parameter_status
score_authority
cut
direction
ngram_order
cluster_scope
cluster_count
exact_cluster_count
hit_count
exact_hit_count
dominant_cluster_hit_fraction
dominant_phrase_hit_fraction
distinct_phrase_count
distinct_start_count
best_hit_signature
```

Raw hit count must remain diagnostic.

## Matched null comparison

Every positive case should have matched null cases.

At minimum:

```text
same token length
same alphabet
same damage rate
same number of candidates
same profile set
same cut/direction set
```

For each profile/cut/direction/damage tier, emit:

```text
positive_cluster_count_median
null_cluster_count_median
positive_exact_cluster_count_median
null_exact_cluster_count_median
positive_hit_count_median
null_hit_count_median
lift_cluster_count
lift_exact_cluster_count
overlap_rate
false_positive_rate_at_positive_threshold
```

The key question is not “does a positive have hits?”

The key question is:

```text
Does the positive produce clustered support above matched nulls?
```

## Concentration checks

Order-2 evidence is especially risky.

For every candidate/profile, compute:

```text
dominant_phrase_hit_fraction
dominant_cluster_hit_fraction
dominant_start_hit_fraction
top_5_phrase_hit_fraction
top_5_cluster_hit_fraction
```

Flag unsafe evidence if:

```text
one phrase dominates
one start position dominates
one cluster dominates
order-2 support is high but order-3 support is absent
normal support exists but strict support collapses completely
```

Do not decide thresholds permanently yet. Emit the numbers and apply conservative warning labels.

## First pass acceptance criteria

The first diagnostic microbatch is successful if:

```text
1. It runs deterministically.
2. It emits all required manifests and summary rows.
3. It keeps normal/strict separate.
4. It keeps diagnostic and score-candidate views separate.
5. It records omitted order 4/order 5 clearly.
6. It records that production scoring is unchanged.
7. Positive damaged cases show measurable cluster support above matched nulls in at least some order-3 profiles.
8. Order-2 inflation, if present, is visible rather than hidden.
9. Bad/null cases do not look indistinguishable from positives without warnings.
```

It does not need to produce a perfect final score yet.

## Review gate after this phase

Use one substantial review gate after the first complete diagnostic evidence pack.

Do not ask for review after every small implementation step.

The review pack should be:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_2026-06-XX.zip
```

It should include:

```text
10_context/
  current state
  active runbook
  v3.2 canon spec
  Lane 1 closure decision
  Lane 2 diagnostic plan

20_component_outputs/
  corpus manifest
  diagnostic run manifest
  profile manifest rows
  candidate summaries
  cluster summaries
  null comparison rows
  concentration rows
  damage tier summaries
  readout

30_source/
  changed scanner/evaluation/corpus source files
  ngram_hamming reference/bridge/backend files if touched

40_tests/
  focused tests

50_review_questions/
  explicit answers to the bridge acceptance questions
```

The pack status may be:

```text
packed_review_ready
packed_with_blocks
```

## Required tests

Add tests for behaviour, not just file existence.

Required test areas:

```text
1. Deterministic damage generation:
   same seed gives same damage positions and same damaged tokens

2. Different seed changes damage:
   not required for scoring, but useful to prove seed is active

3. Damage manifest:
   records rate, seed, token count, damage count, and position hash

4. Profile manifest validation:
   rejects missing profile_origin
   rejects missing canonical_profile_id where required
   rejects missing score_authority
   rejects silent S34C length broadening
   rejects BR_O3_conservative_strict being labelled S3W

5. Normal/strict separation:
   normal and strict outputs cannot collapse into one unlabelled row

6. Cluster scope separation:
   all-profile diagnostic summaries and score-candidate-view summaries cannot be mixed

7. Diagnostic-only exclusion:
   diagnostic-only profiles cannot affect score-candidate summaries

8. Null matching:
   every positive case must have matched nulls for the same length/damage tier/profile scope

9. Launch safety:
   production_scorer_change must remain false
   broad scan approval must remain explicit
   report-only output must not alter production rank

10. Stable ordering:
   output rows must be sorted deterministically
```

## Planning document updates

Update:

```text
planning/projects/no_wli/00_CURRENT_STATE.md
planning/projects/no_wli/04_ACTIVE_RUNBOOK.md
planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md
```

Add a new section:

```text
Lane 2 gated diagnostic scoring evidence
```

Required wording:

```text
Lane 1 is closed for the order-2/order-3 FWD normal/strict language asset tranche.

Lane 2 may now run a small post-review diagnostic microbatch.

This is not production scoring.

This is not a production ranking change.

This is not a broad candidate search.

This is an evidence run over controlled positives, deterministic damage tiers, and matched nulls.

The goal is to decide whether the n-gram Hamming phrase-coherence evidence is strong enough to proceed to report-only scorer integration.
```

Also add:

```text
Order 4 remains part of the canonical scorer plan but is outside the current Lane 1 asset tranche.

Order 5 remains optional diagnostic future scope.

S34C_main cannot be fully tested until order 4 is available.

Counts/log-counts remain diagnostic only.

Raw hit counts remain diagnostic only.

Order-2 support remains diagnostic unless it clears a later higher proof burden.
```

## Next substantial review gate

The next review should happen after devs produce a complete Lane 2 diagnostic evidence pack with:

```text
1. deterministic damaged-positive corpus
2. matched null corpus
3. diagnostic scanner output
4. cluster and concentration summaries
5. damage-tier summaries
6. tests
7. updated planning docs
8. explicit no-production-change records
```

Do not require review for every small internal edit unless the devs touch:

```text
production ranking
score authority semantics
profile thresholds
normal/strict separation
cluster scope semantics
asset identity
fallback behaviour
deterministic damage generation
```

Those are high-risk and should trigger review earlier.

## Decision after the next review

At the next review, we should decide one of these:

```text
A. Proceed to report-only scorer integration.
B. Revise cluster definitions and rerun diagnostics.
C. Build order 4 language assets before further scoring work.
D. Keep Lane 2 diagnostic-only and collect more evidence.
E. Stop or redesign if positives and nulls do not separate.
```

No production scoring decision should be made at that review unless the evidence is unexpectedly strong and the production safety machinery has also been built and reviewed.
