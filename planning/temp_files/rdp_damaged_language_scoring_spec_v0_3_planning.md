# RDP Damaged-Language Scoring Spec

## Dictionary Tags, Confirmed Cicada References, Span-Hamming Features, and N-gram Evidence

Version: `v0.3-planning`

Purpose: implementation-ready design, not final code.

This version keeps the full HD ladder as a first-class feature matrix. It adds explicit metadata for confirmed Cicada / puzzle / art / literature / source-reference words, and fixes the proper-noun / cultural-term policy so it is consistent.

---

# 1. Core aim

We are not building a general English dictionary.

We are building a controlled scoring system for **damaged RDP/no-WLI candidate text**, where candidate outputs may be only about **40–50% correct** at the rune/letter level.

The system must help decide:

```text
Does this candidate look more like damaged plaintext than bad/null text?
```

not merely:

```text
Does this candidate contain things that resemble dictionary words?
```

The final scorer should use two separate evidence layers:

```text
1. Span-Hamming word evidence
   Local damaged-word evidence.

2. N-gram phrase evidence
   Ordered natural-language / phrase evidence.
```

They share the same word-tag policy, but they are not the same scorer.

---

# 2. Existing relevant data

## 2.1 Current Hamming dictionary policy files

The current strict/normal/broad/research word-list files should be treated as **input metadata**, not trusted ground truth.

Important rule:

```text
Never carry old selected bits forward automatically.
```

The old strict list is known to be too broad.

## 2.2 Google n-gram dataset

The Mortlach Google n-gram repository is relevant because it is already shaped for this kind of work.

The important planning assumption is:

```text
The dataset is not arbitrary raw Google n-grams.
It is already partly RDP-shaped.
But it is still much larger than we can trust blindly.
```

Therefore:

```text
Do not use n-gram membership as automatic word admission.
Use filtered n-grams as phrase/order evidence.
Use strong n-gram contexts as reviewable support.
```

---

# 3. Final word tags

Every word gets one of three final tags:

```text
S = strict
N = normal
X = reject
```

Bit mapping:

```text
S -> strict=1, normal=1
N -> strict=0, normal=1
X -> strict=0, normal=0
```

Default rule:

```text
Every word starts as X.
A word enters S or N only by explicit admission.
```

This is the key correction compared with the failed manual-review draft.

Important:

```text
Confirmed Cicada/reference metadata is not a fourth final tag.
It is supporting metadata used to explain and protect decisions.
```

---

# 4. Tag definitions

## 4.1 Strict: `S`

Strict means:

```text
Obvious everyday written word
OR
strong Cicada / puzzle / crypto / rune / symbolic word
OR
word with strong positive evidence from good partial RDP candidates and acceptable noise.
```

Strict is a high-precision scoring list.

Strict does **not** mean:

```text
technically valid English
recognisable to a well-read person
interesting vocabulary
moderately common
present in old strict
present in a Google n-gram file
present in a confirmed source text but otherwise weak
```

Examples already accepted as strict-style:

```text
water
people
which
about
right
world
proof
logic
graph
theorem
ratios
runes
runic
glyph
crypt
morse
caesar
rotor
nulls
koans
typos
digram
hamming
```

Special accepted strict examples:

```text
koans = S
typos = S
caesar = S, because Caesar cipher / puzzle context
rotor = S, because Enigma / cipher context
```

## 4.2 Normal: `N`

Normal means:

```text
Most normal readers would recognise it in written text,
or it is useful in an expected clue domain,
or it is a confirmed Cicada/source-reference word worth keeping,
but it is not clean/strong enough for strict.
```

Normal is broader than strict, but it is **not** an extended dictionary.

Examples:

```text
clefs
mason
egypt
china
japan
irish
welsh
dutch
indian
prism
lemma
gauss
quark
caret
cache
motto
serif
telex
micro
maser
congeal
louts
dulls
theres
didnt
theyre
doesnt
wasnt
arent
youve
whats
heres
syringing
```

Missing-apostrophe contractions are `N`, not `S`:

```text
didnt
theyre
doesnt
wasnt
arent
youve
whats
heres
theres
```

Reason:

```text
Plausible if apostrophes are stripped during normalisation, but not clean strict words.
```

## 4.3 Reject: `X`

Reject means the word is not useful enough for the default span-Hamming/n-gram scoring policy.

Reject classes:

```text
slang / chat spelling
typo-looking
proper-name-only
surname/person-name only
specialist science jargon
medical/botany/taxonomy/chemistry jargon
obscure archaic word
rare animal/plant name
odd plural
weird derivative
foreign fragment
dialect form
extended dictionary baggage
too obscure for normal reader recognition
too noisy under span-Hamming tests
unverified Cicada/fan-theory vocabulary
copycat puzzle vocabulary
```

Examples already calibrated as `X`:

```text
nonce
schwa
kudzu
ombre
lariat
throve
churl
clews
keening
motet
tippy
rubberise
aerosolise
shelffuls
teemingness
gonna
gotta
wanna
kinda
dunno
outta
lemme
sorta
```



---

# 5. Topic and reference-support rules

Cicada-style material can include art, music, literature, myth, religion, maths, language, symbolic references, source texts, and cryptography.

Therefore:

```text
Do not reject all non-everyday words automatically.
But do not promote them to strict unless they are strongly puzzle-relevant,
ordinary enough, or statistically proven useful.
```

## 5.1 Strong puzzle / crypto / symbolic terms

Usually `S`:

```text
runes
runic
glyph
crypt
morse
caesar
rotor
nulls
koans
hamming
digram
graph
proof
logic
theorem
ratios
```

Possible `S` or `N`, depending on noise and spelling policy:

```text
pgp
openpgp
rsa
xor
tor
onion
outguess
qr
url
base64
vigenere
atbash
gematria
bookcode
transposition
hash
```

Default caution:

```text
A term being used somewhere in a puzzle does not automatically make it S.
S is for strong scoring words.
N is for useful but broader clue-domain words.
```

## 5.2 Art / music / literary / religious clue terms

Usually `N`:

```text
clefs
pieta
motif
tonal
bards
altar
saint
monks
abbot
torah
jesus
moses
angels
devil
demon
satan
bible
psalm
```

Some may be `S` if strongly puzzle-symbolic, already accepted, or ordinary enough:

```text
latin
liber
roman
greek
norse
mythic
horus
wotan
freya
```

But the rule is cautious:

```text
Proper nouns are usually N or X, not S.
Only promote to S if strongly symbolic, puzzle-specific, statistically useful,
or also an ordinary word.
```

---

# 6. Confirmed Cicada / source-reference metadata

This is the main new policy addition in `v0.3-planning`.

Some words are not ordinary English and may look like proper nouns, literary baggage, art references, religious terms, or specialist puzzle terms.

For Cicada/RDP scoring, these must not be silently rejected if they are tied to confirmed Cicada material.

This category is metadata, not a fourth final tag.

Required fields:

```text
confirmed_ref_keep
confirmed_ref_class
confirmed_ref_confidence
confirmed_ref_source
confirmed_ref_note
```

Allowed `confirmed_ref_class` values:

```text
none
cicada_pgp_verified_text
cicada_liber_primus_text
cicada_confirmed_method
cicada_confirmed_tool
cicada_confirmed_source_text
cicada_confirmed_art_or_music
cicada_confirmed_author_or_figure
cicada_confirmed_religious_or_mythic_reference
cicada_confirmed_infrastructure
cicada_solver_archive_reference
```

Allowed `confirmed_ref_confidence` values:

```text
pgp_verified
artifact_verified
archive_documented
solver_consensus
unverified_reject
```

Definition:

```text
A confirmed Cicada/RDP reference word is a word or term that appears in,
or directly names, one of:

1. a PGP-verified Cicada communication;
2. solved/accepted Liber Primus text;
3. a confirmed puzzle method, cipher, tool, medium, or infrastructure item;
4. a confirmed source text, artwork, author, literary work, music reference,
   religious/mythic reference, or other cultural source used in the puzzle chain;
5. a confirmed solver-archive reference with source traceability.
```

Non-examples:

```text
fan theory terms
unsigned claimed puzzle terms
later copycat puzzle terms
fiction/pop-culture inspired by Cicada
general occult/mystical/literary words with no confirmed Cicada source
```

Policy:

```text
confirmed_ref_keep prevents automatic rejection solely as:

proper-name-only
cultural term
literary term
art reference
music reference
myth/religion term
specialist puzzle vocabulary

It does not automatically promote a word to S or N.
```

Final tag policy remains:

```text
S = ordinary everyday word OR core puzzle/crypto/RDP term OR statistically proven strong signal
N = recognisable or confirmed clue-domain/reference word, but not clean enough for S
X = rejected/noisy/unconfirmed/too obscure/not useful for default scoring
```

Most confirmed source-text names, authors, places, and literary references should be `N`, not `S`.

Only promote to `S` if the term is also common, central to the puzzle mechanics, or manually admitted with strong evidence.

## 6.1 What a Cicada 3301 puzzle word is

For this project, a **Cicada 3301 puzzle word** means:

```text
A word or term that belongs to a confirmed Cicada puzzle step,
confirmed Cicada communication,
confirmed puzzle method,
confirmed puzzle tool,
confirmed source text,
confirmed artwork/music reference,
or accepted Liber Primus/RDP textual material.
```

A Cicada puzzle word does **not** mean:

```text
A word that merely sounds occult, mystical, literary, or cryptic.
A word from Discord speculation.
A word from a fan theory.
A word from an unsigned claimed puzzle.
A word from a copycat puzzle.
A word from a later fiction/pop-culture work inspired by Cicada.
```

## 6.2 Examples of confirmed-reference keep words

These examples are not all automatically `S`.

They are examples of words that should receive confirmed-reference metadata if the source check passes.

Usually `S` or strong `N`:

```text
pgp
openpgp
runes
runic
liber
primus
onion
tor
outguess
qr
rsa
xor
base64
hash
caesar
vigenere
atbash
gematria
bookcode
```

Usually `N keep`, not `S`:

```text
agrippa
mabinogion
blake
crowley
emerson
goya
bach
escher
hofstadter
rasputin
```

Default treatment:

```text
If the term is a method/tool/core puzzle mechanism, consider S or N.
If the term is a source text, author, artist, artwork, or myth/religion reference, usually N.
If the term is name-only and weakly useful, keep it reviewable but do not promote silently.
```

---

# 7. Proper nouns and cultural terms

This section replaces the contradictory earlier rule.

People/surnames/names-only are `X` by default.

Countries, places, languages, source-text names, authors, mythic names, religious terms, and cultural references are not `S` by default.

They may be `N` if they are:

```text
ordinary reader-recognisable,
confirmed Cicada/RDP reference words,
useful clue-domain terms,
or statistically useful and not too noisy.
```

They may be `S` only if they are:

```text
strongly puzzle-central,
also ordinary/common words,
or manually promoted with explicit evidence.
```

Examples:

```text
egypt = N, if treated as ordinary cultural/geographical vocabulary
china = N, if treated as ordinary cultural/geographical vocabulary
japan = N, if treated as ordinary cultural/geographical vocabulary
irish = N
welsh = N
dutch = N
indian = N
```

Examples usually `X` unless confirmed reference evidence applies:

```text
tajik
james
george
wayne
isaac
clark
```

Rule:

```text
Do not globally reject all countries/languages/cultural terms.
Do not globally admit them either.
Admit common ones to N with a reason.
Keep confirmed Cicada references reviewable with confirmed_ref metadata.
```

---

# 8. Required metadata

Every output row must preserve enough metadata to explain its tag.

Required fields:

```text
word
rune_length
count
runes
hash

old_strict
old_normal
old_broad
old_research

manual_tag
manual_reason

semantic_flags
hard_reject_flags
topic_flags

confirmed_ref_keep
confirmed_ref_class
confirmed_ref_confidence
confirmed_ref_source
confirmed_ref_note

hd0_neighbours
hd1_neighbours
hd2_neighbours
hd3_neighbours
hd4_neighbours
hd5_neighbours
hd6_neighbours

null_match_rate_by_hd
bad_candidate_match_rate_by_hd
positive_candidate_match_rate_by_hd
lift_by_hd

ngram_support_summary
ngram_best_context
ngram_rescue_candidate

proposed_tag
decision_source
admission_reason
reject_reason
review_priority
```

Allowed `decision_source` values:

```text
manual_override
hard_rule_reject
semantic_admission
topic_admission
confirmed_ref_admission
statistical_admission
statistical_reject
ngram_review_support
review_required
```

Important distinction:

```text
manual X != default X
```

Manual `X` means explicitly reviewed and rejected.

Default `X` means not admitted.

---

# 9. Hard invariants

These must be enforced in code/tests.

```text
1. Default tag is X.

2. Existing strict/normal bits must never be carried forward automatically.

3. Every S word must have an admission_reason.

4. Every N word must have an admission_reason.

5. Every non-X word must have decision_source != unknown.

6. Manual overrides always win.

7. Hard reject flags force X unless explicitly overridden.

8. S requires stronger evidence than N.

9. Any S word admitted through puzzle/Cicada relevance must have a topic flag
   or confirmed_ref metadata.

10. Output must include reason metadata for every row.

11. Any non-X word with no reason is invalid.

12. Any S word with a hard reject flag is invalid unless manually overridden.

13. Any word silently carried forward from old strict/normal is invalid.

14. High-HD features must not be trusted without null statistics.

15. N-gram hits must not rescue words silently; they must create reviewable
    admission evidence.

16. confirmed_ref_keep must not silently promote a word to S or N.

17. confirmed_ref_keep with confirmed_ref_confidence = unverified_reject must
    not admit the word.

18. Any claimed Cicada-specific admission must record source/provenance.

19. Unsigned/copycat/fan-theory Cicada terms must not be admitted as confirmed
    references.

20. Full HD ladder generation is first-class for the current planning version.
    Do not silently prune high-HD rungs before feature/null evaluation.
```

---

# 10. Span-Hamming feature principle

HD is not one global setting.

Each word length gets an **HD ladder**.

Low-HD rungs provide strong evidence.

Higher-HD rungs provide damaged-text evidence and must be null-normalised.

For each feature, record:

```text
observed_count
expected_null_count
excess = observed_count - expected_null_count
lift = observed_count / expected_null_count
```

Do not trust raw match counts alone.

The actual question is:

```text
Does this feature separate better partial candidates from bad/null candidates?
```

---

# 11. Span-Hamming HD ladder

This full ladder is first-class in `v0.3-planning`.

Do not descope it during dictionary rebuild.

Do not prune it before null/bad/positive evaluation.

## 11.1 Full feature matrix

```text
Length 1:
  HD0

Length 2:
  HD0

Length 3:
  HD0, HD1

Length 4:
  HD0, HD1

Length 5:
  HD0, HD1

Length 6:
  HD0, HD1, HD2

Length 7:
  HD0, HD1, HD2

Length 8:
  HD0, HD1, HD2, HD3

Length 9:
  HD0, HD1, HD2, HD3

Length 10:
  HD0, HD1, HD2, HD3, HD4

Length 11:
  HD0, HD1, HD2, HD3, HD4

Length 12:
  HD0, HD1, HD2, HD3, HD4, HD5

Length 13:
  HD0, HD1, HD2, HD3, HD4, HD5

Length 14:
  HD0, HD1, HD2, HD3, HD4, HD5
```

Optional experimental rung:

```text
Length 13–14:
  HD6
```

But HD6 is disabled unless null tests show useful separation.

## 11.2 Reasoning

Low-HD long-word features are still valuable:

```text
If a candidate has a tasty long exact/near-exact word match, it may deserve an early keep.
```

Higher-HD long-word features are needed because candidate text may be around 40–50% damaged.

So both are useful:

```text
low HD = strong keep evidence
high HD = damaged-text ranking evidence
```

---

# 12. Strict versus normal HD use

For `v0.3-planning`, both strict and normal selected sets should be evaluated across the full enabled ladder.

Policy:

```text
strict:
  generate full enabled HD ladder

normal:
  generate full enabled HD ladder
```

Reason:

```text
We do not yet know how large the strict list will be, especially at long lengths.
We also do not yet know which high-HD strict/normal rungs separate positives from nulls.
So feature generation should stay complete.
```

However:

```text
Full generation does not mean full trust.
Full generation does not mean equal weight.
Full generation does not mean every rung enters the final combined score.
```

Final use must be decided from null/bad/positive results:

```text
A rung may be kept, downweighted, disabled, or made review-only.
But it must not be silently removed before the feature panel proves it is noisy.
```

---

# 13. Span-Hamming feature names

Use explicit feature names.

Examples:

```text
strict_len05_hd0
strict_len05_hd1

normal_len05_hd0
normal_len05_hd1

strict_len10_hd0
strict_len10_hd1
strict_len10_hd2
strict_len10_hd3
strict_len10_hd4

normal_len10_hd0
normal_len10_hd1
normal_len10_hd2
normal_len10_hd3
normal_len10_hd4

strict_len14_hd0
strict_len14_hd1
strict_len14_hd2
strict_len14_hd3
strict_len14_hd4
strict_len14_hd5

normal_len14_hd0
normal_len14_hd1
normal_len14_hd2
normal_len14_hd3
normal_len14_hd4
normal_len14_hd5
```

Each feature should report:

```text
observed_count
expected_null_count
excess
lift
candidate_rank_effect
control_breaks
rescues
```

---

# 14. Span-Hamming gates

## 14.1 Fast keep gate

Purpose:

```text
Catch rare strong evidence quickly.
```

Triggered by:

```text
long strict HD0 match
long strict HD1 match
multiple medium-long strict low-HD matches
very high lift from low-HD long-word features
```

This gate should be conservative.

## 14.2 Damaged-text rank gate

Purpose:

```text
Rank damaged candidates by whether they look more word-like than null text.
```

Uses the full enabled feature panel, with emphasis likely to come from:

```text
strict length 8–14 HD2–HD5 excess over null
normal length 6–14 HD1–HD5 excess over null, if proven useful
```

This gate must be null-normalised.

High-HD normal features are allowed to exist, but must earn their final weight.

---

# 15. N-gram evidence layer

## 15.1 Role

N-grams are not a replacement for span-Hamming.

They answer a different question:

```text
Do ordered word sequences look like natural language?
```

Span-Hamming asks:

```text
Do damaged local spans look word-like?
```

So:

```text
span-Hamming = damaged local word evidence
n-grams = phrase/order/natural-language evidence
```

## 15.2 Do not dump n-gram words into the dictionary

Do not use this rule:

```text
word appears in Google n-grams -> admit word
```

That would reintroduce dictionary bloat.

Instead:

```text
Use S/N/X tags to filter n-grams.
Use strong n-gram evidence as reviewable support, not silent admission.
```

A word can be rescued to `N` if:

```text
it appears in strong, high-quality n-gram contexts
AND it is not hard-reject
AND it has useful topic, confirmed-reference, or positive-candidate support
```

N-gram support should rarely promote a word to `S`.

---

# 16. N-gram tag classes

For 2-grams:

```text
S S -> strict n-gram
S N -> normal n-gram
N S -> normal n-gram
N N -> broad normal n-gram
any X -> reject unless manually rescued for review
```

For 3–5-grams:

```text
all S words       -> high-trust phrase evidence
S/N mix, no X     -> normal phrase evidence
any X             -> reject unless manually rescued for review
proper-name-heavy -> downweight or reject unless confirmed_ref evidence applies
```

Confirmed-reference words inside n-grams:

```text
confirmed_ref_keep words may prevent immediate rejection of a phrase,
but they do not make the phrase strict by themselves.
```

---

# 17. N-gram feature matrix

Start exact only.

```text
ngram2_strict_exact
ngram2_normal_exact

ngram3_strict_exact
ngram3_normal_exact

ngram4_strict_exact
ngram4_normal_exact

ngram5_strict_exact
ngram5_normal_exact
```

For each feature:

```text
hit_count
sum_log_count
max_log_count
top_k_sum_log_count
longest_ngram_hit
expected_null_score
excess_over_null
lift_over_null
```

Use:

```text
score_per_ngram = log(count + 1)
```

Then aggregate.

---

# 18. N-gram use in WLI versus no-WLI

## 18.1 WLI / LP case

This is the easier and stronger use case.

If word lengths are known:

```text
1. Select matching n-gram shape file.
2. Check candidate word sequence against that n-gram set.
3. Score exact n-gram matches by log count.
4. Compare with null/bad candidates.
```

The Mortlach n-gram data is already organised around word/rune length shapes, making it especially useful for LP/WLI-style scoring.

## 18.2 no-WLI case

Harder, because segmentation is unknown.

Use only when there are candidate word windows or candidate segmentations.

Possible no-WLI flow:

```text
1. Generate span-Hamming word hits.
2. Find adjacent compatible word-hit sequences.
3. Check whether the ordered sequence appears in filtered n-grams.
4. Score phrase evidence.
5. Normalise by number of segmentations tried.
```

Important no-WLI metadata:

```text
number_of_segmentations_tried
matches_per_segmentation
best_segmentation_ngram_score
null_expected_best_score
```

Otherwise, trying many segmentations will inflate scores.

---

# 19. N-gram null-normalisation

N-gram scores must also be compared to nulls.

Raw phrase hits are not enough.

For each candidate:

```text
observed_ngram_score
expected_null_ngram_score
excess = observed - expected
lift = observed / expected
```

Nulls should include:

```text
random rune strings
shuffled rune strings preserving rune frequencies
wrong-candidate outputs
bad solver candidates
candidate texts with shuffled word order
candidate texts with shuffled spans
```

---

# 20. Positive, bad, and null corpora

## 20.1 Positive / near-positive corpus

Use recent RDP/no-WLI partial solutions.

Include:

```text
known better partial candidates
higher match-ratio candidates
candidate texts from promising runs
candidate texts near accepted branches
```

This is the damaged language we actually care about.

## 20.2 Bad candidate corpus

Use:

```text
poor solver candidates
misranked candidates
known bad branches
wrong-seed outputs
candidate outputs rejected by later evidence
```

## 20.3 Null corpus

Use multiple nulls:

```text
random rune strings
shuffled rune strings preserving rune frequencies
random strings preserving word lengths
wrong-key / wrong-cipher generated outputs
candidate texts with shuffled spans
candidate texts with shuffled word order
```

---

# 21. Combined scoring interpretation

A candidate may pass for different reasons.

## 21.1 Span-Hamming keep

```text
Candidate has more damaged-word evidence than null.
```

## 21.2 N-gram keep

```text
Candidate contains ordered word sequences resembling real language.
```

## 21.3 Strong combined keep

```text
Candidate has both damaged local word evidence and phrase-order evidence.
```

This is likely the strongest signal.

---

# 22. Human review lists

Human review should inspect contradictions, not every word.

Priority review buckets:

```text
1. Old strict -> proposed X
2. Old rejected -> proposed S or N
3. High-frequency word blocked by hard reject
4. Low-frequency word admitted by topic support
5. Common word with high null noise
6. Obscure-looking word with high positive lift
7. S word with any warning flag
8. N word with high null contribution
9. Manual override conflict
10. N-gram support wants to rescue an X word
11. Strong n-gram hit contains weak/odd word
12. Feature contribution outliers
13. confirmed_ref_keep word still proposed X
14. confirmed_ref_keep word proposed S
15. unverified Cicada/fan-theory word proposed S or N
16. proper-name-only word proposed S
17. common cultural/geographical/language word inconsistently rejected
18. long strict word with high-HD null noise
19. normal high-HD feature with large null contribution
```

Every review row should show:

```text
word
old tag
proposed tag
reason flags
topic flags
confirmed_ref fields
span-Hamming lift/noise summary
n-gram support summary
why it is being shown
```

---

# 23. Assistant alignment rules

These are explicit rules for me, because drift has repeatedly hurt this project.

## 23.1 Before every classification panel

I must restate:

```text
S = obvious everyday written word OR strong Cicada / puzzle / crypto / symbolic word
N = most normal readers would recognise it in written text OR confirmed clue-domain/reference keep
X = slang, typo-ish, proper-name-only, specialist, obscure, rare, archaic, noisy, or weak dictionary baggage
```

Then classify against those definitions.

## 23.2 No vocabulary-flex

I must not use my broad vocabulary as the standard.

If I know a word mainly because my vocabulary is unusually broad, that is evidence for `X`, not `N`.

## 23.3 No silent carry-forward

Invalid:

```text
unreviewed rows keep current strict
```

Correct:

```text
unadmitted rows are X
```

## 23.4 No hidden judgement

Every proposed `S` or `N` must include a reason:

```text
everyday word
missing-apostrophe contraction
puzzle/crypto term
topic/clue-domain term
confirmed Cicada/reference term
positive-candidate support
n-gram phrase support
manual override
```

## 23.5 No pretending manual review happened

Rows not explicitly reviewed must not be labelled manual.

Correct sources:

```text
manual_override
hard_rule_reject
semantic_admission
topic_admission
confirmed_ref_admission
statistical_admission
statistical_reject
ngram_review_support
review_required
```

## 23.6 User corrections become calibration rules

Already learned examples:

```text
rubberise/aerosolise/shelffuls/teemingness -> X
outkilled -> N
schwa/kudzu/ombre/lariat -> X
syringing -> N
keening/throve/churl/clews -> X
typos -> S
clefs -> N
nonce -> X
koans -> S
```

## 23.7 Separate word suitability from scorer usefulness

A word can be semantically acceptable but noisy.

A feature can be mathematically noisy even with good words.

Both must be measured.

## 23.8 Do not invent Cicada confirmation

A word should not receive confirmed Cicada metadata unless the source class is clear.

Allowed confirmation sources should be conservative:

```text
PGP-verified Cicada communications
accepted Liber Primus solved text
archived original puzzle artefacts
solver archive entries with traceability
confirmed reference lists with source notes
```

Disallowed as confirmation:

```text
Discord speculation
YouTube theory
fan reconstruction without source
copycat puzzle
later fiction/pop-culture inspired by Cicada
unsigned claimed message
```

---

# 24. Validation checks

The builder should fail if:

```text
any S has no admission_reason
any N has no admission_reason
any non-X has decision_source unknown
any old bit was copied without a new reason
any S has hard_reject_flags without manual override
any manual override is contradicted
any output row lacks provenance metadata
any high-HD feature lacks null statistics
any n-gram rescue lacks provenance metadata
any n-gram feature ignores tag filtering
any confirmed_ref_keep row lacks confirmed_ref_class
any confirmed_ref_keep row lacks confirmed_ref_confidence
any confirmed_ref_keep row lacks confirmed_ref_source
any confirmed_ref_keep row with unverified_reject is admitted silently
any S admitted through Cicada/reference support lacks topic or confirmed_ref metadata
any unsigned/copycat/fan-theory term is treated as confirmed
any high-HD rung is silently omitted before the feature panel
```

Useful summary reports:

```text
S/N/X count by rune length
S/N/X count by decision source
hard rejects by reason
topic admissions by topic
confirmed_ref admissions by class
confirmed_ref admissions by confidence
old strict retained
old strict rejected
old rejected rescued
manual overrides applied
top S words by null noise
top N words by null noise
top positive-lift words
top n-gram-supported rescues
top contradiction cases
feature lift by length/HD/tag
n-gram lift by n/tag-class
confirmed_ref_keep words proposed X
confirmed_ref_keep words proposed S
unverified Cicada terms proposed non-X
high-HD feature noise by strict/normal tag
```

---

# 25. Implementation phases

## Phase A — dictionary rebuild

```text
1. Load old policy files.
2. Start every word as X.
3. Apply manual overrides.
4. Apply hard reject rules.
5. Apply semantic/topic admission candidates.
6. Apply confirmed_ref metadata candidates.
7. Compute span-Hamming neighbourhood/noise metadata.
8. Produce proposed S/N/X tags.
9. Emit review-priority files.
10. Validate invariants.
```

## Phase B — span-Hamming feature panel

```text
1. Build strict/normal selected sets from tags.
2. Generate the full enabled length/HD ladder for strict and normal.
3. Run positive/bad/null corpora.
4. Report observed/null/excess/lift.
5. Identify useful and noisy rungs.
6. Tune scoring gates.
7. Decide which rungs enter scoring, which are downweighted, and which are review-only.
```

## Phase C — n-gram filtered index

```text
1. Load Mortlach n-gram files.
2. Filter n-grams by S/N/X word tags.
3. Preserve confirmed_ref metadata for phrase review.
4. Build strict/normal n-gram indexes by n and shape.
5. Score WLI/LP candidates first.
6. Add no-WLI segmentation-aware scorer later.
7. Compare with null/bad/positive corpora.
```

## Phase D — combined gate

```text
1. Keep span-Hamming and n-gram scores separate.
2. Measure each independently.
3. Combine only after feature lift is proven.
4. Track rescues and breaks against controls.
5. Keep confirmed_ref effects explainable and auditable.
```

---

# 26. Expected outcome

The old policy likely had:

```text
too many strict words
too many obscure long words
too many extended dictionary entries
too much old strict carry-forward
weak use of n-gram phrase evidence
no clear handling of genuine Cicada/art/literature references
```

The new policy should produce:

```text
small high-trust strict list
broader but controlled normal list
large rejected tail
full provenance metadata
confirmed Cicada/reference metadata
HD ladder span-Hamming features
full enabled HD ladder retained through feature evaluation
filtered n-gram phrase features
null-normalised evidence
reviewable contradiction lists
```

---

# 27. One-paragraph working principle

```text
The dictionary is not an English word list.
It is a controlled scoring instrument for damaged RDP candidate text.

Strict words provide high-confidence local evidence.
Normal words provide broader but still controlled language support.
Rejected words are excluded because they add noise, ambiguity, or weak dictionary baggage.

Confirmed Cicada/reference metadata protects genuine puzzle, art, literature,
source-text, and method words from blind rejection, but it does not silently admit them.

Span-Hamming detects damaged local word evidence.
N-grams detect ordered phrase evidence.

HD is not a single setting: each rune length gets an HD ladder.
For v0.3, the full enabled ladder is first-class for both strict and normal sets.
Low-HD rungs are high-confidence keep evidence.
Higher-HD rungs are damaged-text evidence and must be judged by excess over null.

No old selected bit is trusted unless re-admitted with a reason.
No output row is valid without provenance.
```
