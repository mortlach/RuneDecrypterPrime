# RDP No-WLI N-Gram Phrase Coherence Scorer
## v3.2 Final Parameter Review Against Deep Research Canon

Status: corrected discussion spec  
Purpose: lock canonical profile parameters against the deep-research outputs and prevent silent parameter drift  
Production status: no production scoring change approved  
Date: 2026-05-30

---

## 1. Reason for this revision

This v3.2 revision exists because the bridge profile section had started to introduce tacit assumptions about phrase length, profile thresholds, and order scope.

That is exactly the failure mode this scorer plan must avoid.

The risk is:

```text
a convenient bridge profile is introduced
then it starts looking like the real scorer profile
then a length/HD choice becomes a quiet default
then the default is treated as a robust design decision
```

This v3.2 spec therefore separates:

```text
canonical deep-research profile values
temporary bridge diagnostic values
local implementation convenience values
future profile variants
```

Only the canonical values may be described as the research-led scorer plan.

Anything else must be labelled as diagnostic, bridge-only, experimental, or future-only.

---

## 2. Canon rule

The deep-research profile values are canonical unless this document explicitly says otherwise.

Any profile in code, manifests, readouts, review packs, or planning docs must declare:

```text
profile_origin
canonical_profile_id
parameter_status
score_authority
```

Allowed `profile_origin` values:

```text
deep_research_canon
original_prompt_profile
bridge_derived
implementation_probe
future_variant
```

Allowed `parameter_status` values:

```text
canonical
canonical_equivalent
broader_than_canon
narrower_than_canon
new_noncanonical
diagnostic_only
blocked
```

Allowed `score_authority` values:

```text
score_bearing_candidate
diagnostic_only
blocked_bridge_candidate
future_only
```

A profile may not silently change:

```text
order
cut
min phrase token length
max total HD
max word HD
score-bearing role
diagnostic role
```

If any of these change, it is a new profile or a non-canonical variant.

---

## 3. Deep-research canonical architecture

The canonical scorer architecture is:

```text
exact word-structured phrase Hamming
positive support only
normal and strict cuts kept separate
FWD first
all eligible hits counted exactly
no hit caps
no top-k
no silent fallback
no raw additive fusion
cluster support, not raw hit volume
count/log-count fields diagnostic only
```

Phrase identity is canonical on:

```text
direction
dictionary_cut
ngram_order
canonical word_token_ids
```

Flattened rune/token IDs are scanning payload only.

They must not become the canonical phrase identity or deduplication key.

---

## 4. Original prompt profile ladder: P0-P5

These were the original broad research-input profiles. They are not all score-bearing recommendations, but they are the baseline parameter set from which later profiles derive.

### P0 exact baseline

```text
orders: 2, 3, 4
cuts: normal, strict
min_phrase_token_length: 5
max_total_phrase_hd: 0
max_word_hd: 0
role: audit / exact baseline
```

### P1 word-analogue

```text
orders: 2, 3, 4
cuts: normal, strict
min_phrase_token_length: 7
max_total_phrase_hd: 2
max_word_hd: 2
role: soft diagnostic / inherited from single-word evidence
```

Important: P1 is not a universal phrase-scoring rule.

It is useful as a soft diagnostic because it inherits the earlier single-word intuition, but it must not silently become the central phrase scorer.

### P2 conservative

```text
orders: 2, 3, 4
cuts: normal, strict
min_phrase_token_length: 8
max_total_phrase_hd: 2
max_word_hd: 1
role: conservative phrase-Hamming family
```

### P3 longer phrase

```text
orders: 3, 4
cuts: normal, strict
min_phrase_token_length: 10
max_total_phrase_hd: 3
max_word_hd: 2
role: longer phrase support
```

### P4 strict long

```text
orders: 3, 4
cuts: strict
min_phrase_token_length: 10
max_total_phrase_hd: 2
max_word_hd: 1
role: strict long confirmation
```

### P5 5-gram diagnostic

```text
order: 5
cuts: normal, strict
min_phrase_token_length: 12
max_total_phrase_hd: 3
max_word_hd: 2
role: diagnostic only
```

---

## 5. Canonical deep-research scorer ladder

This is the canonical research-led scorer ladder for the intended phrase-coherence scorer.

### Diagnostic family: B2R

```text
profile_id: B2R
profile_origin: deep_research_canon
canonical_profile_id: B2R
orders: {2}
cuts: normal, strict reported separately
min_phrase_token_length: 7
max_total_phrase_hd: 2
max_word_hd: 2
score_authority: diagnostic_only
role: weak order-2 telemetry
risk: dangerous / inflation-prone
```

B2R may be useful for instrumentation, coverage checking, and explaining early order-2 behaviour.

It is not score-bearing in the first scorer ladder.

### Diagnostic family: N3S_diag

```text
profile_id: N3S_diag
profile_origin: deep_research_canon
canonical_profile_id: N3S_diag
orders: {3}
cuts: normal
min_phrase_token_length: 7
max_total_phrase_hd: 2
max_word_hd: 2
score_authority: diagnostic_only
role: soft normal trigram diagnostic
risk: tests whether P1 carry-over is too loose
```

This is the soft P1-style trigram diagnostic.

It should not silently become the central 3-gram scorer.

### Score-bearing candidate family: N3C

```text
profile_id: N3C
profile_origin: deep_research_canon
canonical_profile_id: N3C
orders: {3}
cuts: normal
min_phrase_token_length: 8
max_total_phrase_hd: 2
max_word_hd: 1
score_authority: score_bearing_candidate
role: main normal 3-gram coverage
risk: medium
```

This is the first serious central 3-gram coverage profile.

### Score-bearing candidate family: S3W

```text
profile_id: S3W
profile_origin: deep_research_canon
canonical_profile_id: S3W
orders: {3}
cuts: strict
min_phrase_token_length: 7
max_total_phrase_hd: 2
max_word_hd: 2
score_authority: score_bearing_candidate
role: strict trigram confirmation with moderate reach
risk: low to medium
```

This is a strict 3-gram confirmation profile.

Note that it is not the same as strict P2. Its threshold is softer on max-word-HD than N3C.

### Score-bearing candidate family: N4L

```text
profile_id: N4L
profile_origin: deep_research_canon
canonical_profile_id: N4L
orders: {4}
cuts: normal
min_phrase_token_length: 10
max_total_phrase_hd: 3
max_word_hd: 2
score_authority: score_bearing_candidate
role: longer normal 4-gram confirmation
risk: medium to low
```

This is the normal order-4 confirmation profile.

### Score-bearing candidate family: S34C_main

```text
profile_id: S34C_main
profile_origin: deep_research_canon
canonical_profile_id: S34C
orders: {3, 4}
cuts: strict
min_phrase_token_length: 10
max_total_phrase_hd: 2
max_word_hd: 1
score_authority: score_bearing_candidate
role: highest-precision strict confirmation / bounded-override candidate
risk: low, but likely sparse
```

This v3.2 spec treats min phrase token length 10 as the canonical value for the main S34C confirmation profile.

Reason: S34C is intended to be the highest-precision strict confirmation family. Length 10 preserves that role. A length-8 version is broader and must be diagnostic unless separately promoted.

### Diagnostic family: F5D

```text
profile_id: F5D
profile_origin: deep_research_canon
canonical_profile_id: F5D
orders: {5}
cuts: normal, strict reported separately
min_phrase_token_length: 12
max_total_phrase_hd: 3
max_word_hd: 2
score_authority: diagnostic_only
role: sparse high-confidence 5-gram diagnostic
risk: very sparse, not central
```

Order 5 remains optional and diagnostic unless later evidence proves otherwise.

---

## 6. Canonical tuple direction

The intended later score-candidate tuple remains based on the canonical families:

```text
T(candidate) =
(
  S34C_main_cluster_count,
  N4L_cluster_count,
  S3W_cluster_count,
  N3C_cluster_count,
  S34C_main_exact_cluster_count,
  N4L_exact_cluster_count,
  S3W_exact_cluster_count,
  N3C_exact_cluster_count,
  best_hit_signature
)
```

Diagnostic families do not enter this tuple:

```text
B2R
N3S_diag
F5D
```

Raw hits do not enter this tuple.

Count/log-count values do not enter this tuple.

---

## 7. Drift found in the bridge section

The v3 bridge section introduced:

```text
O2_soft
O2_conservative_len8
O2_long_len10
O3_soft
O3_conservative
```

These bridge profiles are not wrong, but they are not the canonical deep-research scorer ladder.

They are temporary order-2/order-3 diagnostics.

They exist only because the current data-plane tranche is order 2 and order 3.

They must not silently replace:

```text
B2R
N3S_diag
N3C
S3W
N4L
S34C_main
F5D
```

---

## 8. Corrected bridge section name

Do not call the bridge section:

```text
Bridge profile family
```

Use:

```text
Temporary order-2/order-3 bridge diagnostics
```

This makes the scope clear.

The bridge is not the final scorer ladder.

The bridge is not production scoring.

The bridge is not a replacement for order 4.

The bridge is not a replacement for F5D diagnostics.

---

## 9. Corrected temporary bridge diagnostics

### BR_O2_soft

```text
profile_id: BR_O2_soft
profile_origin: bridge_derived
canonical_profile_id: B2R
orders: {2}
cuts: normal, strict separately
min_phrase_token_length: 7
max_total_phrase_hd: 2
max_word_hd: 2
parameter_status: canonical_equivalent for B2R shape, but bridge-scoped
score_authority: diagnostic_only
role: inspect currently active order-2 shape
promotion_status: blocked
```

This is essentially B2R scoped into the bridge.

It remains diagnostic only.

### BR_O2_len8_conservative

```text
profile_id: BR_O2_len8_conservative
profile_origin: bridge_derived
canonical_profile_id: none
orders: {2}
cuts: normal, strict separately
min_phrase_token_length: 8
max_total_phrase_hd: 2
max_word_hd: 1
parameter_status: derived from P2 but non-canonical for order-2 scoring
score_authority: blocked_bridge_candidate
role: test whether conservative order-2 evidence survives anti-inflation checks
promotion_status: blocked pending null/concentration/pair-ledger/damage-tier review
```

This is not a canonical scorer profile.

It is a bridge diagnostic derived from P2.

Deep research did not recommend order-2 as score-bearing in the first scorer ladder.

### BR_O2_len10_long

```text
profile_id: BR_O2_len10_long
profile_origin: bridge_derived
canonical_profile_id: none
orders: {2}
cuts: normal, strict separately
min_phrase_token_length: 10
max_total_phrase_hd: 2
max_word_hd: 1
parameter_status: new_noncanonical
score_authority: diagnostic_only
role: test whether long two-word phrases behave differently from short two-word phrases
promotion_status: blocked
```

This profile was not directly recommended by the deep research.

It is allowed only as a labelled diagnostic to test whether order-2 behaviour is actually a phrase-token-length effect.

### BR_O3_soft

```text
profile_id: BR_O3_soft
profile_origin: bridge_derived
canonical_profile_id: N3S_diag for normal cut only
orders: {3}
cuts: normal, strict separately
min_phrase_token_length: 7
max_total_phrase_hd: 2
max_word_hd: 2
parameter_status: normal cut is canonical-equivalent to N3S_diag; strict cut is bridge extension
score_authority: diagnostic_only
role: inspect soft P1-style trigram behaviour
promotion_status: blocked
```

The normal-cut view maps to N3S_diag.

The strict-cut view is not S3W unless explicitly declared and interpreted as strict soft 3-gram evidence.

### BR_O3_conservative

```text
profile_id: BR_O3_conservative
profile_origin: bridge_derived
canonical_profile_id: N3C for normal cut only
orders: {3}
cuts: normal, strict separately
min_phrase_token_length: 8
max_total_phrase_hd: 2
max_word_hd: 1
parameter_status: normal cut is canonical-equivalent to N3C; strict cut is not S3W
score_authority: blocked_bridge_candidate
role: first serious order-3 bridge candidate and N3C-style diagnostic
promotion_status: can inform N3C; strict view requires separate review
```

Important correction:

```text
BR_O3_conservative strict is not S3W.
```

S3W is:

```text
strict, order 3, min length 7, HD <= 2, max word HD <= 2
```

BR_O3_conservative strict is:

```text
strict, order 3, min length 8, HD <= 2, max word HD <= 1
```

Those are different profiles.

They must not be silently conflated.

---

## 10. Parameter cross-check table

| Proposed / bridge profile | Deep-research match | Status | Required label |
|---|---|---|---|
| `B2R` | Exact canonical diagnostic | Keep | `deep_research_canon`, `diagnostic_only` |
| `N3S_diag` | Exact canonical diagnostic | Keep | `deep_research_canon`, `diagnostic_only` |
| `N3C` | Exact canonical score-candidate | Keep | `deep_research_canon`, `score_bearing_candidate` |
| `S3W` | Exact canonical score-candidate | Keep | `deep_research_canon`, `score_bearing_candidate` |
| `N4L` | Exact canonical score-candidate | Keep | `deep_research_canon`, `score_bearing_candidate` |
| `S34C_main_len10` | Canonical in v3.2 | Keep | `deep_research_canon`, `score_bearing_candidate` |
| `S34C_len8` | Broader than canonical | Diagnostic only | `future_variant`, `broader_than_canon`, `diagnostic_only` |
| `F5D` | Exact canonical diagnostic | Keep | `deep_research_canon`, `diagnostic_only` |
| `BR_O2_soft` | Same thresholds as B2R | Bridge diagnostic | `bridge_derived`, `canonical_equivalent`, `diagnostic_only` |
| `BR_O2_len8_conservative` | P2-derived but not canonical scorer | Blocked bridge diagnostic | `bridge_derived`, `noncanonical`, `blocked_bridge_candidate` |
| `BR_O2_len10_long` | New, not directly recommended | Diagnostic only | `bridge_derived`, `new_noncanonical`, `diagnostic_only` |
| `BR_O3_soft_normal` | Same thresholds as N3S_diag | Bridge diagnostic | `bridge_derived`, `canonical_equivalent`, `diagnostic_only` |
| `BR_O3_soft_strict` | Strict extension of N3S-style profile | Diagnostic only | `bridge_derived`, `new_noncanonical`, `diagnostic_only` |
| `BR_O3_conservative_normal` | Same thresholds as N3C | Bridge candidate | `bridge_derived`, `canonical_equivalent`, `blocked_bridge_candidate` |
| `BR_O3_conservative_strict` | Not S3W; stricter P2-like strict view | Blocked bridge candidate | `bridge_derived`, `narrower_than_S3W`, `blocked_bridge_candidate` |

---

## 11. Corrected treatment of S34C

There was drift on S34C.

One later table allowed:

```text
S34C:
  min phrase token length: 8
```

But the stricter high-precision role is better aligned with:

```text
S34C_main:
  min phrase token length: 10
```

For this v3.2 spec:

```text
S34C_main = length 10
S34C_len8 = diagnostic only if emitted
```

No implementation may silently broaden S34C_main from 10 to 8.

If length 8 is used, it must have a separate profile ID:

```text
S34C_len8_diag
```

and must be labelled:

```text
broader_than_canon
diagnostic_only
```

---

## 12. Corrected treatment of P1/P2

### P1

```text
min length: 7
HD <= 2
max word HD <= 2
```

P1 is a soft diagnostic.

It is inherited from the single-word evidence region.

It is not central phrase evidence.

Allowed P1-style uses:

```text
B2R
N3S_diag
BR_O2_soft
BR_O3_soft
```

All are diagnostic unless separately promoted through review.

### P2

```text
min length: 8
HD <= 2
max word HD <= 1
```

P2 is more conservative.

Allowed P2-style uses:

```text
N3C for normal order 3
BR_O2_len8_conservative as blocked diagnostic bridge
BR_O3_conservative_normal as N3C-equivalent bridge view
```

P2-style order-2 evidence remains blocked unless it clears null, concentration, pair-ledger, and damage-tier review.

---

## 13. Corrected treatment of order 2

Order 2 must not become score-bearing merely because it was first or because it produced the first visible signal.

Canonical order-2 role:

```text
B2R diagnostic only
```

Order-2 bridge diagnostics may be run to inspect:

```text
instrumentation
coverage
phrase-token-length effects
inflation risk
normal/strict separation
```

Order 2 can move beyond diagnostic only if it passes a higher burden than order 3:

```text
cluster diversity
low concentration
matched-null lift
pair-ledger improvement
low or zero breaks
evidence not dominated by one phrase, one start, one cluster, or one candidate family
controlled damage-tier review before production promotion
```

---

## 14. Corrected treatment of order 3

Order 3 remains the first serious phrase-coherence test.

Canonical order-3 roles:

```text
N3S_diag: soft diagnostic
N3C: main normal coverage candidate
S3W: strict trigram confirmation candidate
S34C_main: strict order-3/order-4 high-precision confirmation candidate
```

Bridge order-3 profiles may inform these canonical profiles, but only where thresholds actually match.

Do not silently equate strict BR_O3_conservative with S3W.

---

## 15. Corrected treatment of order 4

Order 4 must not be dropped from the plan.

Order 4 is only outside the current bridge because the active full raw tranche is order 2 and order 3.

That is a data-plane scope limit, not a design decision.

Canonical order-4 roles:

```text
N4L: normal order-4 confirmation
S34C_main: strict order-3/order-4 high-precision confirmation
```

Order 4 should be sized after order-2/order-3 provenance and bridge diagnostics are reviewed.

No document may imply that order 4 has been judged and rejected.

---

## 16. Corrected treatment of order 5

Order 5 remains optional and diagnostic.

Canonical order-5 role:

```text
F5D:
  order: 5
  normal/strict
  min length: 12
  HD <= 3
  max word HD <= 2
  diagnostic only
```

Order 5 is not part of the order-2/order-3 bridge.

That does not delete it from the future diagnostic plan.

---

## 17. Required manifest additions

Every profile row must include:

```text
profile_id
profile_origin
canonical_profile_id
parameter_status
score_authority
orders
cuts
min_phrase_token_length
max_total_phrase_hd
max_word_hd
role
scope_reason
equivalent_research_profile
promotion_status
```

Where useful, include:

```text
broader_than_profile
narrower_than_profile
threshold_diff_summary
```

Examples:

```text
profile_id: BR_O3_conservative_strict
canonical_profile_id: none
parameter_status: narrower_than_S3W
threshold_diff_summary:
  S3W min_len=7, max_word_hd=2
  this profile min_len=8, max_word_hd=1
score_authority: blocked_bridge_candidate
```

---

## 18. Required scope declaration additions

Every run must say whether it is running:

```text
canonical scorer ladder
bridge diagnostic ladder
implementation probe
future diagnostic variant
```

Every run must list:

```text
requested_profiles
effective_profiles
completed_profiles
omitted_canonical_profiles
omitted_orders
omitted_cuts
omitted_directions
why_omitted
unsafe_interpretations
```

Example:

```text
This bridge run includes orders 2 and 3 only.
Order 4 is omitted because it is not in the current full raw asset tranche.
Therefore this run cannot test N4L or full S34C_main behaviour.
```

---

## 19. Required review questions before accepting any bridge pack

Before accepting the bridge diagnostic pack, reviewers must answer:

```text
1. Which profiles exactly match deep-research canonical profiles?
2. Which profiles are derived from P1/P2/P3/P4/P5 but not canonical scorer profiles?
3. Which profiles are new and not directly recommended by the research?
4. Which profiles are diagnostic only?
5. Which profiles are blocked from score-bearing use?
6. Which profiles, if any, can inform N3C/S3W/N4L/S34C_main?
7. Has any profile silently changed min phrase token length?
8. Has any profile silently changed max total HD?
9. Has any profile silently changed max word HD?
10. Has any diagnostic profile affected score-candidate clusters?
11. Has order 4 been deferred only for data-plane reasons, not design reasons?
12. Has order 5 been deferred only as optional diagnostic, not deleted?
13. Are counts/log-counts still diagnostic only?
14. Are raw hits still diagnostic only?
15. Are normal and strict still separate?
```

If any answer is unclear, the bridge pack is not review-ready.

---

## 20. Final v3.2 corrected position

The corrected plan is:

```text
Continue the current full raw order-2/order-3 build.

Use the time to prepare bridge diagnostics, schemas, and tests.

Do not launch broad bridge scans until full raw order-2/order-3 provenance passes.

Do not mistake bridge profiles for the canonical deep-research scorer ladder.

Use bridge profiles only to inspect:
  order-2 instrumentation evidence,
  order-3 first serious phrase-coherence evidence,
  strict/normal separation,
  phrase-token-length effects,
  clustering and inflation behaviour.

Keep the canonical research scorer ladder intact:
  diagnostics: B2R, N3S_diag, F5D
  score-bearing candidates: N3C, S3W, N4L, S34C_main

Keep S34C_main at min phrase token length 10.
Allow S34C_len8 only as diagnostic.

Keep order 2 diagnostic unless it clears a much higher proof burden.

Do not drop order 4.
Do not drop order 5 diagnostics.
Do not use count/log-count weighting.
Do not use raw hit counts as scores.
Do not allow diagnostic profiles to shape score-candidate clusters.

Make every scope reduction explicit in the manifest and readout.
```

---

## 21. Bottom line

The bridge diagnostics are allowed, but they are not the canonical scorer.

The canonical research-aligned scorer direction remains:

```text
N3C
S3W
N4L
S34C_main
```

with:

```text
B2R
N3S_diag
F5D
```

as diagnostics.

The bridge must not silently descope that plan into order-2/order-3 only.

The bridge must not silently broaden S34C from length 10 to length 8.

The bridge must not treat P1/P2 convenience thresholds as robust phrase-scoring design.


## Final Amendment: Staged Build Toward the Full Design

The project is allowed to build toward the research-led scorer design in stages.

However, staged implementation must not become silent scope reduction.

Every stage must clearly state:

```text
1. the end-state design it is building toward;
2. the subset implemented in this stage;
3. the subset deliberately not implemented yet;
4. what this stage is allowed to prove;
5. what this stage is not allowed to prove;
6. which outputs are diagnostic only;
7. which outputs, if any, are score-candidate outputs;
8. what evidence is required before the next stage.
```

The end-state design remains:

```text
exact word-structured phrase Hamming
canonical phrase identity on word_token_ids
normal/strict separation
FWD/REV separation
explicit profile families
cluster-based support
exact all-hit accounting
matched post-word-Hamming nulls
hard-pair rescue/break reporting
positive support only
no raw additive score
no count/log-count weighting in v1
```

Bridge work is allowed, but only as a bridge.

The order-2/order-3 bridge diagnostics exist to test and prepare the end-state architecture. They do not replace the canonical research ladder, and they do not silently descope order 4 or order 5.

Tooling should therefore be built with the end-state design in mind.

At minimum, the tooling should support profile-manifest driven iteration over:

```text
order
cut
direction
min phrase token length
max total HD
max word HD
score-bearing vs diagnostic role
cluster scope
exact-hit fields
length-bucket reporting
matched-null mode
```

This does not mean every profile or order must be run immediately.

It means the code and reports should not bake in a one-off order-2/order-3 assumption that later has to be undone.

The planning language should distinguish:

```text
destination:
  the research-led scorer architecture

stage:
  a partial implementation step toward that architecture

probe:
  a diagnostic run whose result may or may not become useful
```

Current order-2/order-3 bridge work is a stage/probe.

It is not the final scorer destination.

Also:

```text
Tool capability does not imply score authority.
```

A field may be computed, emitted, and analysed without being score-bearing.

This applies especially to:

```text
raw_hit_count
order-2 support
P1-style soft support
count/log_count
diagnostic profiles
global exact fields
null-fragile support
```

The manifest must make the score authority explicit.

No interim run should be allowed to imply a broader conclusion than its declared scope supports.

