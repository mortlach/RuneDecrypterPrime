# PhaseB N-Gram Hamming Exact No-Cap Pilot Design Plan - 2026-05-29

Status: v3_2_canon_bridge_accepted
Work status: await_full_raw_provenance_then_bridge_diagnostic_pack
Project: no_wli
Owner: agent
Source-of-truth parents:
- planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md
- planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_implementation_start_plan_2026-05-14.md
- planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_fast_real_index_smoke_review_pack_2026-05-29.zip
- planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md

## v3.2 Canon/Bridge Update - 2026-05-30

The exact no-cap pilot sequence and balanced readout are now interpreted under
the v3.2 canon/bridge rule.

Accepted interpretation:

- order-2 produced the first visible signal because it was the simplest and
  cheapest active slice, not because it is the final scorer direction
- order-2 remains diagnostic/bridge-only unless it passes a higher burden of
  proof
- order-3 is the first serious phrase-coherence test once full raw assets are
  available and reviewed
- order-4 remains part of the canonical destination, deferred only for data-plane
  and sizing reasons
- order-5 remains optional diagnostic, not deleted

The next broad evidence step is not another ad hoc P1/P2 pilot. The next broad
step, after full raw order-2/order-3 provenance passes review, should be an
order-2/order-3 bridge diagnostic pack with explicit profile authority fields:

```text
profile_origin
canonical_profile_id
parameter_status
score_authority
```

Bridge outputs must not imply that bridge profiles replace the canonical
research ladder:

```text
diagnostic canonical families:
  B2R
  N3S_diag
  F5D

score-candidate canonical families:
  N3C
  S3W
  N4L
  S34C_main
```

Until provenance review is complete, allowed work is preparation only:

- bridge profile manifest design
- cluster schema design
- synthetic cluster/profile-authority tests
- provenance review checklist

Lane 2 preparation plan:

- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md`

Blocked until review:

- broad bridge scan launch
- order-4/order-5 expansion
- full hard-pair report
- production scorer changes
- direct additive use of P2/current-score combinations

## Current Gate

C++ Slice 2 tiny real-index smoke passed review with pre-pilot amendments.

Implemented amendments before this design:

- positive-control smoke now proves the selected phrase appears:
  - selected `phrase_id`
  - expected `hit_start == 1`
  - expected `total_phrase_hd == 0`
  - expected all `word_hds == 0`
- next review-pack ZIPs must use POSIX-style `/` archive entries.
- candidate-source comparability is now a hard pilot gate.

## Purpose

Design the first exact no-cap pilot without launching it.

The pilot should answer only:

```text
Can the compiled C++ backend scan a tiny, deterministic, reviewable real
candidate set against the real phrase index with exact no-cap hit counting,
explicit backend manifests, and defensible candidate stream provenance?
```

It must not answer full hard-pair effectiveness, tune profile parameters, or
change production scorer defaults.

## Non-Negotiable Boundaries

- No full hard-pair report.
- No broad pilot.
- No production scorer weights/defaults/ranking changes.
- No CLI arguments for runner/helper scripts.
- Hardcoded constants only.
- Repo-relative paths only where controllable.
- Backend must be explicit:
  - full pilot path uses `backend_impl=cpp_fast`
  - no silent Python fallback
  - Python reference may be used only for bounded parity/audit rows
- Count all eligible hits exactly.
- Debug examples are output-only and must not influence feature values.

## Pilot Shape

Initial intended scope:

```text
candidates: 10
chunks: 20
chunk length: 500 tokens
direction: fwd
cuts: normal
orders: 2, 3
profiles: P0, P1, P2
backend: cpp_fast
reference parity: bounded subset only
```

Profiles:

- `P0_exact_short`
- `P1_word_analogue_len7_hd2`
- `P2_conservative_len8_hd2`

This is the real-candidate hard-pair comparability pilot. It must not be called
the controlled `20-50%` damage ladder unless the required damage-stream
fingerprints are present and verified.

## Candidate-Source Comparability Gate

The highest-risk failure mode is scanning the wrong candidate/damage stream.
Therefore, the pilot must begin with a preflight manifest that proves one of:

1. pilot candidates are rebuilt/derived directly from hard-pair road-test
   manifests; or
2. candidate text source rows match hard-pair road-test manifests by explicit
   fingerprints.

Required fields for a controlled damage-stream claim:

```text
sample_id
chunk_id
damage_model
damage_level
seed
clean_token_hash
damaged_token_hash
candidate_id
```

Current observed candidate text source:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1/candidate_full_texts.jsonl.gz`
- fields observed:
  - `candidate_id`
  - `current_score`
  - `label`
  - `latin_render`
  - `panelA_score`
  - `token_count`
  - `token_hash`
  - `token_sequence_text`
  - `truth_match_ratio`

This source is useful for hard-pair candidate token scanning, but it does not
carry the full controlled damage-stream fingerprint fields by itself.

Current observed hard-pair road-test manifests:

- `hard_pair_manifest.csv`
  - candidate pair ids, token paths, scores, known better candidate, source
    artifact path, `token_streams_resolved`
- `candidate_manifest_resolved.csv`
  - candidate ids, label/truth/current score, direction, token count,
    candidate token path, token hash, pair occurrence counts
- `candidate_chunk_manifest.csv`
  - candidate chunk ids, candidate id, chunk index/start/end, token count,
    chunk status, direction

These are enough to build a hard-pair candidate-source preflight, but not enough
to claim controlled `20-50%` damage ladder equivalence without additional
damage-source fingerprints.

## Deterministic Candidate Selection

The pilot should choose candidates from hard-pair rows, not arbitrary first rows.

Candidate strata:

- current-scorer correct good candidate
- current-scorer misrank rescue opportunity
- Panel A rescue
- Panel A break / likely false positive
- high-current-score bad candidate
- repeated bad candidate appearing across multiple pairs
- low/no-hit control candidate where available

Selection algorithm should be hardcoded and deterministic:

1. load pair and candidate manifests
2. derive candidate-level tags from:
   - current score correctness
   - known better/worse role
   - Panel A rescue/break files
   - label and truth match ratio
   - pair occurrence count
3. select up to 10 candidate ids by fixed stratum order
4. tie-break by stable `candidate_id`
5. require two 500-token chunks per selected candidate
6. write missing-stratum and missing-candidate lists instead of silently
   substituting

## Required Pilot Outputs

Output root:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_exact_no_cap_pilot_v1
```

Required files:

- `config.json`
- `input_manifest.json`
- `candidate_source_preflight_manifest.json`
- `candidate_selection_manifest.json`
- `backend_manifest.json`
- `phrase_index_manifest_used.json`
- `profile_manifest.json`
- `chunk_feature_rows.csv`
- `candidate_feature_rows.csv`
- `debug_examples.jsonl`
- `parity_audit_rows.jsonl`
- `readout.md`

Required backend manifest fields:

- `backend_impl`
- `python_fallback_allowed`
- `_ngram_hamming_fast_available`
- extension module name
- phrase-index path
- loaded phrase entry counts by profile/cut/order
- no-hit-cap assertion

Required candidate-source preflight fields:

- input paths and row counts
- selected candidate ids
- token hashes from all available sources
- missing fingerprint fields
- comparability verdict:
  - `hard_pair_candidate_stream_verified`
  - `controlled_damage_stream_verified`
- blocked reason if either intended claim cannot be supported

## Feature Rows

For each candidate/chunk/profile/cut/order:

- `candidate_id`
- `candidate_chunk_id`
- `chunk_index`
- `chunk_start`
- `chunk_end`
- `profile_id`
- `direction`
- `dictionary_cut`
- `ngram_order`
- `backend_impl`
- `phrase_hit_count`
- `unique_phrase_hit_count`
- `opportunity_count`
- `positive_start_offset_count`
- `phrase_hits_per_opportunity`
- `positive_start_offset_fraction`
- `mean_total_phrase_hd`
- `min_total_phrase_hd`
- `mean_normalised_phrase_hd`
- `best_normalised_phrase_hd`
- `weighted_hit_sum`
- `max_phrase_weight`
- `mean_phrase_weight`
- backend counters:
  - `candidate_tokens_scanned`
  - `candidate_start_offsets_considered`
  - `phrase_entries_considered`
  - `phrase_verification_attempts`
  - `phrase_verification_passes`

## Parity Audit

Python reference parity should be bounded:

- one positive-control row from phrase index
- at least one selected real candidate chunk
- one zero-hit or low-hit row if naturally present

The broad pilot path must use C++ only. If C++ is unavailable, the pilot blocks.

## Pass Conditions

The exact no-cap pilot passes only if:

- candidate-source preflight is explicit and honest
- hard-pair candidate stream is verified for the selected rows
- controlled damage ladder is either verified or explicitly not claimed
- backend is `cpp_fast`
- Python fallback is `False`
- all selected candidate chunks are accounted for
- all feature rows include backend counters
- positive-control parity passes
- bounded real-row parity passes
- output is deterministic on repeat
- no hit caps are present
- runtime stays within a small interactive budget

## Stop Conditions

Stop before scanning if:

- selected candidates cannot be tied back to hard-pair candidate manifests
- required source files are missing
- C++ backend is unavailable
- selected candidates lack full chunks
- path validation fails

Stop after first scan batch if:

- elapsed time projects beyond an interactive pilot budget
- backend output diverges from Python on bounded parity rows
- candidate-source preflight reveals only uncontrolled streams while the run was
  configured to claim controlled damage-ladder evidence

## Review Questions

1. Is the candidate-source preflight strong enough for a hard-pair
   comparability pilot?
2. Should the first exact no-cap pilot avoid controlled `20-50%` damage-ladder
   language entirely unless additional fingerprints are discovered?
3. Is the deterministic candidate stratum list acceptable?
4. Should the pilot implement only `normal` cut first, or include `strict` in
   the first pilot despite the original initial shape saying normal only?
5. Is the bounded Python parity audit sufficient if the broad pilot path uses
   C++ only?

## Implementation / Launch Update - 2026-05-29

The exact no-cap pilot runner was implemented with the approved amendments and launched once.

Result:

```text
status = blocked
completed_scans = 1 / 120
elapsed_seconds = 1.724
projected_seconds_after_first_scan = 206.918
budget_seconds = 120.0
blocked_reason = first scan projected 206.9s beyond 120.0s budget
```

The provenance preflight passed for the hard-pair candidate stream:

```text
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
controlled_damage_stream_required = false
```

Bounded parity did not run because the runner stopped at the runtime projection gate.

New review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_exact_no_cap_pilot_runtime_block_review_pack_2026-05-29.zip
```

## Current Stop Point

This is now a runtime sizing review point. Do not relaunch the 120-cell pilot
until the reviewer approves either a smaller microbatch, a larger declared
logged-run budget, or a backend/entry-index acceleration slice.

## Microbatch Sizing Update - 2026-05-29

The reviewer approved a 6-cell microbatch sizing slice instead of a full
120-cell rerun.

Implemented scope:

```text
candidate_count = 1
chunks_per_candidate = 1
cut = normal
orders = 2, 3
profiles = P0, P1, P2
planned scan cells = 6
```

Result:

```text
status = pass
completed_scans = 6 / 6
elapsed_seconds = 8.172
bounded parity rows = 3
all_required_parity_passed = true
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
```

Attempt-weighted projection for the original 120-cell target:

```text
measured_attempts = 27,374,016
measured_scan_seconds = 1.735
measured_attempts_per_second = 15,774,970
full_pilot_target_attempts = 547,480,320
attempt_weighted_full_pilot_projected_seconds = 34.706
```

New review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_exact_no_cap_microbatch_sizing_review_pack_2026-05-29.zip
```

## Current Stop Point After Microbatch

Do not relaunch the 120-cell pilot until the reviewer approves the declared
budget and launch shape. If approved as a logged run, use a conservative
wallclock budget that includes setup, parity, output writing, and projection
margin, not only scan-time projection.

## Full Pilot Update - 2026-05-29

The reviewer approved the full 120-cell pilot with a 10-minute guard.

Implemented scope:

```text
candidate_count = 10
chunks_per_candidate = 2
cut = normal
orders = 2, 3
profiles = P0, P1, P2
planned scan cells = 120
max_wallclock_seconds = 600.0
early_projection_check_cells = 12
early_projection_stop_seconds = 600.0
```

Result:

```text
status = pass
completed_scans = 120 / 120
elapsed_seconds = 43.963
bounded parity rows = 3
all_required_parity_passed = true
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
```

Timing summary:

```text
measured_attempts = 547,480,320
measured_scan_seconds = 36.956
measured_attempts_per_second = 14,814,535
```

New review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_exact_no_cap_full_pilot_review_pack_2026-05-29.zip
```

## Current Stop Point After Full Pilot

This is now a full-pilot review point. Do not expand to broad pilot, strict,
order 4, P3/P4, full hard-pair reporting, controlled damage-ladder language, or
production scorer changes until the reviewer approves the next bounded step.

## Full Pilot Interpretation Update - 2026-05-29

The reviewer approved closing the exact no-cap full-pilot gate and requested a
narrow interpretation pack over the existing output only.

Interpretation result:

```text
status = pass
total_hits = 14
candidates_with_hits = 3 / 10
candidates_with_zero_hits = 7 / 10
productive_profile_orders = P1 normal order 2, P2 normal order 2
```

Stratum readout:

```text
current_scorer_correct_good_candidate = 6 hits
stable_fill = 8 hits
all other selected strata = 0 hits
```

New review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_exact_no_cap_full_pilot_interpretation_review_pack_2026-05-29.zip
```

## Current Stop Point After Interpretation

This is now an interpretation review point. Do not run a bounded expansion,
add strict/order 4/P3/P4, start broad pilot/full hard-pair reporting, claim a
controlled damage ladder, or change production scorer behavior until the
reviewer approves the next bounded step.

## Bounded Expansion v1 Update - 2026-05-29

The reviewer approved moving faster with a bounded expansion over the productive
shape found in the full pilot.

Implemented scope:

```text
claim_mode = hard_pair_candidate_comparability
cut = normal
order = 2
profiles = P0, P1, P2
candidates = 100
chunks_per_candidate = 2
scan_cells = 600
max_wallclock_seconds = 600.0
```

Result:

```text
status = pass
completed_scans = 600 / 600
elapsed_seconds = 75.368
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
parity_rows = 4
all_required_parity_passed = true
```

Hit readout:

```text
total_hits = 188
candidates_with_hits = 39 / 100
candidates_with_zero_hits = 61 / 100
P0 hits = 0
P1 hits = 95
P2 hits = 93
```

New review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_bounded_expansion_v1_review_pack_2026-05-29.zip
```

## Current Stop Point After Bounded Expansion v1

This is now a bounded expansion review point. Do not move to production scorer
changes, controlled damage-ladder language, strict/order 4/P3/P4, or a broad
full hard-pair report until the reviewer approves the next bounded step.

## Balanced Readout v1 Update - 2026-05-29

External review was temporarily unavailable, so work continued to the next
bounded readout requested by the user. This run uses the same productive scan
shape as bounded expansion v1, but selects a more balanced candidate set.

Implemented scope:

```text
claim_mode = hard_pair_candidate_comparability
cut = normal
order = 2
profiles = P0, P1, P2
target strata = known_better, known_worse, panel_rescue, panel_break, bad_control, high_truth_stable_fill
target candidates per stratum = 20
selected candidates = 118
chunks_per_candidate = 2
scan_cells = 708
```

One explicit shortfall was recorded:

```text
panel_break_known_worse = 18 / 20
```

Result:

```text
status = pass
completed_scans = 708 / 708
elapsed_seconds = 90.447
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
parity_rows = 4
all_required_parity_passed = true
```

Hit readout:

```text
total_hits = 328
candidates_with_hits = 44 / 118
candidates_with_zero_hits = 74 / 118
P0 hits = 1
P1 hits = 164
P2 hits = 163
known_better hits = 160
known_worse hits = 8
```

New review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_balanced_readout_v1_review_pack_2026-05-29.zip
```

## Current Stop Point After Balanced Readout v1

This is now a balanced readout review point. The next useful step is likely a
focused comparison/decision pack over these outputs, not another larger scan.
Do not move to production scorer changes, controlled damage-ladder language,
strict/order 4/P3/P4, or a broad full hard-pair report until this readout is
interpreted.

## Balanced Readout Interpretation Update - 2026-05-29

A comparison/decision pack was created over the balanced readout v1 outputs only.
No new scan was run.

Decision readout:

```text
known_better mean hits per candidate = 4.000
known_worse mean hits per candidate = 0.211
high_truth_stable_fill mean hits per candidate = 7.750
bad_control mean hits per candidate = 0.250
panel_rescue_known_better hits = 0
P1/P2 same-hit-count candidates = 117 / 118
P0 positive chunk rows = 1
```

New review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_balanced_readout_interpretation_v1_review_pack_2026-05-29.zip
```

## Current Stop Point After Balanced Interpretation

This is now a scorer-design-slice review point. A reasonable next step is to
design a non-production scorer slice around normal/order-2/P1-or-P2 weighted
hits, with P0 as an audit/control feature. Do not change production scoring,
claim controlled damage-ladder evidence, add strict/order 4/P3/P4, or start a
full hard-pair report until reviewed.
