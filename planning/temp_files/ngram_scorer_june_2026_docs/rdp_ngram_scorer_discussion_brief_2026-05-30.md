# RDP N-Gram Scorer Discussion Brief - 2026-05-30

Status: discussion brief

Companion context:

- `planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_scorer_investigation_context_review_2026-05-30.md`

## One-Sentence State

The n-gram Hamming scorer implementation is mostly ready at the reference/C++
parity level, but the full raw asset/provenance layer is still in progress, and
the first empirical signal is normal/order-2/P1-P2 comparability rather than the
research-plan ideal of score-bearing clustered 3/4-gram phrase support.

## What Is Ready

- Python reference matcher exists.
- C++ fast backend exists and builds.
- Synthetic parity passed.
- Tiny real-index smoke passed with no Python fallback.
- Exact no-cap pilot passed.
- Bounded expansion passed.
- Balanced readout passed.
- Sample-index all-candidate matrix exists, with clear caveats.
- Non-production scorer design and combination notes exist, with clear
  boundaries.
- Resumable full raw shard build is running for fwd normal/strict order 2 and
  order 3.

## What Is Not Ready

- Full raw fwd order-2/order-3 normal/strict assets are not yet complete.
- Full raw asset/provenance review pack is not complete.
- Full hard-pair report has not started.
- Controlled 20-50% damage-ladder proof is not available from the candidate
  comparability runs.
- Strict/order-4/P3/P4 expansion is not approved.
- Cluster-tuple support scorer has not been validated over full/provenance-grade
  assets.
- Production scorer changes are not approved.

## Most Important Evidence

Exact joined n-gram scanning was effectively null:

```text
N4 normal 2-4 combined:
  truth preference = 2 / 2594
  rescues = 0
  breaks = 0
```

This supports the shift to damaged word-structured Hamming.

Balanced word-structured Hamming readout showed strong stratum separation:

```text
known-better mean hits per candidate = 4.000
known-worse mean hits per candidate = 0.211
high-truth stable-fill mean hits = 7.750
bad-control mean hits = 0.250
```

But panel-rescue candidates were a warning:

```text
panel-rescue known-better hits = 0
panel-rescue candidates with P2 hits = 0 / 20
```

And P1/P2 redundancy was extreme in the balanced slice:

```text
P1/P2 same-hit-count candidates = 117 / 118
```

Sample-index all-candidate interpretation warns against additive fusion:

```text
current known-better rate = 0.767926
P2 raw known-better rate = 0.220509
current + log1p(P2) known-better rate = 0.695451
```

## Main Design Tension

The June research plan says:

- 3-grams should be central;
- 4-grams should confirm;
- 2-grams should be weak or diagnostic;
- score-bearing evidence should be clustered, not raw-hit based.

The actual pilot evidence says:

- the first non-zero useful signal is normal/order-2/P1-P2;
- early order-3 in the small pilot was zero-hit;
- order-3 full raw data is currently being built, not yet interpreted;
- raw P2 is separable by candidate stratum but not safe as a standalone pairwise
  scorer.

So the practical question is not whether the research plan is wrong. It is how
to avoid jumping from a real but weak order-2 lead into an unsafe scorer, while
also not waiting forever for a perfect 3/4-gram support layer.

## Candidate Next Directions

### Option A - Wait For Full Raw Order-2/3 Provenance Before More Scorer Design

Do this if the discussion prioritizes data-plane integrity.

Benefits:

- avoids designing around sample/probe artifacts;
- lets order-3 be judged fairly;
- keeps the full raw asset build as the immediate gate.

Risks:

- delays scorer-design decisions;
- may leave the current order-2 lead underexplored.

Best next artifact:

- full raw asset/provenance review pack after shard build completes and is
  summarized.

### Option B - Design A Narrow Non-Production Order-2 Support Slice

Do this if the discussion prioritizes making the observed signal inspectable.

Shape:

- normal/order-2/P2 raw weighted hits as report-only support;
- P1 kept only if a specific diagnostic asks for it;
- P0 exact hits as audit/control;
- no additive production score;
- no broad rescue claim;
- explicit panel-rescue zero-hit investigation.

Benefits:

- follows the observed evidence;
- gives a concrete support artifact to compare against current/span-Hamming.

Risks:

- order-2 is exactly the family the research plan treats as inflation-prone;
- could overfocus on short/weak evidence before order-3 full assets land.

Best next artifact:

- non-production pair ledger or diagnostic pack over the balanced/sample-index
  outputs, with concentration and zero-hit-panel-rescue analysis.

### Option C - Prototype The Cluster Tuple With Orders 2 And 3 Only

Do this if the discussion wants to bridge the research design and observed
signal.

Shape:

- do not implement the final `S34C/N4L/S3W/N3C` tuple yet;
- build a temporary report-only tuple over available order-2/order-3 evidence;
- cluster overlap-or-touch intervals;
- raw hits diagnostic only;
- expose exact cluster count and top-phrase-share;
- use no production scoring.

Benefits:

- tests anti-inflation machinery early;
- does not require waiting for order 4;
- can reveal whether order-2 support remains useful after clustering.

Risks:

- may create a temporary tuple that differs from the June design;
- order-3 full assets are still in progress.

Best next artifact:

- cluster diagnostic prototype over completed full raw order-2/3 assets after
  provenance review.

### Option D - Prioritize Panel-Rescue Zero-Hit Diagnosis

Do this if the discussion treats rescue behavior as the central blocker.

Question:

Why do panel-rescue known-better candidates have zero P2 hits?

Possible causes:

- phrase asset coverage gap;
- candidate-source or chunk locality mismatch;
- true rescues are local-word evidence without phrase continuity;
- order-2 whole-phrase matching is too sparse;
- damage has destroyed contiguous phrase islands;
- current candidate strata are not representative.

Benefits:

- directly addresses the most worrying empirical caveat.

Risks:

- may become a case-study rabbit hole before the full raw asset build completes.

Best next artifact:

- panel-rescue no-hit audit comparing candidate chunks, span-Hamming local hits,
  available phrase opportunities, and missing phrase coverage.

## Recommended Discussion Order

1. Confirm the evidence boundaries:
   - hard-pair candidate comparability only;
   - not controlled damage ladder;
   - not production scorer;
   - not full raw until shard build/provenance completes.

2. Decide whether current priority is:
   - finish full raw/provenance;
   - inspect order-2 support;
   - prototype clustering;
   - explain panel-rescue zero hits.

3. Decide whether P1 and P2 should both remain in the next non-production slice.

4. Decide whether order-2 can be allowed as a report-only support feature despite
   the research recommendation that it should be weak/diagnostic.

5. Decide what evidence is required before 3-gram support can become central:
   - full raw asset completion;
   - non-zero hit rates;
   - cluster diversity;
   - null lift;
   - pairwise rescue/break ledger.

6. Decide whether any matched null work should happen before full hard-pair
   reporting.

## Current Recommended Position

The cautious recommendation is:

1. Let the full raw fwd order-2/order-3 shard build finish.
2. Summarize and review provenance before any broader scan.
3. Do not start full hard-pair reporting yet.
4. Treat normal/order-2/P2 as the live empirical lead, but only report-only.
5. Use the completed full raw order-3 assets to test whether the research plan's
   intended center of gravity becomes active.
6. If order-3 remains sparse, prototype a cluster-based bridge that lets order-2
   be inspected without letting raw hit volume dominate.
7. Keep production scorer weights and ranking policy unchanged.

## Red Lines

Do not:

- relaunch monolithic full raw asset building;
- call sample/probe results full raw evidence;
- call candidate comparability results controlled 20-50% damage-ladder results;
- add P2 directly to current score as an unbounded additive feature;
- promote order-2 before concentration/null checks;
- start strict/order-4/P3/P4 expansion without explicit sizing and review;
- start a full hard-pair report before the full raw asset/provenance gate;
- change production scorer defaults.

Do:

- keep exact all-hit accounting;
- keep C++ backend explicit;
- forbid silent Python fallback;
- keep strict/normal separate;
- keep FWD/REV separate;
- emit repo-relative logs and progress;
- preserve partial shard extractability;
- build review packs before expansion.

