# RDP N-Gram Scorer v2 Response Review - 2026-05-30

Status: review response draft

Responds to:

- `planning/temp_files/ngram_scorer_june_2026_docs/v2 .txt`

Companion context:

- `planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_scorer_investigation_context_review_2026-05-30.md`
- `planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_scorer_discussion_brief_2026-05-30.md`

Purpose: provide detailed dev/reviewer responses to the v2 coordinated spec,
identify agreement points, call out amendments, answer the open questions, and
prepare the next implementation slice while the full raw order-2/order-3 shard
build continues.

## Executive Response

I agree with the v2 direction.

The v2 draft fixes the main interpretation risk correctly:

```text
order-2 is an early lead and instrumentation slice;
order-3 is the first serious phrase-coherence test;
order-4 is likely confirmation-grade;
order-5 remains diagnostic unless proven otherwise.
```

That is the right framing. It preserves the research architecture without
discarding the only clearly active empirical signal seen so far.

My main recommended amendment is to make the next implementation tranche
explicitly two-lane:

```text
Lane 1: finish and review the full raw order-2/order-3 data plane.
Lane 2: prepare, but do not launch broadly, the report-only order-2/order-3
        cluster diagnostic pack.
```

This lets implementation preparation continue while the shard build runs, but
keeps the evidence gate intact. The diagnostic pack should be ready to execute
once full raw provenance passes review.

## Current Live Context

As of the latest local check during this response:

```text
python process = running
python pid = 7348
active build = phaseB_ngram_hamming_full_raw_asset_shards_v1
scope = fwd, normal/strict, orders 2 and 3, full raw
latest observed shard manifests = 503
latest observed pass shard manifests = 503
latest active order = 3
latest observed shard = order 3, shard 304
latest observed log elapsed = about 5h41m
latest observed ETA by completed bytes = about 17h50m
```

This supports the v2 statement that the current work is still data-plane work,
not scorer promotion work.

## High-Level Agreement

I agree with these v2 conclusions without reservation:

- Exact joined n-gram scanning is closed as a valid negative for damaged no-WLI
  streams.
- Word-structured phrase Hamming is the correct semantic direction.
- Infrastructure readiness is not scorer readiness.
- Current evidence is candidate-comparability and implementation evidence, not
  controlled damage-ladder proof.
- Order-2 should not become the final scorer direction just because it produced
  the first visible signal.
- Order-2 evidence should not be ignored.
- Order-3 deserves a fair full-raw test before the scorer center is decided.
- Order-4 should not be launched until order-2/order-3 provenance and diagnostic
  results are reviewed.
- Raw hit count must not be the final score.
- Direct additive fusion is forbidden for this tranche.
- Count/log-count weighting should remain diagnostic.
- Normal and strict must remain separate.
- FWD and REV must remain separate.
- Exact hits should be visible without becoming a separate profile ladder.
- Matched nulls are required before profile promotion.

## Main Amendment: Separate "Prepare" From "Run"

The user intent is sensible: finish the current run, but use the time while it
runs to prepare implementation after discussion and agreement.

I recommend recording that distinction as a rule:

```text
Implementation preparation may proceed while the full raw shard build runs.
Broad scanning, profile promotion, full hard-pair reporting, and expansion to
new orders must wait for full raw provenance review.
```

Preparation work can include:

- drafting the order-2/order-3 cluster diagnostic plan;
- defining output schemas;
- defining hardcoded profile manifests;
- writing review checklists;
- identifying existing input files;
- designing deterministic candidate/pair selection;
- preparing tests for cluster semantics and support tuples.

Preparation work should not include:

- launching a broad order-2/order-3 diagnostic scan before provenance review;
- starting order-4 or order-5 asset work;
- changing production scoring;
- adding P2 to current score;
- calling the existing comparability results controlled damage results.

## Response By V2 Section

### Section 1: One-Sentence Direction

Agree.

The formulation:

```text
research-led architecture
implementation-tested machinery
evidence-gated profile promotion
no production scoring change yet
```

is exactly the right coordination phrase. It prevents both overfitting to the
first order-2 signal and ignoring that signal.

Suggested small addition:

```text
data-plane provenance before broad interpretation
```

The current blocker is not just "more evidence"; it is specifically full raw
asset/provenance completion for order 2 and order 3.

### Section 2: What This Spec Is Trying To Fix

Agree.

The two bad interpretations are real. The second one is especially important:
if we decide in advance that 3/4-grams must win, we could miss a practical
shorter-order support feature. But the first one is the more immediate risk
because order-2 currently has visible hits and could seduce us into premature
promotion.

Recommended wording:

```text
Order-2 may become a useful auxiliary support or diagnostic feature, but it
should carry a higher burden of null/concentration proof than order-3 or order-4.
```

### Section 3: Current State

Agree, with one live update:

The full raw shard build is actively processing order-3 data and has already
emitted hundreds of passing shard manifests. It is not complete, but the
resumable data-plane approach is working in the sense that partial shard outputs
are being written and can be counted.

I would keep the scientific-readiness wording strict:

```text
not controlled damage-ladder proof
not full raw/provenance-grade proof
not production ranking proof
```

That exact phrase should remain in the active discussion pack.

### Section 4: Research-Led Architecture To Preserve

Agree.

One implementation nuance: phrase identity and scan identity should be named
separately everywhere.

Recommended terms:

```text
canonical_phrase_identity =
  direction + dictionary_cut + ngram_order + canonical word_token_ids

scan_compatibility_payload =
  flattened rune_token_ids and rune_lengths
```

This helps avoid accidental deduplication by joined tokens later.

### Section 5: Handling Variable N-Gram Order And Phrase Length

Strongly agree.

This is one of the most important parts of v2. The earlier order debate can be
misleading because order is word count, not evidence length. A long order-2 hit
may be better evidence than a very short order-3 hit, depending on length,
threshold, cut, and mismatch distribution.

Recommended addition:

```text
All order comparisons should be stratified by phrase token length bucket.
```

Minimum suggested buckets for diagnostics:

```text
7-9
10-12
13-16
17+
```

These buckets should not necessarily become scoring buckets; they are needed to
interpret whether order effects are really length effects.

### Section 6: Counts And Log-Counts

Agree.

Counts/log-counts should be preserved in hit records and summaries, but not
score-bearing.

Important detail: once duplicate collapse metadata is available, preserve:

```text
count
sum_count
max_count
log_count
max_log_count
phrase_count
duplicate_row_count
top_latin_ngram_for_max_count
```

But for v1 scorer comparison:

```text
all count-derived fields = diagnostics only
```

### Section 7: Cluster-Based Evidence

Agree, with one important clarification.

The v2 text says:

```text
A phrase coherence cluster is a connected component of score-bearing or
diagnostic phrase-hit intervals whose flattened token intervals overlap or
touch.
```

For the bridge pack, that is acceptable if the output clearly distinguishes:

```text
global_all_profile_cluster_id
score_candidate_cluster_id
diagnostic_only_cluster_id
```

The research implementation brief originally emphasized global clustering across
score-bearing families. In a bridge where most profiles are diagnostic, using
all diagnostic hits to form clusters could either help reveal inflation or hide
score-candidate support inside a broader diagnostic cluster.

Recommended bridge approach:

```text
Emit both:
  cluster_all_profiles_overlap_touch
  cluster_score_candidate_profiles_overlap_touch
```

Then use the all-profile cluster for diagnostics and the score-candidate cluster
for any simulated support tuple.

No production decision should depend on this until reviewed.

### Section 8: Exact Hits

Agree.

Exact hits should be fields, not a separate profile family.

Recommended additional exact diagnostics:

```text
exact_cluster_count_by_order
exact_cluster_count_by_cut
exact_best_phrase_token_length
exact_best_hit_signature
```

Exact support should remain a sanity/audit dimension unless it proves enough
coverage and precision in hard-pair ledgers.

### Section 9: Proposed Coordinated Profile Strategy

Agree.

The separation into:

```text
current instrumentation profiles
near-term order-2/order-3 bridge profiles
later intended 3/4 scorer profiles
```

is the right way to avoid locking early instrumentation into final scoring.

I recommend adding a fourth category:

```text
blocked/future profile families
```

This category should include:

- order 4 until sized and reviewed;
- order 5 until order 4 has shown reason or a separate diagnostic is approved;
- skip/gapped evidence;
- edit distance;
- count-weighted scoring;
- direct additive scorer fusion.

### Section 10: Stage A - Current Data-Plane Completion

Agree.

This should be the current operational priority:

```text
finish full raw fwd order-2/order-3 shard build
summarize provenance
build review pack
stop for review
```

No order-4 expansion should start before this. No full hard-pair report should
start before this.

If the current run fails or is interrupted, the next response should not be "try
monolithic again" or "launch the full matrix anyway". The next response should
be:

```text
extract completed shard coverage
identify failed/missing shards
resume only missing shards or fix a clear blocker
preserve partial outputs
```

### Section 11: Stage B - Order-2/Order-3 Bridge

Agree with the direction, but I recommend making Stage B explicitly
post-provenance.

Suggested gate:

```text
Stage B can be implemented in skeleton form before provenance review, but should
not run broad real candidate scans until the full raw order-2/order-3
provenance pack is reviewed.
```

Bridge profiles are sensible:

```text
O2_soft
O2_conservative
O3_soft
O3_conservative
```

Recommended profile manifest details:

| Profile | Order | Cut handling | Min length | Max total HD | Max word HD | Role |
|---|---:|---|---:|---:|---:|---|
| `O2_soft` | 2 | normal/strict separate | 7 | 2 | 2 | diagnostic |
| `O2_conservative` | 2 | normal/strict separate | 8 or 10 | 2 | 1 | bridge candidate |
| `O3_soft` | 3 | normal/strict separate | 7 | 2 | 2 | diagnostic |
| `O3_conservative` | 3 | normal/strict separate | 8 | 2 | 1 | central candidate |

Design decision needed:

```text
O2_conservative min length 8 vs 10
```

My leaning:

```text
use both as separate diagnostics initially:
  O2_conservative_len8
  O2_long_len10
```

Reason: existing P1/P2 redundancy suggests threshold differences may be
ineffective on the current assets; a length-10 order-2 diagnostic tests whether
longer two-word phrases behave more like real phrase evidence.

### Section 12: Stage C - Intended 3/4 Scorer

Agree.

This should not be production scoring yet.

The v2 draft correctly preserves:

```text
N3C
S3W
N4L
S34C
```

I agree that `S34C` min length is a real decision.

My recommendation:

```text
For first 3/4 scorer diagnostics, emit both:
  S34C_len8
  S34C_len10

Do not promote either until null/concentration and hard-pair ledgers are
reviewed.
```

If only one must be chosen before any run:

```text
choose min length 10 for the high-precision confirmation role
```

Reason: `S34C` is supposed to be the top confirmation family. Length 8 may be
useful, but it risks blurring the distinction between central coverage and
confirmation.

### Section 13: Stage D - Order-5

Agree.

Order-5 should stay diagnostic and optional. It should not be bundled into the
next tranche. The cost and likely sparsity are not justified until order-3 and
order-4 behavior are clearer.

### Section 14: Matched Nulls

Agree.

Matched nulls are necessary because the operational null is not random token
noise. It is "candidate already liked by word/span-Hamming but potentially
wrong-order or locally repetitive."

Recommended first null minimum:

```text
offset_permute_null first
periodic_decoy_null second
window_collage_null third
```

Reason:

- `offset_permute_null` is easiest to define from one candidate's anchors.
- `periodic_decoy_null` directly stress-tests the repeated-local-structure
  failure mode.
- `window_collage_null` is valuable but needs donor bucketing decisions and is
  easier to get subtly wrong.

### Section 15: Panel-Rescue Zero-Hit Audit

Strongly agree.

This should be a small explanatory audit, not a broad run.

Recommended minimal candidate set:

```text
20 panel-rescue known-better candidates already identified in the balanced/design outputs
plus matched panel-rescue known-worse counterparts if available
```

Minimum outputs:

```text
candidate_id
pair_id
role
chunk_id
span_hamming_support_present
span_hamming_best_regions
ngram_order2_hits
ngram_order3_hits_if_available
phrase_opportunity_count_by_order
best_failed_near_hit_if cheap/available
likely_no_hit_reason
```

Potential no-hit reason categories:

```text
no local word/span support in scanned chunk
local support exists but not adjacent
phrase asset coverage missing
phrase length/opportunity missing
HD too high for contiguous phrase
short-word-only evidence
candidate-source/chunk mismatch
true rescue is local lexical, not phrase-coherent
```

### Section 16: Promotion Gates

Agree.

I would make the gates explicitly profile-family-specific and mode-specific:

```text
diagnostic -> bridge-candidate -> tie-break-candidate -> bounded-override-candidate
```

Order-2 should have a special extra gate:

```text
order-2 cannot move beyond bridge-candidate unless it beats matched nulls and
does not concentrate in one phrase/local region.
```

Suggested concentration warning defaults for discussion:

```text
top_phrase_share > 0.35
median hit_to_cluster_ratio > 3
single_cluster_share > 0.50
```

These should be warnings in the bridge pack, not automatic production decisions.

### Section 17: Offline Decision Modes

Agree.

Direct additive is forbidden for this tranche.

I would also add:

```text
support_flag_only
```

This mode does not rank candidates. It simply marks candidates/pairs with
support categories:

```text
order2_support_only
order3_support_only
order2_and_order3_support
strict_support_present
exact_support_present
null_fragile_support
```

This could make human inspection easier before rank simulation.

### Section 18: Proposed Next Artefacts

Agree with all four.

I recommend ordering them as:

1. full raw order-2/order-3 provenance summary;
2. panel-rescue zero-hit audit design, possibly runnable after provenance;
3. order-2/order-3 cluster diagnostic pack;
4. matched null pilot;
5. order-4 sizing and expansion decision.

The panel-rescue audit can be designed now and may reuse existing balanced
readout outputs. It should not require waiting for order-4.

### Section 19: Red Lines

Agree.

I would add:

```text
Do not let diagnostic profiles form score-affecting clusters unless the cluster
mode explicitly says so.
```

This prevents accidental scoring contamination when many diagnostic views are
present in the same run.

### Section 20: Open Discussion Questions For Dev

Detailed answers below.

### Section 21: Recommended Position

Agree.

My version:

```text
Finish full raw order-2/order-3 data work.
Review provenance.
Prepare the order-2/order-3 bridge diagnostic implementation while the build
runs, but do not run it broadly until provenance passes.
Use cluster diagnostics and matched nulls to decide whether order-2 is only
diagnostic or has a narrow support role.
Use full order-3 results to decide whether the research architecture's intended
center becomes active.
Keep production scoring unchanged.
```

## Answers To The 12 Open Dev Questions

### 1. Do we agree that order-2 was run first mainly because it was simplest, not because it was expected to be best?

Yes.

Order-2 was the cheapest and easiest slice to get through the implementation and
runtime gates. Its positive signal proves that the machinery can find real
phrase-like evidence, but it does not prove order-2 is the correct scorer
center.

### 2. Do we agree that order-3 should be the first serious phrase-coherence test once full raw assets are ready?

Yes.

Order-3 is the first serious phrase-coherence test because it is the smallest
order that has enough word-order structure to move beyond two-word local
coincidence. It should be tested fairly against order-2 with comparable soft and
conservative profiles.

### 3. Should the next diagnostic pack compare order-2 and order-3 with matched soft and conservative profiles?

Yes.

This is the best bridge between the research plan and the active evidence.

Recommended profiles:

```text
O2_soft
O2_conservative_len8
O2_long_len10
O3_soft
O3_conservative
```

Normal and strict should be separate outputs for each.

### 4. Should the bridge use overlap-or-touch clustering exactly as proposed?

Yes as the default cluster rule.

But emit two cluster scopes:

```text
all_profile_overlap_touch_cluster
score_candidate_overlap_touch_cluster
```

The all-profile cluster is useful for inflation diagnostics. The score-candidate
cluster prevents diagnostic-only profiles from accidentally shaping a simulated
score.

### 5. Should normal and strict both be present for every bridge profile, or should strict be delayed until normal behaviour is understood?

Both should be present if full raw assets are available and runtime is
reasonable.

Reason:

- strict/normal comparison is one of the central scientific questions;
- strict may reveal precision even where normal inflates;
- delaying strict would force another pass over similar data.

But they must remain separate. Do not merge strict and normal into one score.

### 6. Should P1 and P2 both remain in the bridge, given their current redundancy, or should P1 become audit-only?

P1 should become audit/diagnostic; P2 or a P2-like conservative profile should be
the bridge candidate.

However, keep P1 in the next diagnostic pack at least once because the current
P1/P2 redundancy is itself an important finding. We need to know whether that
redundancy persists with full raw assets and order-3.

Recommended:

```text
P1/O2_soft = diagnostic
P2/O2_conservative = bridge candidate
```

### 7. What is the exact definition of "panel-rescue zero-hit audit" and how small should that audit be?

Definition:

```text
A bounded explanatory audit of candidates where span/Panel evidence indicated a
rescue opportunity but the n-gram P2/order-2 signal had zero hits.
```

Recommended size:

```text
20 panel-rescue known-better candidates from the existing balanced/design output
plus their known-worse pair counterparts where available.
```

Keep it explanatory, not a scoring run.

### 8. What minimum null work is required before saying any order-2 evidence is useful?

Minimum before order-2 can be called useful as more than instrumentation:

```text
offset_permute_null
periodic_decoy_null
cluster lift over null
top_phrase_share check
hit_to_cluster_ratio check
pair ledger check on changed or supported pairs
```

`window_collage_null` is desirable before promotion but not required for the
first bridge diagnostic.

### 9. What is the threshold for starting order-4 sizing?

Order-4 sizing should start only after:

```text
full raw order-2/order-3 provenance passes;
order-3 diagnostic readout is interpreted;
runtime/asset-size estimates are written;
the expected value of order-4 is stated in terms of a concrete question.
```

The concrete question should be:

```text
Does order-4 provide sparse high-confidence confirmation that reduces false
support from order-2/order-3?
```

### 10. Should S34C use min token length 8 or 10 when we reach the intended 3/4 scorer stage?

My recommendation:

```text
Use min length 10 for the main S34C confirmation profile.
Emit min length 8 as a separate diagnostic if runtime allows.
```

Reason: S34C is supposed to be the highest-precision confirmation family. Length
10 keeps that role cleaner. Length 8 may be useful, but it needs null and
concentration review before it can share the same role.

### 11. Do we need a controlled 20/30/40/50 damage-ladder run before any profile can be promoted?

Before production promotion: yes, or an explicitly accepted substitute
validation that answers the same robustness question.

Before report-only bridge work: no.

Current candidate-comparability evidence can guide diagnostics, but it cannot
support controlled damage-tier claims. For any score-bearing promotion, damage
tier behavior matters because absence and survival rates differ sharply across
20-50 percent corruption.

### 12. What should be the first review pack that closes this discussion phase?

First closeout review pack should be:

```text
full raw order-2/order-3 provenance summary review pack
```

It should include:

```text
shard coverage
pass/fail shard manifests
order/cut asset counts
phrase length distributions
duplicate/collapse metadata
normal/strict differences
run logs
interruption/resume history
known limitations
```

The next review pack after that should be:

```text
order-2/order-3 cluster diagnostic pack design
```

or, if the design is already agreed:

```text
order-2/order-3 cluster diagnostic pack output
```

## Implementation Preparation While Current Run Continues

The following can be prepared without violating the current data gate.

### 1. Draft Profile Manifest Schema

Prepare a hardcoded profile manifest for the bridge:

```text
O2_soft
O2_conservative_len8
O2_long_len10
O3_soft
O3_conservative
```

Fields:

```text
profile_id
direction
orders
cuts
min_phrase_token_length
max_total_hd
max_word_hd
normalised_hd_ceiling
role
score_candidate_flag
diagnostic_flag
```

### 2. Draft Cluster Output Schema

Prepare schema fields:

```text
cluster_scope
cluster_id
candidate_id
chunk_id
start_offset
end_offset
profiles_present
cuts_present
orders_present
raw_hit_count
unique_phrase_id_count
unique_start_count
exact_hit_present
best_hit_signature
```

### 3. Draft Candidate Summary Schema

Prepare fields:

```text
candidate_id
profile_id
direction
cut
order
raw_hit_count
cluster_count
exact_hit_count
exact_cluster_count
unique_phrase_id_count
unique_start_count
hit_to_cluster_ratio
top_phrase_share
best_hit_signature
```

### 4. Draft Pair Ledger Schema

Prepare fields:

```text
pair_id
expected_better_id
expected_worse_id
baseline_winner
phrase_tuple_winner
order2_tuple_better
order2_tuple_worse
order3_tuple_better
order3_tuple_worse
normal_support_delta
strict_support_delta
first_diff_component
outcome_label
panel_rescue_flag
concentration_flags
null_lift_summary
```

### 5. Draft Panel-Rescue Zero-Hit Audit Schema

Prepare fields:

```text
pair_id
candidate_id
role
chunk_id
panel_rescue_flag
span_hamming_best_support
ngram_hit_count_by_order
phrase_opportunity_count_by_order
best_failed_or_near_phrase_note
likely_no_hit_reason
```

### 6. Draft Tests

Prepare tests for:

```text
overlap clusters merge
touching clusters merge
one-token gap does not merge
diagnostic-only clusters do not affect score-candidate clusters
raw hit count can exceed cluster count
exact hit fields are nested fields, not separate profiles
normal and strict remain separate
profile manifest hash changes when thresholds change
```

These tests can be written before broad execution if they use tiny synthetic
fixtures.

## Recommended Immediate Next After Current Run Completes

1. Summarize the full raw shard build.
2. Produce the full raw order-2/order-3 provenance review pack.
3. Stop for review.
4. If accepted, run or build the order-2/order-3 cluster diagnostic pack.
5. Use the cluster diagnostic output to decide whether:
   - order-3 becomes central;
   - order-2 remains diagnostic;
   - order-2 gets a narrow bridge-support role;
   - order-4 sizing is justified;
   - matched nulls should run immediately.

## Final Position

The v2 doc is directionally right and should become the coordination basis after
minor clarifications.

My recommended amendments are:

1. explicitly distinguish implementation preparation from broad run launch;
2. add dual cluster scopes for all-profile diagnostics versus score-candidate
   support;
3. keep P1 as diagnostic and P2-like profiles as bridge candidates;
4. add an `O2_long_len10` diagnostic because order-2 length may matter more than
   order alone;
5. use S34C length 10 as the main later confirmation profile, with length 8
   diagnostic if needed;
6. make the full raw order-2/order-3 provenance review pack the first closeout
   artifact for this discussion phase.

This preserves the research-led architecture while making good use of the active
implementation work and the early order-2 signal.

