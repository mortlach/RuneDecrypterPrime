# Final implementation memo for the RDP phrase coherence scorer

## Decision memo

The accepted baseline already fixes the big architectural choices: v1 uses exact word-structured phrase Hamming; Python is the reference implementation; C++ comes only after parity; there are no hit caps, no top-k truncation, no silent fallback, no merging of normal and strict cuts, and phrase evidence is positive support only. The frozen first ladder is also fixed: diagnostic `B2R`, `N3S_diag`, `F5D`; score-bearing `N3C`, `S3W`, `N4L`, `S34C`; and the first evaluation is offline under `report_only`, `tie_break`, and `bounded_override`. Those constraints strongly favour a conservative, explicit, cluster-based support system rather than any fitted scalar or count-weighted model. fileciteturn0file0 fileciteturn0file1

The most important final implementation choice is this: **treat phrase coherence as a small lexicographic tuple built from non-inflated local support units, not as a raw-hit score**. That recommendation follows directly from your prior feature audit, where a high-volume feature such as `repeated_3gram_rate` produced many rescues but many more breaks, and from the broader string-matching literature, where richer models such as weighted edit distance, skip n-grams, and weighted automata add flexibility but also more parameters, more state, or more smoothing machinery than your v1 contract allows. fileciteturn0file1 citeturn14view2turn13view1turn13view2

The concrete decisions I recommend are summarised below.

| Topic | Final v1 decision | Why |
|---|---|---|
| Phrase cluster | **Global overlap-or-touch interval cluster** over flattened token intervals, across all score-bearing hits | Best control against repeated-local-structure inflation without introducing a new gap parameter |
| Exact hits | **Fields, not a separate score-bearing family**; expose both per-family and global exact counts | Keeps exact evidence visible without doubling the ladder |
| Score unit | **Cluster counts**, not raw hit counts | Raw hits are easy to inflate in one region; clusters force locality collapse |
| Tuple order | **`S34C`, `N4L`, `S3W`, `N3C`**, then family exact-cluster counts, then `best_hit_signature` | Puts strongest confirmation first while keeping strict and normal separate |
| Tie-break mode | Phrase tuple inserted **after baseline core fields and before baseline tail fields** | Lets phrase evidence resolve weak baseline ties without acting like an additive score |
| Bounded override | Only when phrase winner has **top-family dominance** and baseline differs only on a predeclared weak field | Minimises breaks |
| Nulls | `offset_permute_null`, `window_collage_null`, `periodic_decoy_null`, all built from **real upstream support spans** | Preserves observed local evidence while breaking phrase order, without inventing a new damage model |
| Counts and log-counts | **Diagnostic only** | Count-based language-model weighting normally needs smoothing/back-off and stable corpus statistics, which your v1 explicitly avoids |

These choices are consistent with the accepted baseline, with the phrase-identity rule that keeps structured `word_token_ids` authoritative, and with established results showing that Hamming-style same-length substitution matching is a cleaner fit than edit distance when you want explicit fixed-boundary comparison and deterministic exact counting. Edit distance remains useful later if you explicitly decide to admit indels, but it should not be smuggled into this scorer through the back door. fileciteturn0file0 fileciteturn0file1 citeturn2search0turn14view2turn14view3turn8academia4

## Cluster and exact evidence

### Exact cluster definition

For v1, a **phrase coherence cluster** should mean:

> the connected component of all score-bearing phrase hits whose flattened token intervals overlap **or touch**.

Formally, for a hit `h` with start offset `s(h)` and phrase token length `L(h)`, define its interval as `[s(h), s(h) + L(h))`. Two hits are adjacent in the cluster graph if their intervals overlap or if one ends exactly where the other begins. A cluster is then the connected component under that relation. In implementation terms, if hits are sorted by `(start, end)`, a new cluster begins only when `next.start > current_cluster_end`; if `next.start <= current_cluster_end`, the hit stays in the current cluster and extends the end as needed. fileciteturn0file0 fileciteturn0file1

That definition is the right v1 choice because it is conservative in exactly the place your prior audit says conservatism is needed. It collapses bursts of near-duplicate local structure into one support unit, which directly addresses the failure mode behind `repeated_3gram_rate`. It also avoids a new “small gap” tolerance parameter, and therefore avoids quietly drifting towards skip/gapped phrase evidence, which is a distinct modelling family in both approximate matching and language modelling. fileciteturn0file1 citeturn15search0turn13view2

The alternatives are weaker for v1:

| Candidate definition | Recommendation | Reason |
|---|---|---|
| Overlapping intervals only | Reject | Misses zero-gap duplicates and allows back-to-back inflation |
| Overlapping or touching intervals | **Accept** | Conservative, deterministic, no extra parameter |
| Intervals within a small gap | Reject in v1 | Introduces a new gap hyperparameter; effectively starts a gapped-evidence model |
| Same start offset | Reject | Too brittle; shifted duplicates survive |
| Same phrase id | Reject | Phrase identity is not locality; one noisy region can still emit many ids |
| Same local word/span support region | Reject for scoring; keep only as audit metadata | Couples phrase scoring to upstream heuristics too tightly |

The implementation should compute clusters **globally across all score-bearing families**, not separately within each family. Then, for each cluster, store booleans such as `has_S34C`, `has_N4L`, `has_S3W`, `has_N3C`, and derived exact variants. This lets one local region be recognised as “multi-family confirmed” without letting it create more than one unit of support per family. That is the cleanest way to preserve strong local confirmation while blocking repeated-local-structure inflation. fileciteturn0file1

### How to avoid repeated-local-structure inflation

The anti-inflation rule should be explicit:

- **Cluster counts are score-bearing.**
- **Raw hit counts are diagnostic only.**
- **Within a cluster, each family contributes at most one unit.**
- **Within a cluster, exact evidence is also counted at most once per family.**

In other words, if one local span emits fifteen overlapping `N3C` hits from related phrase ids, that should still be worth only `N3C_cluster_count += 1`, not fifteen. If the same local span also emits one `S34C` hit and one exact `N4L` hit, then it can legitimately contribute `S34C_cluster_count += 1` and `N4L_exact_cluster_count += 1`, because that is not inflation within a family; it is cross-family confirmation of the same region. fileciteturn0file1

To make that auditable, each run should also emit these non-score-bearing diagnostics per family: `raw_hit_count`, `unique_phrase_id_count`, `unique_start_count`, `cluster_count`, `exact_hit_count`, `exact_cluster_count`, `hit_to_cluster_ratio`, and `top_phrase_share`. A score-bearing family whose `hit_to_cluster_ratio` or `top_phrase_share` explodes is exhibiting exactly the kind of concentration that broke earlier high-volume features. fileciteturn0file1

### Exact-hit handling

Exact hits should **not** become a separate score-bearing profile family. They should be exposed as **fields inside each score-bearing family**, plus two **global report fields**:

- per family: `exact_hit_count_F`, `exact_cluster_count_F`
- global: `exact_hit_count_global`, `exact_cluster_count_global`

That gives you exact evidence where it matters, but does not double the ladder. Making exact hits a separate profile family would introduce a second axis that is not really independent: exact hits are nested subsets of the same underlying Hamming profiles. In v1 that would mostly increase tuple width and reporting complexity without adding a truly orthogonal support signal. fileciteturn0file0 fileciteturn0file1

The score-bearing usage should be narrower still: only the **family exact-cluster counts** belong in the phrase support tuple, and only after the main family cluster counts. The **global exact fields** should stay visible in reports, but should not become earlier tuple components. That keeps exact evidence visible, auditable, and tie-breaking, without letting one locally exact island dominate the whole comparator. fileciteturn0file0

## Promotion gates and matched nulls

### Practical promotion checklist

Because your prior audit showed that “lots of rescues” is not enough if the same feature also creates many breaks, the promotion checklist should be divided into **mandatory gates** and **review diagnostics**. The mandatory gates determine whether a family can graduate from report-only status to future tie-break or override candidacy; the diagnostics explain why it passed or failed. fileciteturn0file1

The mandatory gates I recommend are:

| Gate | Required for tie-break candidacy | Required for bounded-override candidacy | Why |
|---|---|---|---|
| Contract integrity | Must pass | Must pass | No caps, no dropped hits, deterministic manifest, fail-loud behaviour are non-negotiable |
| Positive pair utility | `rescues >= 5` or at least 1% of evaluated hard pairs, `net_rescues > 0` | Same, plus stronger precision | Avoids promoting vanishingly rare or negative-value profiles |
| Rescue precision | `rescues / (rescues + breaks) >= 0.85` | `>= 0.95`, and ideally `breaks == 0` on the main evaluation set | Override modes must be stricter than tie-break modes |
| Incremental value beyond baseline word/span | At least 3 rescues that are not already explained by stronger baseline fields | Same | This scorer is second-stage support, so it must add something new |
| Matched-null lift | Support rate on real winners at least **2×** the largest support rate on the three matched nulls | Same | Prevents promotion of features that also “light up” on scrambled local evidence |
| Concentration control | `top_phrase_share <= 0.35` and median `hit_to_cluster_ratio <= 3` | Same, with no concentration exceptions | Guards against the old repeated-local-structure failure mode |
| Cross-cut sanity | Strict precision must not be worse than the corresponding normal family | Same | Strict is supposed to be the precision cut, not just a second view |
| Bucket stability | No evaluated damage bucket should show more breaks than rescues | Same | A future production family should not be held up by one hidden bad regime |

Those thresholds are not claims about universal truth; they are recommended starting gates for *your* v1 review standard. Their purpose is to encode your design lesson that precision of support, incremental value, and robustness to false local structure matter more than raw rescue volume. fileciteturn0file1

The review diagnostics should then include: per-damage-bucket rescues and breaks, order-specific contributions, exact-hit share, phrase-id diversity, correlation with existing span/word layers, null-family activation rates, and the effect of counts or log-counts if you log them diagnostically. Those are useful to inspect, but they should not decide promotion by themselves. Count-based language-model practice is a useful reminder here: once counts begin to matter directly, smoothing and back-off choices matter as well, and the system quickly stops being a simple explicit support tuple. citeturn13view0turn13view2

### Exact null generator definitions

The right matched nulls for this scorer must start from **real candidates that already have upstream local word/span support**, because a random 29-symbol stream is not the operational null after your first-stage filter. Every null below is therefore built from **observed upstream support anchors**, not from synthetic random mutations. That preserves the actual damage texture and local word-like evidence while testing whether phrase coherence survives when order or composition is broken. fileciteturn0file1

Before defining the three nulls, define one shared input object:

> **Anchor manifest**: merge upstream word/span hits by overlap-or-touch into non-overlapping local support regions; in each region choose one canonical anchor span by lexicographic strength `(lower HD, longer length, stricter cut, earlier start)`; keep the original gap segments between anchor regions unchanged.

This anchor manifest is deterministic, ties back to the existing word/span layer, and avoids inventing a new damage model. fileciteturn0file1

The nulls should then be:

| Null | Input | Preserves | Destroys | Deterministic construction | Required diagnostics |
|---|---|---|---|---|---|
| `offset_permute_null` | One candidate’s anchor manifest | Exact anchor-span contents; anchor count; anchor lengths; original gap lengths; candidate-level damage texture | Original local ordering and adjacency between supported spans | Permute anchor spans among anchor slots by a manifest-seeded derangement; keep gaps fixed | per-family hit/cluster/exact counts; support tuple; raw-to-cluster ratio; original-vs-null lift |
| `window_collage_null` | Anchor manifests from same evaluation bucket | Real observed anchors; matched support density; matched length/support bins; real gap geometry | Candidate-specific phrase continuity across anchors | For each target anchor slot, choose a donor anchor from another candidate in the same bucket by deterministic round-robin nearest-bin matching, excluding self | same as above, plus donor-bucket coverage and seam concentration |
| `periodic_decoy_null` | One candidate’s anchor manifest | Real anchor contents; original slot-length distribution; original gap lengths | Lexical diversity and natural ordering; replaces them with repeated local structure | For each anchor-length bin, fill every slot with the strongest anchor from that same bin, cycling deterministically if two representatives are used | same as above, plus `top_phrase_share` and `hit_to_cluster_ratio` inflation under repetition |

`offset_permute_null` is the cleanest “same local evidence, wrong order” null. `window_collage_null` is the best “same level of local evidence, but borrowed from elsewhere” null. `periodic_decoy_null` is the stress test built specifically to catch another `repeated_3gram_rate`-style trap. All three preserve real local material and therefore avoid inventing a bespoke synthetic corruption process. fileciteturn0file1

Two constraints matter here. First, the nulls must be **deterministic**: every permutation or donor assignment must come from a manifest seed and stable sorting, never from unrecorded randomness. Second, the nulls must not rely on gapped or skip-gram scoring rules that are not in the production model. Skip n-grams and spaced seeds are real techniques, and they can improve recall under sparse conditions, but the literature treats them as an additional modelling dimension, not a free extra on top of exact fixed-boundary matching. That is exactly why they belong outside v1’s production comparator. citeturn13view2turn15search0turn11academia3

## Support tuple and offline decision modes

### Exact support tuple

I recommend the following **exact support tuple ordering** for v1:

```text
T(c) =
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

with lexicographic comparison, larger being better. `B2R`, `N3S_diag`, and `F5D` stay fully diagnostic and do not enter `T(c)`. `raw_hit_count`, `log_count`, `exact_hit_count_global`, and `exact_cluster_count_global` also stay out of `T(c)` and remain report-only. fileciteturn0file0 fileciteturn0file1

The one ordering change I do recommend versus your draft is this:

> **Put `N4L` before `S3W`.**

The reason is pragmatic rather than dogmatic. Your accepted baseline already treats 3-grams as the centre and 4-grams as stronger confirmation. A normal-cut 4-word long cluster carries more explicit ordered-boundary information than a strict-cut 3-gram under the looser “word analogue” threshold, and the prior audit did not show that strict alone already cleans up false highs strongly enough to make strict-3 automatically safer than normal-4. In a no-fit tuple, the harder-to-fake longer-order event should therefore outrank the looser strict trigram event, while the `S34C` family remains the top precision bucket. fileciteturn0file1 citeturn13view0

That recommendation also agrees with general n-gram modelling practice: higher-order evidence is more informative but sparser, which is why conventional language models need smoothing and interpolation. Your v1 explicitly avoids that machinery, so the cleanest equivalent is not to blend the families into one score, but to order them lexicographically and let stronger, rarer confirmation sit earlier in the tuple. citeturn13view0turn13view2

I recommend defining `best_hit_signature` as the lexicographically best single hit after family counts tie:

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

This is a tie-break and audit field only. It should never outrank the family cluster counts themselves. fileciteturn0file0

### Exact offline comparison rules

To make the three offline modes precise, the baseline comparator must be exposed as two manifest-declared blocks:

- `B_core`: the existing phrase-blind **core** ranking fields
- `B_tail`: the existing phrase-blind **tail/tie-break** fields

If the current system does not already expose that partition, define it now before coding the phrase scorer, because otherwise “tie-break” and “bounded override” are not mechanically well-defined. fileciteturn0file0

The three offline modes should then be:

| Mode | Exact rule |
|---|---|
| `report_only` | Keep the current baseline result unchanged. Also compute `phrase_cmp = lexcmp(T(a), T(b))` and log whether it agrees, disagrees, or ties. |
| `tie_break` | Compare `B_core(a)` vs `B_core(b)`. If unequal, baseline wins. If equal, compare `T(a)` vs `T(b)`. If still equal, compare `B_tail(a)` vs `B_tail(b)`. If still equal, use stable candidate id order. |
| `bounded_override` | Compare `B_core_strong(a)` vs `B_core_strong(b)`, where `B_core_strong` is `B_core` with its single weakest field removed. If unequal, baseline wins. If equal, phrase may replace that weakest field **only if** `override_guard` passes. Otherwise fall back to the removed weak field, then `B_tail`, then stable id. |

The exact `override_guard` should be:

```text
override_guard(a, b) is true iff

1. T(a) > T(b), and
2. the first differing component between T(a) and T(b)
   is one of:
   {S34C_cluster_count, N4L_cluster_count,
    S34C_exact_cluster_count, N4L_exact_cluster_count}, and
3. a has at least one top-family cluster:
   (S34C_cluster_count + N4L_cluster_count) >= 1, and
4. b has no top-family cluster:
   (S34C_cluster_count + N4L_cluster_count) == 0.
```

This is deliberately narrow. It means a candidate can bounded-override only with clear top-family phrase coherence, never merely with lower-family accumulation. That is the right v1 rule if your objective is “minimise breaks first”. fileciteturn0file0 fileciteturn0file1

The logic behind these rules is the same logic behind the rest of the design: phrase coherence is a discrete support layer, not an additive score. `report_only` measures value without intervention. `tie_break` lets phrase evidence resolve weak existing ties. `bounded_override` is reserved for cases where phrase evidence is both stronger and more specific than the weakest remaining baseline discriminator. fileciteturn0file0

## First experiment and implementation checklist

### Frozen first-run profile ladder

I recommend instantiating the frozen ladder as follows. This assumes the shorthand expands in the obvious way from the earlier profile families in your prior note; if your local abbreviations differ, keep the thresholds below and only remap the labels in the manifest. fileciteturn0file1

| Profile | Orders | Cuts | Min phrase token length | Max total HD | Max word HD | Role | Risk |
|---|---|---:|---:|---:|---:|---|---|
| `N3C` | `{3}` | `normal` | 8 | 2 | 1 | score-bearing | main normal coverage |
| `S3W` | `{3}` | `strict` | 7 | 2 | 2 | score-bearing | strict but looser threshold; medium risk |
| `N4L` | `{4}` | `normal` | 10 | 3 | 2 | score-bearing | stronger confirmation, sparser |
| `S34C` | `{3,4}` | `strict` | 8 | 2 | 1 | score-bearing | highest precision confirmation |
| `B2R` | `{2}` | `normal, strict` | 7 | 2 | 2 | diagnostic | danger of volume inflation |
| `N3S_diag` | `{3}` | `normal` | 7 | 2 | 2 | diagnostic | softer normal trigram view |
| `F5D` | `{5}` | `normal, strict` | 12 | 3 | 2 | diagnostic | rare high-confidence support |

Exact `HD = 0` events are **not** separate rows; they are embedded as per-family exact fields and global report fields. Counts and log-counts remain diagnostic only. fileciteturn0file0 fileciteturn0file1

### Recommended aggregate fields

The minimum safe aggregate set is:

| Field group | Fields |
|---|---|
| Score-bearing tuple | `S34C_cluster_count`, `N4L_cluster_count`, `S3W_cluster_count`, `N3C_cluster_count`, aligned family `exact_cluster_count`s, `best_hit_signature` |
| Global diagnostics | `exact_hit_count_global`, `exact_cluster_count_global`, `raw_hit_count_by_family`, `unique_phrase_id_count_by_family`, `unique_start_count_by_family`, `hit_to_cluster_ratio_by_family`, `top_phrase_share_by_family` |
| Cluster records | `cluster_id`, `start`, `end`, `families_present`, `best_hit_signature`, `phrase_ids_present`, `exact_flags_present` |
| Run integrity | eligible hit count, counted hit count, asset hashes, profile manifest hash, cluster mode, tuple order, null seed |
| Null diagnostics | per-null family cluster counts, exact cluster counts, raw hits, tuple, real-vs-null lift |

This aggregate set is intentionally narrow. It is enough to rank pairs, inspect inflation, and audit false support, without drifting into fitted scoring or count-weighted language modelling. Conventional count-based n-gram work is useful here mainly as a warning: once counts start to matter directly, smoothing choice and asset coverage start to matter too. That is why count and log-count fields should stay out of `T(c)` in v1. fileciteturn0file0 citeturn13view0turn13view2

### Hard-pair report fields

For each evaluated hard pair, I recommend emitting exactly these report fields:

| Field | Purpose |
|---|---|
| `pair_id`, `expected_better_id`, `expected_worse_id` | ground-truth bookkeeping |
| `baseline_cmp` | current production phrase-blind outcome |
| `phrase_cmp` | pure `T(a)` vs `T(b)` result |
| `report_only_outcome` | agree / disagree / tie |
| `tie_break_outcome` | simulated comparator outcome |
| `bounded_override_outcome` | simulated comparator outcome |
| `first_diff_tuple_component` | where phrase comparison became decisive |
| `better_tuple`, `worse_tuple` | full phrase support tuples |
| `better_best_hit_signature`, `worse_best_hit_signature` | audit of strongest local evidence |
| `better_cluster_summary`, `worse_cluster_summary` | local support localisation |
| `rescue_or_break_by_mode` | direct evaluation label |
| `null_lift_summary` | whether support survives matched null checks |
| `concentration_flags` | high `top_phrase_share`, high `hit_to_cluster_ratio`, single-cluster domination |

The key review object is not the absolute count output; it is the **pair ledger**. That is where you will see whether a family truly contributes precision, whether a rescue is incremental beyond baseline word/span evidence, and whether a candidate won only because one local pattern exploded. fileciteturn0file1

### Pass and fail criteria for the first run

The first run should be considered **review-pass** only if all of the following hold:

- every contract test passes, including all-hit exactness, no-cap invariants, manifest integrity, and deterministic reruns;
- `report_only` shows positive net rescues for the score-bearing tuple;
- `tie_break` simulation achieves positive net rescues with precision at or above **0.90**;
- `bounded_override` simulation produces **no breaks** on the primary hard-pair set;
- top-family phrase support has a real-vs-null lift of at least **2×** against the strongest matched null;
- no score-bearing family breaches the concentration guardrails (`top_phrase_share > 0.35` or median `hit_to_cluster_ratio > 3`). fileciteturn0file1

The run should be considered **hard-fail** if any eligible hits are dropped, if normal/strict separation leaks, if phrase identity collisions occur because structured `word_token_ids` were not respected, if exact counts exceed total counts, or if any offline mode depends on an undeclared baseline-field partition. Those are contract errors, not modelling disappointments. fileciteturn0file0 fileciteturn0file1

### What remains report-only

For this first implementation cycle, the following should remain report-only:

- all live production use of phrase evidence;
- all diagnostic families: `B2R`, `N3S_diag`, `F5D`;
- raw hit counts, log-counts, continuation-style ideas, and any count weighting;
- global exact fields as primary comparators;
- any skip/gapped phrase support;
- any direct additive score merge with existing word/span ranking;
- any C++ backend before exact Python parity is frozen. fileciteturn0file0 fileciteturn0file1

### What to implement next

The next thing to implement is therefore not another design search. It is a **deterministic Python reference** with these exact pieces:

1. the frozen profile manifest above;
2. global overlap-or-touch clustering for score-bearing hits;
3. per-family and global exact fields;
4. the exact support tuple  
   `S34C > N4L > S3W > N3C`, then aligned exact-cluster counts, then `best_hit_signature`;
5. the three matched null generators defined from upstream anchor manifests;
6. the three offline comparators: `report_only`, `tie_break`, `bounded_override`;
7. the pair ledger and concentration diagnostics;
8. fail-loud contract tests for no-cap exactness, identity correctness, and rerun determinism. fileciteturn0file0 fileciteturn0file1

That is the smallest safe next step because it resolves the remaining ambiguities without reopening the broad model decision. It keeps the scorer faithful to your accepted baseline, protects against the specific inflation failure you already observed, and creates an audit trail strong enough that a later C++ port can be judged against a stable behavioural contract rather than against a moving design target. fileciteturn0file0 fileciteturn0file1