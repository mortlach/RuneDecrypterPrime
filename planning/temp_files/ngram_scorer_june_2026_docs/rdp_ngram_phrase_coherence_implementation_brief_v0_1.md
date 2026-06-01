# RDP Robust N-Gram Phrase Coherence Scorer
## Implementation Brief v0.1 — Python Reference First

Date: 2026-05-30  
Status: design-gate ready  
Scope: deterministic Python reference implementation and offline hard-pair evaluation only

---

## 1. Purpose

Build the first production-shaped **Robust N-Gram Phrase Coherence Scorer** for RuneDecrypterPrime.

This scorer runs **after** the existing word-Hamming / span-Hamming layer.

The word/span layer asks:

> Does this no-WLI candidate contain damaged word-like local evidence?

The new phrase scorer asks:

> Do those local word-like regions line up into plausible ordered n-gram phrase evidence?

This is not a generic language model and not a raw n-gram frequency score. It is a second-stage evidence layer for damaged candidate ranking.

---

## 2. What “done” means for this phase

This phase is complete when we have a deterministic Python reference implementation that can:

1. Load declared phrase profiles from a manifest.
2. Evaluate FWD n-gram phrase assets with exact word-structured Hamming.
3. Emit every eligible hit for each declared profile, with no caps and no top-k.
4. Preserve phrase identity using structured `word_token_ids`, not just flattened token sequences.
5. Cluster score-bearing phrase hits using the v1 overlap-or-touch rule.
6. Produce per-candidate support tuples.
7. Produce hard-pair reports for:
   - `report_only`
   - `tie_break`
   - `bounded_override`
8. Produce matched null diagnostics:
   - `offset_permute_null`
   - `window_collage_null`
   - `periodic_decoy_null`
9. Write enough manifests and records that a later C++ backend can be tested against the Python reference exactly.

The phase is **not** complete merely because a scalar score exists.

---

## 3. Non-goals for this phase

Do not implement these as score-bearing production behaviour in this phase:

- C++ fast backend.
- Live production ranking changes.
- Direct additive score merge with existing word/span ranking.
- Joined-phrase Hamming as a ranking path.
- Edit-distance phrase scoring.
- Skip/gapped phrase scoring.
- Noisy-channel scoring.
- N-gram language-model reranking.
- WFST composition.
- Count/log-count weighting.
- Any absence penalty for missing phrase evidence.
- Hit caps, top-k, max hits per chunk, or max hits per offset.

Diagnostic reporting is allowed for some of these ideas only where explicitly listed below.

---

## 4. Core design decision

Use **exact word-structured phrase Hamming**.

For a phrase with words:

```text
w1, w2, ..., wn
```

and token lengths:

```text
L1, L2, ..., Ln
```

at candidate start offset `s`, compare:

```text
candidate[s : s+L1]                       against w1
candidate[s+L1 : s+L1+L2]                 against w2
candidate[s+L1+L2 : s+L1+L2+L3]           against w3
...
```

For each candidate phrase placement, compute:

```text
word_hds
total_phrase_hd
max_word_hd
phrase_token_length
normalised_phrase_hd
exact_flag
```

A hit is valid for a profile only if it satisfies that profile’s declared gates.

---

## 5. Phrase identity rule

Phrase identity is:

```text
direction
dictionary_cut
ngram_order
canonical word_token_ids
```

Do not use the joined flattened token sequence as the phrase identity.

`rune_token_ids` may be used for scanning and compatibility checks, but not as the canonical identity.

This matters because two different word-structured phrases can flatten to the same token sequence.

---

## 6. First-run profile ladder

The first run uses a small frozen ladder.

### Score-bearing profiles

| Profile | Orders | Cuts | Min phrase token length | Max total HD | Max word HD | Role |
|---|---:|---|---:|---:|---:|---|
| `N3C` | `{3}` | `normal` | 8 | 2 | 1 | main normal coverage |
| `S3W` | `{3}` | `strict` | 7 | 2 | 2 | strict trigram confirmer |
| `N4L` | `{4}` | `normal` | 10 | 3 | 2 | longer normal confirmation |
| `S34C` | `{3,4}` | `strict` | 8 | 2 | 1 | highest precision confirmation |

### Diagnostic profiles

| Profile | Orders | Cuts | Min phrase token length | Max total HD | Max word HD | Role |
|---|---:|---|---:|---:|---:|---|
| `B2R` | `{2}` | `normal`, `strict` | 7 | 2 | 2 | weak 2-gram telemetry; risky |
| `N3S_diag` | `{3}` | `normal` | 7 | 2 | 2 | softer normal trigram diagnostic |
| `F5D` | `{5}` | `normal`, `strict` | 12 | 3 | 2 | sparse 5-gram diagnostic |

### Important profile notes

- `B2R`, `N3S_diag`, and `F5D` must not enter the v1 support tuple.
- `count` and `log_count` must not affect the score.
- Exact hits are not separate profiles. They are fields inside each profile and in global diagnostics.
- FWD only for this phase.
- REV assets must not be silently mixed into FWD scoring.

---

## 7. Hit record contract

Every score-affecting hit must produce a full hit record.

Minimum fields:

```text
run_id
candidate_id
chunk_id
profile_id
direction
dictionary_cut
ngram_order
phrase_id
word_token_ids
start_offset
end_offset
phrase_token_length
rune_lengths
word_hds
total_phrase_hd
max_word_hd
normalised_phrase_hd
exact_flag
count
log_count
is_score_bearing_profile
```

`count` and `log_count` are included for diagnostics only.

The implementation must never return only the “best” hits. All eligible hits for each declared profile must be emitted or the run must fail.

---

## 8. Cluster definition

For v1, a phrase coherence cluster means:

> The connected component of all score-bearing phrase hits whose flattened token intervals overlap or touch.

For a hit `h`:

```text
start = s(h)
end = s(h) + phrase_token_length(h)
interval = [start, end)
```

Two hits are in the same cluster if:

```text
next.start <= current_cluster_end
```

A new cluster starts only when:

```text
next.start > current_cluster_end
```

### Important cluster rules

- Clustering applies only to score-bearing profiles:
  - `N3C`
  - `S3W`
  - `N4L`
  - `S34C`
- Clustering is global across all score-bearing families.
- Within one cluster, each score-bearing family contributes at most one unit.
- Within one cluster, exact evidence contributes at most one exact unit per family.
- Raw hit counts are diagnostic only.
- Cluster counts are score-bearing.

This is the main protection against repeated-local-structure inflation.

---

## 9. Cluster record contract

Minimum cluster fields:

```text
run_id
candidate_id
chunk_id
cluster_id
start_offset
end_offset
families_present
phrase_ids_present
best_hit_signature
has_N3C
has_S3W
has_N4L
has_S34C
has_exact_N3C
has_exact_S3W
has_exact_N4L
has_exact_S34C
raw_hit_count
unique_phrase_id_count
unique_start_count
```

Diagnostic concentration fields:

```text
hit_to_cluster_ratio_by_family
top_phrase_share_by_family
```

---

## 10. Exact-hit handling

Exact hits are fields, not a separate score-bearing profile family.

Emit:

```text
exact_hit_count_N3C
exact_cluster_count_N3C
exact_hit_count_S3W
exact_cluster_count_S3W
exact_hit_count_N4L
exact_cluster_count_N4L
exact_hit_count_S34C
exact_cluster_count_S34C
exact_hit_count_global
exact_cluster_count_global
```

Only the family exact-cluster counts enter the phrase support tuple.

Global exact fields are report-only.

---

## 11. Candidate support tuple

The v1 phrase support tuple is:

```text
T(candidate) =
(
    S34C_cluster_count,
    N4L_cluster_count,
    S3W_cluster_count,
    N3C_cluster_count,

    S34C_exact_cluster_count,
    N4L_exact_cluster_count,
    S3W_exact_cluster_count,
    N3C_exact_cluster_count,

    best_hit_signature
)
```

Compare tuples lexicographically. Larger is better.

Diagnostic profiles do not enter the tuple.

Raw hit counts do not enter the tuple.

Counts/log-counts do not enter the tuple.

---

## 12. Best hit signature

`best_hit_signature` is a deterministic tie-break and audit field only.

Recommended ordering:

```text
best_hit_signature =
max_lex_h (
    family_rank(h),          # S34C > N4L > S3W > N3C > diagnostics
    exact_flag(h),           # 1 > 0
    phrase_token_length(h),  # longer is better
    -total_phrase_hd(h),     # lower is better
    -max_word_hd(h),         # lower is better
    phrase_id(h)             # deterministic terminal tie-break
)
```

`best_hit_signature` must never outrank the family cluster counts.

---

## 13. Offline decision modes

The phrase scorer must first be evaluated offline. It must not change live production ranking in this phase.

The existing baseline comparator must be split into manifest-declared blocks:

```text
B_core
B_tail
```

If this split does not currently exist, it must be created before `tie_break` or `bounded_override` can be considered mechanically meaningful.

### 13.1 `report_only`

Baseline winner remains unchanged.

Also compute:

```text
phrase_cmp = lexcmp(T(a), T(b))
```

Log whether phrase evidence:

```text
agrees
disagrees
ties
```

### 13.2 `tie_break`

Comparator:

```text
1. Compare B_core(a) vs B_core(b).
2. If unequal, baseline wins.
3. If equal, compare T(a) vs T(b).
4. If still equal, compare B_tail(a) vs B_tail(b).
5. If still equal, use stable candidate id order.
```

### 13.3 `bounded_override`

Comparator:

```text
1. Compare B_core_strong(a) vs B_core_strong(b),
   where B_core_strong is B_core with its single weakest field removed.

2. If unequal, baseline wins.

3. If equal, phrase may replace that weakest field only if override_guard passes.

4. Otherwise fall back to the removed weak field,
   then B_tail,
   then stable candidate id order.
```

`override_guard(a, b)` is true iff:

```text
1. T(a) > T(b), and

2. the first differing component between T(a) and T(b)
   is one of:
   {
     S34C_cluster_count,
     N4L_cluster_count,
     S34C_exact_cluster_count,
     N4L_exact_cluster_count
   }, and

3. a has at least one top-family cluster:
   S34C_cluster_count + N4L_cluster_count >= 1, and

4. b has no top-family cluster:
   S34C_cluster_count + N4L_cluster_count == 0.
```

This intentionally prevents lower-family accumulation from driving an override.

---

## 14. Matched null generators

The nulls must be built from real upstream word/span support. They must not invent a new damage model.

### Shared input: anchor manifest

Create an anchor manifest from upstream word/span hits:

1. Merge upstream word/span hits by overlap-or-touch into non-overlapping local support regions.
2. In each region choose one canonical anchor span by:

```text
lower HD
longer length
stricter cut
earlier start
```

3. Keep the original gap segments between anchor regions unchanged.

This anchor manifest must be deterministic.

### 14.1 `offset_permute_null`

Input:

```text
one candidate anchor manifest
```

Preserves:

```text
anchor-span contents
anchor count
anchor lengths
original gap lengths
candidate-level damage texture
```

Destroys:

```text
original local ordering
original adjacency between supported spans
```

Construction:

```text
Permute anchor spans among anchor slots by a manifest-seeded derangement.
Keep gaps fixed.
Use stable sorting and a recorded seed.
```

Diagnostics:

```text
per-family hit counts
per-family cluster counts
exact cluster counts
support tuple
raw-to-cluster ratio
original-vs-null lift
```

### 14.2 `window_collage_null`

Input:

```text
anchor manifests from the same evaluation bucket
```

Preserves:

```text
real observed anchors
matched support density
matched length/support bins
real gap geometry
```

Destroys:

```text
candidate-specific phrase continuity across anchors
```

Construction:

```text
For each target anchor slot, choose a donor anchor from another candidate in the same bucket.
Use deterministic round-robin nearest-bin matching.
Exclude self as donor.
```

Diagnostics:

```text
per-family hit counts
per-family cluster counts
exact cluster counts
support tuple
raw-to-cluster ratio
original-vs-null lift
donor-bucket coverage
seam concentration
```

### 14.3 `periodic_decoy_null`

Input:

```text
one candidate anchor manifest
```

Preserves:

```text
real anchor contents
original slot-length distribution
original gap lengths
```

Destroys:

```text
lexical diversity
natural phrase ordering
```

Construction:

```text
For each anchor-length bin, fill every slot with the strongest anchor from that same bin.
If two representatives are used, cycle deterministically.
```

Diagnostics:

```text
per-family hit counts
per-family cluster counts
exact cluster counts
support tuple
raw-to-cluster ratio
top_phrase_share
hit_to_cluster_ratio inflation under repetition
```

---

## 15. Output files

The Python reference run should produce parser-friendly outputs.

Recommended outputs:

```text
run_manifest.json
asset_manifest.json
profile_manifest.json
phrase_hits.csv
phrase_clusters.csv
candidate_phrase_summary.csv
hard_pair_phrase_report.csv
null_phrase_summary.csv
readout.md
```

### 15.1 `run_manifest.json`

Minimum fields:

```text
run_id
timestamp_utc
implementation_name
implementation_version
python_version
asset_manifest_sha256
profile_manifest_sha256
cluster_mode
tuple_order
null_seed
score_affecting_profiles
diagnostic_profiles
counts_used_for_scoring = false
live_ranking_changed = false
```

### 15.2 `profile_manifest.json`

Must contain every active profile exactly as run.

A change to any threshold, role, order set, cut set, or cluster mode must change the manifest hash.

### 15.3 `readout.md`

Must include:

```text
run status
candidate count
hard-pair count
profile table
tuple order
cluster mode
number of hits emitted
number of clusters emitted
any fail-loud errors
report_only summary
tie_break summary
bounded_override summary
null-lift summary
concentration warnings
```

---

## 16. Hard-pair report fields

For each pair:

```text
pair_id
expected_better_id
expected_worse_id
baseline_cmp
phrase_cmp
report_only_outcome
tie_break_outcome
bounded_override_outcome
first_diff_tuple_component
better_tuple
worse_tuple
better_best_hit_signature
worse_best_hit_signature
better_cluster_summary
worse_cluster_summary
rescue_or_break_by_mode
null_lift_summary
concentration_flags
```

The hard-pair report is the main review object.

---

## 17. Review-pass criteria

The first run is review-pass only if:

1. Every contract test passes.
2. All-hit exactness is proved on synthetic dense cases.
3. Manifest integrity is proved.
4. Deterministic reruns produce identical outputs.
5. `report_only` shows positive net rescues for the score-bearing tuple.
6. `tie_break` simulation shows positive net rescues with precision at or above 0.90.
7. `bounded_override` simulation produces no breaks on the primary hard-pair set.
8. Top-family phrase support has at least 2× real-vs-null lift against the strongest matched null.
9. No score-bearing family breaches concentration guardrails:

```text
top_phrase_share > 0.35
median hit_to_cluster_ratio > 3
```

If the hard-pair set is too small for these numbers to be stable, report that explicitly and do not promote.

---

## 18. Hard-fail conditions

The run must fail clearly if any of these happen:

```text
eligible hits are dropped
any score-affecting hit cap is applied
top-k affects score-bearing output
normal/strict separation leaks
FWD/REV assets are mixed silently
phrase identity collapses to flattened token sequence only
duplicate structured phrase ids are accepted silently
rune_lengths are malformed
word_hds do not sum to total_phrase_hd
exact counts exceed total counts
profile manifest is missing or incomplete
asset manifest is missing or incomplete
offline mode depends on undeclared baseline field partition
deterministic rerun differs
```

These are contract errors, not modelling disappointments.

---

## 19. Test plan

### 19.1 Profile manifest tests

Check:

```text
all expected profile ids exist
score-bearing vs diagnostic flags are correct
thresholds match this spec
FWD-only scope is explicit
counts_used_for_scoring is false
```

### 19.2 Word-structured identity tests

Create two phrases with the same flattened token sequence but different `word_token_ids`.

Expected:

```text
they remain distinct phrase ids
hits are recorded against the correct structured identity
deduplication does not collapse them
```

### 19.3 Exact-hit tests

Inject known exact 3-gram and 4-gram phrases at known offsets.

Expected:

```text
total_phrase_hd == 0
max_word_hd == 0
exact_flag == true
exact_hit_count_F increments
exact_cluster_count_F increments
```

### 19.4 Damaged-hit tests

Inject phrases with controlled mismatches.

Expected:

```text
hits pass only the profiles they should pass
max_word_hd gates are enforced
normalised_phrase_hd is reported correctly
```

### 19.5 All-hit no-cap tests

Create a dense candidate that produces many overlapping eligible hits.

Expected:

```text
all eligible hits emitted
raw_hit_count is high
cluster_count is low
no debug-example bound affects score-bearing output
```

### 19.6 Cluster tests

Use intervals that:

```text
overlap
touch
have a one-token gap
```

Expected:

```text
overlap -> same cluster
touch -> same cluster
one-token gap -> separate clusters
```

### 19.7 Anti-inflation tests

Create one local region that emits many related phrase hits.

Expected:

```text
raw_hit_count increases
cluster_count increments once per family
hit_to_cluster_ratio warns if high
```

### 19.8 Strict/normal separation tests

Expected:

```text
normal and strict summaries remain separate
strict hit does not automatically become normal hit unless the asset genuinely contains both identities
```

### 19.9 Null-generator determinism tests

Expected:

```text
same input + same seed -> identical null candidate
different seed -> different but valid null candidate
null preserves declared anchor/gap invariants
```

### 19.10 Offline mode tests

Expected:

```text
report_only never changes baseline winner
tie_break only acts after B_core tie
bounded_override only acts when override_guard passes
stable candidate id order resolves final ties
```

### 19.11 Python/C++ parity tests

Not for this phase, but prepare the golden fixtures now.

When C++ is added later, it must match Python on:

```text
hit records
cluster records
candidate summaries
support tuples
hard-pair outcomes
manifest hashes
```

---

## 20. Implementation order

Recommended safe order:

1. Define profile dataclasses / config objects.
2. Write profile manifest output.
3. Write phrase asset validation.
4. Write word-structured Hamming verifier.
5. Write Python scanner / candidate placement enumerator.
6. Emit hit records.
7. Implement overlap-or-touch clustering.
8. Emit cluster records and candidate summaries.
9. Implement support tuple comparison.
10. Implement hard-pair report-only mode.
11. Implement tie-break simulation.
12. Implement bounded-override simulation.
13. Implement anchor manifest generation.
14. Implement the three matched null generators.
15. Add concentration diagnostics.
16. Add readout summary.
17. Freeze golden fixtures for later C++ parity.

Do not start C++ until the Python reference behaviour is frozen and reviewed.

---

## 21. Open items that must be checked against the repo

These cannot be guessed without the current repo state:

1. Exact file paths for the new scorer.
2. Existing scorer interface names and return shapes.
3. Existing hard-pair report format.
4. Existing candidate/chunk ID schema.
5. Existing phrase asset loader schema.
6. Existing word/span-Hamming hit record shape.
7. Existing baseline comparator fields and whether `B_core` / `B_tail` already exist.
8. Existing manifest style and hash conventions.
9. Existing test fixture layout.

If these are not visible in the provided repo manifest / zip, stop and ask for the current files rather than inventing paths or APIs.

---

## 22. Suggested developer task statement

Implement the deterministic Python reference for the RDP Robust N-Gram Phrase Coherence Scorer.

Use the design in this brief exactly.

The implementation must be report-only and offline. It must not change live production ranking.

The scorer must:

- load the frozen profile ladder;
- evaluate exact word-structured phrase Hamming;
- emit every eligible hit for each declared profile;
- preserve structured phrase identity using `word_token_ids`;
- cluster score-bearing hits with global overlap-or-touch clustering;
- compute candidate support tuples;
- run `report_only`, `tie_break`, and `bounded_override` hard-pair simulations;
- generate the three matched nulls from upstream word/span support anchors;
- emit manifests, hit records, cluster records, candidate summaries, pair reports, null diagnostics, and a readout;
- fail loudly on contract violations;
- include tests for all-hit exactness, identity correctness, strict/normal separation, cluster semantics, null determinism, and offline comparator behaviour.

Keep the following report-only for now:

- diagnostic profiles `B2R`, `N3S_diag`, `F5D`;
- counts and log-counts;
- raw hit counts;
- global exact fields as primary comparators;
- skip/gapped phrase support;
- edit distance;
- joined-phrase Hamming;
- direct additive score merge;
- C++ backend.

The first goal is not to prove the scorer is globally optimal. The first goal is to produce an auditable hard-pair ledger showing whether phrase coherence adds break-constrained incremental evidence beyond the existing word/span-Hamming layer.
