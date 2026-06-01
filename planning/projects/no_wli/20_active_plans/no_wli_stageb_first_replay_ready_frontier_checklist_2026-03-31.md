# No-WLI Stage B first replay-ready frontier checklist

## Purpose

This checklist defines exactly what the first replay-ready late frontier must
contain and how it will be judged once `v46` finishes.

The goal is to avoid losing time after the run finishes by deciding the
inspection criteria in advance.

## Preconditions

Stage B should only start if both are true:

- `v46` or a comparable fresh run finishes cleanly
- the run exports at least one replay-ready late frontier with complete
  candidate capture

Stage B does **not** begin just because the run finishes.

## Must-have capture

The first replay-ready frontier must include, for each frontier candidate:

- `candidate_hash`
- `source`
- `lane`
- `source_rank`
- `final_score`
- `init_score`
- `score_gain`
- `init_search_score`
- `final_match` when truth is available
- `init_match` when truth is available
- `init_key_idx`
- `init_plaintext_idx`
- `final_key_idx`
- `final_plaintext_idx`

The run-level artifact must also include:

- score-selected winner hash
- oracle-best explored challenger hash when truth is available
- winner-vs-oracle disagreement fields
- enough metadata to rebuild the same late frontier feature table used in
  Stage A

## Replay-ready success condition

The frontier is replay-ready only if:

- `frontier_key_material_complete = 1`
- every candidate needed for the late frontier comparison has non-empty:
  - `final_key_idx`
  - `final_plaintext_idx`
- at least the legacy winner and one challenger path can be reconstructed
  faithfully from the artifact

If those conditions do not hold, Stage B stays blocked.

## Must-have first analysis

When the first replay-ready frontier is exported, do these checks in order:

1. Confirm frontier reconstruction:
   - can the exported fixture reproduce the same candidate set and hashes?
2. Confirm feature reconstruction:
   - can the Stage A feature table be rebuilt exactly from the replay-ready
     frontier?
3. Confirm candidate material:
   - can we identify and reconstruct:
     - the legacy winner
     - the best truth challenger
     - the current Stage A reranker winner
4. Confirm replay viability:
   - can at least the legacy winner and one challenger path be replayed or
     continued without missing material?

## First Stage B comparison

Only after the above succeeds, compare:

- legacy late selector choice
- benchmark-only Stage A baseline choice:
  - `score + novelty`
- optional candidate:
  - safe-source-penalty variant

This comparison should answer:

- does the better-ranked candidate replay or continue into a better path?
- is the source-penalty rescue merely a mild benchmark improvement or a real
  replay advantage?

## Pre-v46 baseline freeze

For the handoff into Stage B, freeze:

- conservative Stage A baseline:
  - `score + novelty`

Reason:

- it is simpler
- it rescues the dominant repeated disagreement family
- it is robust under small weight perturbations

Do **not** automatically promote the source-penalty variant to baseline yet.

Reason:

- it does rescue the last unrecovered pattern in Stage A
- but it does so by choosing `7391...`, not the oracle-best `e45...`
- so it should be treated as a promising candidate variant, not the locked
  baseline-to-beat, until replay evidence exists

## Stage B decision note

After the first replay-ready comparison, record one of:

- replay-ready frontier missing required material; Stage B blocked
- reranker improves ranking but not replay outcome
- reranker improves both ranking and replay outcome
- source-penalty variant helps only superficially
- source-penalty variant shows real replay value

## Immediate outputs expected after v46

At minimum:

- fresh replay-ready frontier fixture export
- short replay-readiness note
- one comparison note:
  - legacy vs Stage A baseline
  - optional source-penalty candidate if replay-ready
