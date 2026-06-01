# Late-stage selector work: Stage A operating plan and decision checklist

## Purpose

Treat late-stage selector development as a **small ranking research programme**,
not a general scorer replacement effort.

Current discipline:

- `Stage A` = benchmark-only ranking science
- `Stage B` = replay validation
- `Stage C/D` = only later, if `A` and `B` are genuinely convincing

That means:

- no live scorer changes now
- no black-box model now
- no truth used at selection time
- no broad scorer rewrite now

## Current state

What exists now:

- one must-pass adversarial fixture:
  - `tests/fixtures/no_wli/v45_seed411_late_frontier_fixture.json`
- one small disagreement dataset:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phasec_truth_gap_dataset/rows.json`
- one benchmark-only harness:
  - `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_selector_benchmark.py`
- one replay-capture run in flight:
  - `tune_v46_p9c3_seed411_novel_start_replay_capture_2job`

What does not yet exist:

- enough independent failure cases to claim generality
- a replay-ready historical `v45`
- enough semantic plaintext/key material to make richer semantic features
  meaningful

So the correct posture is:

- use `Stage A` to learn
- use `v45` as the must-pass anchor
- use the disagreement dataset as a sanity check
- wait for `v46` before making stronger claims or touching live flow

## Model ladder

Keep the ladder small and interpretable:

1. legacy selector
2. weighted benchmark-only reranker
3. tiny linear pairwise reranker

Do not add anything more complicated until there is a clear reason.

## Feature ladder

Keep feature growth disciplined:

First:

- score features

Then:

- structural / novelty features

Only later, once replay-ready frontiers exist:

- semantic partial-plaintext features

## Main rule for the disagreement dataset

The current `14` disagreement rows are useful, but they are **not** `14`
independent failure modes.

The current Stage A summary already shows only `5` distinct disagreement
patterns.

So evaluation should be done at two levels:

- row level
- pattern level

If something looks good only at row level but collapses at pattern level, that
is a warning sign.

## Stage A decision checklist

Use this against:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/summary.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/summary.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_selector_stagea/v45_feature_rows.json`

### 1. Must-pass `v45` check

Inspect:

- legacy selector picks the known bad winner
- weighted reranker picks a materially stronger challenger
- pairwise reranker picks a materially stronger challenger
- the truth lift is clearly visible
- the chosen challenger is selected using only live-available features

Pass if:

- both benchmark-only rerankers beat the legacy choice on `v45`
- or at minimum one reranker clearly and reproducibly beats it with an
  interpretable reason

Pause if:

- the legacy failure is not reproduced
- the reranker only “wins” because of a fixture-handling bug
- the reranker win depends on oracle-only fields
- the reranker is unstable across repeated harness runs

### 2. Broader disagreement sanity check

Inspect:

- how many disagreement rows improve
- how many distinct disagreement patterns improve
- whether the same feature family explains the rescues
- whether weighted and pairwise broadly agree on which challenger is better

Call broader lift credible only if most of these are true:

- the reranker improves more than just the `v45` row
- it helps on more than one distinct disagreement pattern
- the improvement is not coming only from duplicated variants of the same
  pattern
- the same small set of features keeps appearing as the reason
- weighted and pairwise are not telling completely different stories

Pause if:

- only `v45` improves
- row-level win count looks nice but pattern-level improvement is tiny
- the rescue depends on one brittle feature that does not recur
- weighted and pairwise disagree badly on most cases
- the model only wins when effectively memorising one fixture shape

### 3. Feature-discipline check

Inspect which features are actually driving the result.

The explanation should make it possible to see whether the rescue is mainly
coming from:

- score features
- novelty / structural features
- lexical features
- placeholder semantic fields that should not yet matter

Healthy Stage A looks like:

- the rescue is explainable in terms of existing score / structural / lexical
  signals
- the same feature family is useful across more than one disagreement pattern
- no unavailable or oracle-only field is leaking in

Pause if:

- placeholder semantic fields dominate before replay-ready frontiers exist
- too many features are needed to explain one fixture
- the rescue logic cannot be explained in plain English
- the model is becoming too complex for the data size

### 4. Dataset-size realism check

Keep the small-data warning explicit in every review.

Questions:

- how many disagreement rows are there?
- how many distinct patterns are there?
- how many seeds / runs do those patterns actually cover?
- are we still basically studying one family of failure?

Enough for Stage A means:

- enough to learn from
- enough to challenge the baseline
- enough to see whether the reranker is obviously nonsense

It does **not** mean enough for strong generalisation claims.

Say “pause, not enough data” if:

- almost all wins still reduce to one pattern family
- the dataset is too small to distinguish a real rule from a clever hack
- pattern-level evidence is too thin to choose between weighted and pairwise
  meaningfully

If that happens, do not escalate the model. Wait for `v46`.

### 5. Benchmark-only reporting check

For each case, the report should make disagreement impossible to hide. Ensure it
shows:

- score-selected winner
- oracle-best explored challenger
- truth gap
- score gap
- disagreement flag
- what the weighted reranker chose
- what the pairwise reranker chose

If that story is still hidden, Stage A is incomplete.

### 6. Decision gate: move to Stage B or not

Move to `Stage B` only if all of these are true:

1. `v45` is clearly rescued by the reranker
2. there is some broader disagreement sanity beyond a single row
3. the rescue uses only live-available features
4. the reranker is still simple and interpretable
5. `v46` finishes with replay-ready frontier material

Stay in `Stage A` if any of these are true:

1. only `v45` improves and nothing else does
2. pattern-level lift is too weak
3. the reranker is already too brittle or complex
4. the feature story is not understandable
5. `v46` is not replay-ready

## What Stage B should mean

`Stage B` should not start just because `v46` finishes.

It should start only when both conditions hold:

- `Stage A` shows a selector variant that looks genuinely better than legacy on
  the frozen frontier and not obviously overfit
- `v46` gives a replay-ready frontier with enough candidate material to test
  continuation or replay meaningfully

## Immediate next actions

While `v46` runs:

1. inspect `summary.md` and `summary.json` for:
   - `v45` must-pass rescue
   - row-level vs pattern-level lift
   - feature dependence
   - weighted vs pairwise agreement
2. write a short note answering:
   - what feature group is actually rescuing `v45`
   - whether the same group helps elsewhere
   - whether the broader lift is credible or still too thin

When `v46` finishes:

3. check replay readiness:
   - key/plaintext fields present
   - frontier complete enough for trial-key / replay checks
4. only then decide:
   - continue refining `Stage A`
   - or move into the first true `Stage B` replay check

## Bottom line

The current operating rule is:

- keep `Stage A` small, benchmark-only, and interpretable
- treat `v45` as the must-pass adversarial fixture
- treat the disagreement dataset as a sanity check, not a training corpus
- do not move toward live integration until `v46` gives a replay-ready frontier
  and `Stage A` shows believable lift beyond one row
