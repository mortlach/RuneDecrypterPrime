# PhaseB N-Gram Hamming Coherence Scorer v1 Implementation Start Plan - 2026-05-14

Status: active
Work status: full_raw_shard_build_running_v3_2_canon_bridge_accepted
Project: no_wli
Owner: agent
Last updated: 2026-05-30
Current gate: full raw order-2/order-3 shard build and provenance review before broad bridge interpretation
Source-of-truth parents:
- planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md
- planning/temp_files/phaseB_ngram_hamming_coherence_scorer_v1_approved_spec.md
- output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_hard_pair_report_v1/readout.md

## v3.2 Canon/Bridge Coordination Update - 2026-05-30

Accepted discussion basis:

- `planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md`

Decision:

- adopt v3.2 as the current coordination language for profile authority,
  profile drift prevention, and staged bridge work
- preserve the deep-research canonical scorer ladder as the destination
- treat current order-2/order-3 work as a bridge/probe, not the final scorer
  direction
- continue the current full raw FWD order-2/order-3 normal/strict shard build
  and stop for provenance review before broad bridge scans

Canonical destination families:

```text
diagnostic:
  B2R
  N3S_diag
  F5D

score-candidate:
  N3C
  S3W
  N4L
  S34C_main
```

Canonical profile authority fields required for every profile row:

```text
profile_origin
canonical_profile_id
parameter_status
score_authority
```

Any profile in code, manifests, readouts, or review packs must not silently
change:

```text
order
cut
min phrase token length
max total HD
max word HD
score-bearing role
diagnostic role
```

Bridge work may prepare schemas, profile manifests, and synthetic tests while
the shard build runs. Broad bridge scans, order-4/order-5 expansion, full
hard-pair reporting, and production scoring changes remain blocked until full
raw order-2/order-3 provenance is complete and reviewed.

Lane 2 preparation plan:

- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_bridge_diagnostic_lane2_plan_2026-05-30.md`

Specific v3.2 constraints:

- `S34C_main` uses min phrase token length `10`
- any length-8 S34C variant must be separately labelled diagnostic and
  broader-than-canon
- order-2 remains diagnostic unless it clears a higher proof burden:
  cluster diversity, low concentration, matched-null lift, pair-ledger
  improvement, low/zero breaks, and later controlled damage-tier review before
  any production promotion
- order 4 is deferred only because it is outside the current data-plane tranche
- order 5 remains future diagnostic, not deleted
- diagnostic profiles must not shape score-candidate clusters unless the
  cluster scope explicitly says so

## Current Implementation Status - 2026-05-14

The approved start plan has moved from review-ready planning into implementation.

Completed:

- Slice 0 damage-source audit:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/audit_phaseB_ngram_hamming_damage_source_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_damage_source_audit_v1`
  - status: `pass`
- Slice 1 asset validation:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_assets_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_asset_validation_v1`
  - status: `pass`
- Slice 2 phrase-index builder:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_phrase_index_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_phrase_index_v1`
  - status: `pass`
  - phrase entries: `196680`
- Slice 3 Python reference matcher:
  - `src/rune_decrypter_prime/scoring/ngram_hamming/reference.py`
  - package export: `src/rune_decrypter_prime/scoring/ngram_hamming/__init__.py`
- Slice 4 reference/tool tests, first pass:
  - `tests/tools/test_phaseB_ngram_hamming_slice0_slice1_v1.py`
  - `tests/scoring/ngram_hamming/test_reference_ngram_hamming.py`
  - `tests/tools/test_phaseB_ngram_hamming_phrase_index_v1.py`

Verification run:

```text
python -m pytest tests/tools/test_phaseB_ngram_hamming_slice0_slice1_v1.py tests/scoring/ngram_hamming/test_reference_ngram_hamming.py tests/tools/test_phaseB_ngram_hamming_phrase_index_v1.py tests/tools/test_phaseB_ngram_hamming_reference_smoke_v1.py -q
```

Latest result:

```text
29 passed in 54.18s
```

Current stop point:

- C++ Slice 1 source is implemented and now builds locally.
- Synthetic C++/Python parity tests pass.
- C++ Slice 2 tiny real-index smoke passes with no Python fallback.
- Pilot/report runners have not started.
- Full hard-pair reporting remains gated on review, exact no-cap pilot, and
  expanded pilot.

## Pre-C++ Amendments - 2026-05-15

Pack-level review approved the Slice 0-3 direction but blocked code-level
review because the first implementation pack did not include actual source and
test files. The following amendments are now implemented before C++ work:

- damage manifest now distinguishes:
  - `same_damage_generator_verified: true`
  - `same_damaged_streams_shared_with_word_hamming: unverified`
- damage manifest records required pilot-time stream fingerprint fields:
  - `sample_id`
  - `chunk_id`
  - `damage_model`
  - `damage_level`
  - `seed`
  - `clean_token_hash`
  - `damaged_token_hash`
- asset manifest now freezes parser and token rules:
  - JSON-style `list[list[int]]`
  - no `eval`
  - no float tokens
  - no string tokens
  - no empty words
  - no empty phrases
  - token bounds `0..28`
  - separator-like scanning values forbidden
- asset validation now emits:
  - `ngram_hamming_asset_word_length_patterns.csv`
  - `ngram_hamming_asset_token_length_quantiles.csv`
  - `ngram_hamming_asset_duplicate_report.csv`
  - `ngram_hamming_asset_examples.csv`
- phrase-index builder now emits:
  - `phrase_profile_eligibility_summary.csv`
- tiny Python reference smoke now exists:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_reference_smoke_v1.py`
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_reference_smoke_v1`
  - status: `pass`
  - backend: `python_reference`
  - broad Python pilot: `False`
  - loaded entries: `2000`
  - elapsed seconds: `1.237`

Replacement implementation review pack with source/test contents:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_impl_review_pack_2026-05-15.zip
```

## Source-Level Review Amendments - 2026-05-15

Source-inclusive pack review result:

```text
Pack-level review: pass
Source-level review: pass with pre-C++ amendments
Next step: fix small contract gaps, then start independent C++ backend + parity tests
```

Pre-C++ contract amendments now implemented:

- `PhraseProfile` now includes `direction`.
- `profile_allows_entry()` requires `entry.direction == profile.direction`.
- reference tests include wrong-direction rejection.
- `rune_lengths` parsing is strict:
  - JSON list of ints only
  - no bool
  - no float
  - no string
  - all values must be positive
- candidate token validation is strict in `scan_chunk_reference()`:
  - non-empty sequence
  - ints only
  - no bool
  - values must be in `0..28`
- builder invalid rows now block core FWD phrase-index status:
  - `core_fwd_invalid_row_count`
  - `invalid_rows_block_core_fwd`
- duplicate/count metadata is explicit in phrase-index rows:
  - `count`
  - `sum_count`
  - `max_count`
  - `log_count`
  - `max_log_count`

Verification after these amendments:

```text
python -m pytest tests/scoring/ngram_hamming/test_reference_ngram_hamming.py tests/tools/test_phaseB_ngram_hamming_slice0_slice1_v1.py tests/tools/test_phaseB_ngram_hamming_phrase_index_v1.py tests/tools/test_phaseB_ngram_hamming_reference_smoke_v1.py -q
29 passed in 54.18s
```

Compile check:

```text
python -m py_compile <all included source/test files>
pass
```

Updated pre-C++ contract review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_pre_cpp_contract_review_pack_2026-05-15.zip
```

## C++ Slice 1 Status - 2026-05-15

Approved next step:

```text
independent C++ backend + synthetic parity tests only
```

Implemented source-only C++ Slice 1:

- `src/rune_decrypter_prime/scoring/ngram_hamming/FastNgramHamming.h`
- `src/rune_decrypter_prime/scoring/ngram_hamming/fast_bindings.cpp`
- `src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py`
- `src/rune_decrypter_prime/scoring/ngram_hamming/setup_ngram_hamming_fast.py`
- `tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py`

Scope is synthetic-only:

- in-memory phrase entries
- one candidate token sequence
- one `PhraseProfile`
- no JSONL phrase-index loading
- no real candidate files
- no benchmark runner
- no production scoring change

Build status:

```text
python src/rune_decrypter_prime/scoring/ngram_hamming/setup_ngram_hamming_fast.py
```

Result:

```text
blocked: Microsoft Visual C++ 14.0 or greater is required
```

The optional backend tests are present and skip when the extension is not built.

Verification on this machine:

```text
python -m pytest tests/scoring/ngram_hamming/test_reference_ngram_hamming.py tests/tools/test_phaseB_ngram_hamming_slice0_slice1_v1.py tests/tools/test_phaseB_ngram_hamming_phrase_index_v1.py tests/tools/test_phaseB_ngram_hamming_reference_smoke_v1.py tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py -q
29 passed, 12 skipped in 58.27s
```

Also implemented the non-blocking damage-audit hardening:

- `reference_configs_required: true`
- `reference_config_exists_count > 0`

C++ Slice 1 review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_cpp_slice1_source_review_pack_2026-05-15.zip
```

## C++ Slice 1 Build/Parity Update - 2026-05-29

Microsoft C++ Build Tools are now available locally. The existing hardcoded
build script was run without CLI arguments:

```text
python src/rune_decrypter_prime/scoring/ngram_hamming/setup_ngram_hamming_fast.py
```

Result:

```text
pass; _ngram_hamming_fast.cp311-win_amd64.pyd copied to src/rune_decrypter_prime/scoring/ngram_hamming/
import OK: rune_decrypter_prime.scoring.ngram_hamming._ngram_hamming_fast
```

Synthetic parity verification:

```text
python -m pytest tests/scoring/ngram_hamming/test_reference_ngram_hamming.py tests/tools/test_phaseB_ngram_hamming_slice0_slice1_v1.py tests/tools/test_phaseB_ngram_hamming_phrase_index_v1.py tests/tools/test_phaseB_ngram_hamming_reference_smoke_v1.py tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py -q
41 passed in 54.58s
```

Status:

- C++ Slice 1 build blocker is cleared.
- Synthetic parity gate is passed on this machine.
- No real-data backend loading, no pilot runner, and no hard-pair report has
  started.

Next gate remains narrow:

- external/source review of built C++ Slice 1 and C++ Slice 2 tiny real-index
  smoke behavior.

## C++ Slice 2 Tiny Real-Index Smoke - 2026-05-29

Implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_fast_real_index_smoke_v1.py`
- `tests/tools/test_phaseB_ngram_hamming_fast_real_index_smoke_v1.py`

Bounded scope:

- `ENTRY_LIMIT = 2000`
- `REAL_CANDIDATE_TOKEN_LIMIT = 250`
- `MAX_WALLCLOCK_SECONDS = 20.0`
- backend `cpp_fast`
- reference backend `python_reference`
- Python fallback disabled
- not a broad pilot

Output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_fast_real_index_smoke_v1
```

Result:

```text
status=pass
parity_match=True
elapsed_seconds=0.957
positive-control fast hits=2
real-candidate fast hits=0
```

Verification:

```text
python -m pytest tests/scoring/ngram_hamming/test_reference_ngram_hamming.py tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py tests/tools/test_phaseB_ngram_hamming_slice0_slice1_v1.py tests/tools/test_phaseB_ngram_hamming_phrase_index_v1.py tests/tools/test_phaseB_ngram_hamming_reference_smoke_v1.py tests/tools/test_phaseB_ngram_hamming_fast_real_index_smoke_v1.py -q
44 passed in 56.71s
```

Review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_fast_real_index_smoke_review_pack_2026-05-29.zip
```

Stop point:

- wait for review before exact no-cap pilot implementation or any broader
  real-data report.

## What Changed

This note starts the implementation planning pass for
`ngram_hamming_coherence_v1`.

No scorer code is changed here. The goal is to freeze the first repo-grounded
implementation map and create a review pack before implementation begins.

## Repo Intelligence Summary

Existing optional fast backend pattern:

- Python wrapper:
  - `src/rune_decrypter_prime/scoring/span_hamming/fast_backend.py`
- C++ pybind entry:
  - `src/rune_decrypter_prime/scoring/span_hamming/fast_bindings.cpp`
- C++ core:
  - `src/rune_decrypter_prime/scoring/span_hamming/FastSpanHamming.h`
- local build script:
  - `src/rune_decrypter_prime/scoring/span_hamming/setup_span_hamming_fast.py`
- parity tests:
  - `tests/scoring/span_hamming/test_fast_span_hamming_backend.py`
  - `tests/tools/test_no_wli_span_hamming_fast_backend_probe_v1.py`

The pattern is usable for build shape and parity-test style, but not for scorer
contract behavior. The new scorer must avoid span-Hamming score caps and must
count all eligible phrase hits exactly or fail loudly.

Filtered n-gram asset source:

- asset root:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1`
- asset builder reference:
  - `tools/benchmarks/scoring/word_ngrams/phaseB_filtered_ngram_index_v1_checked_patch/tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_filtered_ngram_index_v1.py`
- exact scanner/report reference:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_filtered_ngram_hard_pair_report_v1.py`

Observed asset schema:

```text
n
dictionary_cut
encoding_direction
rune_key_hex
rune_joined
rune_words
rune_lengths
rune_token_ids
word_token_ids
wli
count
log_count
phrase_count
top_latin_ngram
top_latin_count
latin_examples
source_file
```

Important field decision:

- `word_token_ids` is present and should be the primary source for
  word-structured phrase Hamming.
- Candidate chunks are flat rune-token sequences.
- Phrase assets are matched by structured `word_token_ids`.
- For each phrase entry, `word_token_ids` defines the word boundaries and
  per-word token sequences.
- `rune_token_ids` is used only as the flattened compatibility check and for
  exact joined-token diagnostics.
- `rune_key_hex` must stay metadata-only because it contains word separators.

Candidate/hard-pair input source:

- hard-pair road-test directory:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`
- candidate text source used by exact n-gram report:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1/candidate_full_texts.jsonl.gz`
- hard-pair summary:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1/pairwise_road_test_summary.csv`
- multiscore span-Hamming reference:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1`
- proxy coherence reference:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1`
- exact filtered n-gram reference:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_hard_pair_report_v1`

Candidate text shape:

- `candidate_full_texts.jsonl.gz` rows include:
  - `candidate_id`
  - `current_score`
  - `label`
  - `latin_render`
  - `panelA_score`
  - `token_count`
  - `token_hash`
  - `token_sequence_text`
  - `truth_match_ratio`
- `token_sequence_text` is whitespace-separated base-29 token ids.
- existing exact report chunks tokens into `500`-token chunks.

## Proposed File Placement

Reusable backend package:

```text
src/rune_decrypter_prime/scoring/ngram_hamming/
  __init__.py
  types.py
  reference.py
  backend.py
  fast_bindings.cpp
  FastNgramHamming.h
  setup_ngram_hamming_fast.py
```

Reason:

- keeps reusable scorer logic out of one-off report scripts
- mirrors optional `span_hamming` extension layout
- allows `tests/scoring/ngram_hamming/` parity tests
- avoids modifying working span-Hamming code

No-WLI report and asset scripts:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/
  validate_phaseB_ngram_hamming_assets_v1.py
  build_phaseB_ngram_hamming_phrase_index_v1.py
  run_phaseB_ngram_hamming_pilot_v1.py
  run_phaseB_ngram_hamming_hard_pair_report_v1.py
```

Tests:

```text
tests/scoring/ngram_hamming/test_reference_ngram_hamming.py
tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py
tests/tools/test_phaseB_ngram_hamming_assets_v1.py
tests/tools/test_phaseB_ngram_hamming_coherence_v1.py
```

## Implementation Slices

### Slice 0 - Damage Source Audit

Before any damage-ladder pilot, identify the existing word-Hamming damage
definitions for `20%`, `30%`, `40%`, and `50%` damage.

Record in `damage_manifest.json`:

- source file path
- damage model name
- damage levels
- seed or deterministic damage identifier
- whether damage is applied before or after chunking
- whether the same damaged streams are shared with word-Hamming comparison rows

The n-gram Hamming scorer must not invent a new damage model.

If the existing word-Hamming damage source cannot be located, the damage-ladder
pilot is blocked.

Hard-pair candidate scoring may still proceed as a separate comparability pilot,
but it must not be described as the `20-50%` controlled damage ladder unless the
damage source is verified.

### Slice 1 - Asset Validation

Create `validate_phaseB_ngram_hamming_assets_v1.py`.

Hardcoded constants:

- asset root
- output root
- enabled directions/cuts/orders
- asset mode fields

Required behavior:

- resolve repo root from script location
- validate all configured paths resolve under repo root unless explicitly
  read-only external input is documented
- require `rune_token_ids`
- require `word_token_ids`
- parse `word_token_ids` into a canonical nested token structure:

```text
tuple[tuple[int, ...], ...]
```

- prove `flatten(word_token_ids) == rune_token_ids`
- prove word lengths from `word_token_ids` equal `rune_lengths`
- prove the number of word-token groups equals `n`
- reject empty token sequences
- record sample/full mode
- summarize duplicates by `word_token_ids`, not Latin text
- prove same joined `rune_token_ids` with different word boundaries do not
  collapse together
- write repo-relative manifests and readout

### Slice 2 - Phrase Index Builder

Create `build_phaseB_ngram_hamming_phrase_index_v1.py`.

Index identity:

```text
direction
dictionary_cut
ngram_order
word_token_ids
```

`word_token_ids` must be parsed into a canonical nested structure:

```text
tuple[tuple[int, ...], ...]
```

Collapse phrase identity by:

```text
direction
dictionary_cut
ngram_order
canonical_word_token_ids
```

Store joined `rune_token_ids` as metadata and for compatibility checks. Do not
collapse word-structured phrases solely by joined tokens if word boundaries
differ.

Output should be JSONL or compact CSV/JSON manifests first. Binary indexing can
come only after the reference behavior is locked.

### Slice 3 - Python Reference Matcher

Create reusable reference logic in:

```text
src/rune_decrypter_prime/scoring/ngram_hamming/reference.py
```

Reference inputs:

- candidate token list
- phrase entries with `word_token_ids`
- profile object

Reference algorithm:

1. For each phrase entry, use its word lengths to define adjacent candidate word
   spans from each start offset.
2. Compute per-word Hamming distances.
3. Apply per-word, total-HD, normalised-HD, length, direction, cut, and order
   eligibility.
4. Count all eligible hits exactly.
5. Emit deterministic features and optional bounded examples.

This is intentionally simple and slow. It defines correctness.

### Slice 4 - Reference Tests

Add tests before C++:

- `test_word_token_ids_parses_to_canonical_nested_tuple`
- `test_word_token_ids_flatten_matches_rune_token_ids`
- `test_same_joined_tokens_different_word_boundaries_do_not_collapse`
- exact phrase hit
- one damaged word
- multiple damaged words
- below minimum phrase length rejected
- above total HD rejected
- above per-word HD rejected
- duplicate phrase collapse
- joined-string and word-structured phrase differ
- FWD/REV separation
- `rune_key_hex` rejected as scanning input
- debug examples do not change feature values
- `test_phrase_hits_per_opportunity_can_exceed_one`
- `test_positive_start_offset_fraction_is_bounded`
- `test_damage_source_manifest_is_required`
- `test_full_report_does_not_silently_fallback_backend`
- repeated run deterministic

### Slice 5 - Independent C++ Backend

Create the optional extension after reference tests are stable.

Recommended module name:

```text
rune_decrypter_prime.scoring.ngram_hamming._ngram_hamming_fast
```

Build script should follow the span-Hamming local build pattern, but all
configuration remains hardcoded in source. No script CLI arguments.

Backend contract:

- load phrase entries by profile/cut/order
- evaluate all eligible phrase placements exactly
- return counters:
  - `candidate_tokens_scanned`
  - `candidate_start_offsets_considered`
  - `phrase_entries_considered`
  - `phrase_verification_attempts`
  - `phrase_verification_passes`
  - `phrase_hits`
  - `unique_phrase_hits`
  - `opportunity_count`
  - `runtime_ms`
- fail loudly for impossible profiles instead of dropping hits
- bounded debug examples are output-only and do not affect scoring

Backend fallback rule:

- The Python reference implementation defines correctness.
- Small tests and tiny pilots may deliberately use the Python reference path.
- Every pilot/report must record `backend_impl` explicitly.
- If a full report is configured to use C++ and the C++ backend is unavailable,
  the run must fail clearly rather than silently switching to Python.

### Slice 6 - Exact No-Cap Pilot

Create `run_phaseB_ngram_hamming_pilot_v1.py`.

First pilot shape:

```text
candidates: 10
chunks: 20
direction: fwd
cuts: normal
orders: 2, 3
profiles: P0, P1, P2
damage_levels: 20, 30, 40, 50
```

Candidate selection must be deterministic and deliberate, not first-row order.
Prefer a small stable set containing:

- some current-correct pairs
- some current-misranked pairs
- truth-better candidates
- truth-worse candidates
- stable sorted candidate IDs

No long-run launch is expected for this pilot. If runtime unexpectedly becomes
long-running, stop and write a runtime-budget note before continuing.

The hard-pair comparability pilot may use:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1/candidate_full_texts.jsonl.gz
```

The controlled `20-50%` damage ladder may not rely on that file alone. It must
use the verified word-Hamming damage source from Slice 0.

### Slice 7 - Expanded Pilot And Full Report

Expanded pilot adds strict, order `4`, P3, and P4.

Full hard-pair report is gated behind:

- asset validation pass
- reference tests pass
- backend parity pass
- exact no-cap pilot pass
- expanded pilot pass

## Review Questions

1. Is `src/rune_decrypter_prime/scoring/ngram_hamming/` the right backend package
   location?
2. Should phrase identity collapse by `word_token_ids` only, with joined
   `rune_token_ids` as metadata, as proposed?
3. Is it acceptable for Slice 1 and Slice 2 to write plain JSON/CSV first before
   any binary phrase-index format exists?
4. Should the first reference matcher iterate phrase entries over offsets, or
   should it start with an anchor-and-verify structure even in Python?
5. Are the proposed test file locations acceptable?
6. Should the first pilot reuse the exact report's `candidate_full_texts.jsonl.gz`
   input, or should it rebuild candidate chunks directly from the hard-pair road
   test manifests?

## Review Amendments Accepted - 2026-05-14

The start plan is approved for implementation after these amendments:

- add Slice 0 damage-source audit before any controlled `20-50%` damage-ladder
  claim
- parse `word_token_ids` into canonical nested tuples and validate it against
  `rune_token_ids`, `rune_lengths`, and `n`
- state clearly that candidate chunks are flat token streams while phrase assets
  are word-structured
- require explicit `backend_impl`; no silent Python fallback when a full report
  is configured for C++
- split opportunity metrics into hit density and bounded positive-offset
  fraction
- choose first pilot candidates deliberately and deterministically

## Opportunity Metrics Amendment

The primary opportunity denominator remains:

```text
opportunity_count = number of candidate start offsets at which at least one
phrase in the active phrase index could fit within the chunk length and profile
length limits
```

Because multiple phrases may hit at the same start offset,
`phrase_hit_count / opportunity_count` can exceed `1.0`. Report it as:

```text
phrase_hits_per_opportunity = phrase_hit_count / opportunity_count
```

Also report the bounded start-offset metric:

```text
positive_start_offset_count = number of start offsets with at least one accepted phrase hit
positive_start_offset_fraction = positive_start_offset_count / opportunity_count
```

`positive_start_offset_fraction` should be in `[0.0, 1.0]` when
`opportunity_count > 0`.

## What Did Not Change

- No production scorer weights changed.
- No solver runtime was launched.
- No new CLI arguments are proposed.
- No FWD/REV pooling is proposed.
- Exact filtered n-gram v1 remains closed as a reference/baseline only.

## Exact No-Cap And Scorer-Design Progress - 2026-05-29

After C++ Slice 2 approval, the exact no-cap hard-pair comparability path was
implemented and advanced through bounded scale-up.

Completed gates:

- amended fast real-index smoke:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_fast_real_index_smoke_v1`
  - status: `pass`
  - backend: `cpp_fast`
  - Python fallback allowed: `false`
- exact no-cap full pilot:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_exact_no_cap_full_pilot_v1`
  - status: `pass`
  - scan cells: `120 / 120`
  - source total hits: `14`
- bounded expansion:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bounded_expansion_v1`
  - status: `pass`
  - scan cells: `600 / 600`
  - source total hits: `188`
- balanced readout:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_balanced_readout_v1`
  - status: `pass`
  - scan cells: `708 / 708`
  - source total hits: `328`
  - candidates: `118`
  - P1/P2 same-hit-count candidates: `117 / 118`
  - P0 audit/control positive rows: `1`

Balanced readout interpretation:

- output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_balanced_readout_interpretation_v1`
- review pack: `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_balanced_readout_interpretation_v1_review_pack_2026-05-29.zip`
- status: `pass`
- readout:
  - known-better mean hits: `4.000`
  - known-worse mean hits: `0.211`
  - panel-rescue known-better hits: `0`

Current scorer-design slice:

- source: `tools/benchmarks/periodic_sub_trans/no_wli/analysis/design_phaseB_ngram_hamming_nonproduction_scorer_v1.py`
- test: `tests/tools/test_phaseB_ngram_hamming_nonproduction_scorer_design_v1.py`
- output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_nonproduction_scorer_design_v1`
- status: `review_ready`
- proposed non-production primary signal:
  - `normal_order2_P2_raw_weighted_hits`
- comparison/audit:
  - P1 redundancy check
  - P0 exact-hit audit/control flag
  - claim-mode/provenance manifest

Current stop point:

- non-production scorer-design review is required before any integration.
- no production scorer behavior has changed.
- no controlled `20-50%` damage-ladder claim is made.
- no strict/order-4/P3/P4 expansion has started.
- no broad pilot or full hard-pair report has started.

## Non-Production Combination Simulation - 2026-05-29

The non-production scorer design slice was approved for simulation with:

```text
primary signal = normal_order2_P2_raw_weighted_hits
log1p(P2) = combination-time only
P0 = audit/control only
panel_rescue_known_better = no rescue claim
```

Implemented combination simulation:

- source: `tools/benchmarks/periodic_sub_trans/no_wli/analysis/simulate_phaseB_ngram_hamming_nonproduction_scorer_combination_v1.py`
- test: `tests/tools/test_phaseB_ngram_hamming_nonproduction_scorer_combination_v1.py`
- output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_nonproduction_scorer_combination_v1`
- status: `review_ready`

Compared score modes:

```text
current_score_only
p2_raw_weighted_hits_only
current_score_plus_log1p_p2
```

Key readout:

```text
known_better - known_worse mean margin:
  current_score_only: 0.157779
  p2_raw_weighted_hits_only: 19.907640
  current_score_plus_log1p_p2: 1.879158

high_truth_stable_fill - bad_control mean margin:
  current_score_only: 0.241644
  p2_raw_weighted_hits_only: 39.070103
  current_score_plus_log1p_p2: 3.800268

panel_rescue_known_better:
  P2-hit candidates: 0 / 20
```

Pairwise inversion note:

- only `2` same-source-pair comparisons are available in this balanced panel.
- `current_score_only` prefers known-better in `1 / 2` and known-worse in `1 / 2`.
- `p2_raw_weighted_hits_only` prefers known-better in `1 / 2` and ties `1 / 2`.
- `current_score_plus_log1p_p2` inherits the same current-score inversion in
  the zero-P2 pair.

Current stop point:

- non-production combination simulation review is required before any scorer integration.
- no production scorer behavior has changed.
- no controlled `20-50%` damage-ladder claim is made.
- no rescue-performance claim is made.
- no strict/order-4/P3/P4 expansion has started.
- no broad pilot or full hard-pair report has started.

## Asset Provenance And Sample-Index All-Candidate Matrix - 2026-05-29

Asset provenance checkpoint:

- source: `tools/benchmarks/periodic_sub_trans/no_wli/analysis/inventory_phaseB_ngram_hamming_asset_provenance_v1.py`
- test: `tests/tools/test_phaseB_ngram_hamming_asset_provenance_inventory_v1.py`
- output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_asset_provenance_inventory_v1`
- status: `pass`
- dataset status: `sample_index_confirmed`
- full raw n-gram rebuild confirmed: `false`
- phrase index entries: `196680`
- phrase index SHA256: `ded2c46e9fa27ff4ea6cd126bd0d3d3f59da86b73a11a254e8cbe0c21bf733e5`
- raw sample index covers:
  - dictionary cuts: `normal`, `strict`
  - directions: `fwd`, `rev`
  - orders: `2`, `3`, `4`, `5`
  - sample line limit per order: `25000`

Decision from provenance:

- current outputs are internally consistent and use the expected sample phrase index.
- current outputs do not support a full raw n-gram rebuild claim.
- any next matrix using this index must be labelled sample-index based.

Sample-index all-candidate matrix:

- source: `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1.py`
- test: `tests/tools/test_phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1.py`
- output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1`
- log: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1/sample_index_matrix_refactor_rerun_2026-05-29.log`
- status: `pass`
- dataset status: `sample_index_confirmed`
- scope:
  - candidates: `604`
  - chunks: `1208`
  - scan cells: `3624 / 3624`
  - cut/order: `normal` / `2`
  - profiles: `P0`, `P1`, `P2`
- backend: `cpp_fast`
- Python fallback allowed: `false`
- elapsed seconds: `386.052`
- measured attempts per second: `16394011.827`
- total hits: `1051`
- candidates with hits: `243 / 604`

Implementation hardening amendment:

- the matrix runner is now a standalone hardcoded runner, not a monkeypatch wrapper
  around the balanced readout runner.
- it still reuses pure parsing/scanning/output helpers from the balanced module, but
  does not mutate balanced runner globals or replace balanced runner functions.
- regression coverage now checks that building the matrix config does not mutate
  the balanced runner config.
- refreshed full matrix rerun from the corrected runner completed `3624 / 3624`
  cells with `status=pass`.

Profile hit readout:

```text
P0 hits = 1
P1 hits = 533
P2 hits = 517
```

Role hit readout:

```text
known_better hits = 1026
known_worse hits = 24
mixed_pair_role hits = 1
```

Sample-index all-candidate matrix interpretation:

- source: `tools/benchmarks/periodic_sub_trans/no_wli/analysis/interpret_phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1.py`
- test: `tests/tools/test_phaseB_ngram_hamming_sample_index_all_candidate_matrix_interpretation_v1.py`
- output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_sample_index_all_candidate_matrix_interpretation_v1`
- status: `review_ready`
- hard-pair rows evaluated: `2594`

Pairwise preference readout:

```text
current_score_only:
  known-better preferred = 1992 / 2594
  known-worse inversions = 602 / 2594
  inversion rate = 0.232074

p2_raw_weighted_hits_only:
  known-better preferred = 572 / 2594
  known-worse inversions = 280 / 2594
  ties = 1742 / 2594
  inversion rate = 0.107941

current_score_plus_log1p_p2:
  known-better preferred = 1804 / 2594
  known-worse inversions = 790 / 2594
  inversion rate = 0.304549

gated_current_plus_log1p_p2:
  known-better preferred = 618 / 2594
  known-worse inversions = 236 / 2594
  ties = 1740 / 2594
  inversion rate = 0.090979
```

Guarded interpretation:

- P2 raw and gated blend are conservative: many ties, lower known-worse inversion rates.
- the naive blend breaks more ties but increases known-worse inversions.
- panel-rescue remains blocked:
  - `panel_rescue_known_better` P2-hit candidates: `0 / 20`
- high-truth versus bad-control separation remains strong under P2/gated modes.

Current stop point:

- sample-index all-candidate matrix interpretation review is required before scorer integration.
- no production scorer behavior has changed.
- no full raw n-gram rebuild claim is allowed from these outputs.
- no controlled `20-50%` damage-ladder claim is made.
- no rescue-performance claim is made.
- no strict/order-4/P3/P4 expansion has started.

## Full-Raw Build-And-Run Tranche: P3 Contract Review Point - 2026-05-29

Requested next tranche:

- prepare a serious full-raw n-gram Hamming matrix.
- build/complete full raw assets for `fwd`, cuts `normal`/`strict`, orders `2`/`3`.
- implement `P3_word_shape_guarded_len8_hd2`.
- run a full-asset canary before any long matrix.
- keep `whole_phrase_only`; do not introduce phrase-internal windows.
- do not make production scorer changes.

Implemented P3 profile contract support:

- Python reference: `src/rune_decrypter_prime/scoring/ngram_hamming/reference.py`
- C++ backend: `src/rune_decrypter_prime/scoring/ngram_hamming/FastNgramHamming.h`
- pybind payload parser: `src/rune_decrypter_prime/scoring/ngram_hamming/fast_bindings.cpp`
- rebuilt extension: `src/rune_decrypter_prime/scoring/ngram_hamming/_ngram_hamming_fast.cp311-win_amd64.pyd`

P3 contract:

```text
profile_id = P3_word_shape_guarded_len8_hd2
min_phrase_token_length = 8
max_total_phrase_hd = 2
max_word_hd = 1
exact_match_word_lengths = (1, 2)
```

Implementation detail:

- `len8` remains a minimum full phrase rune-token length gate.
- the scanner still verifies the whole phrase and records `hit_end = hit_start + phrase_token_length`.
- P3 adds a generic profile field, `exact_match_word_lengths`, so words of rune length `1` or `2` must have word HD `0`.
- scanner mode remains `whole_phrase_only`; phrase-internal windows are not implemented or mixed into this tranche.

Length-bias warning for the full-raw data-taking tranche:

```text
scan_mode = whole_phrase_only

For each indexed n-gram phrase:
  - keep the full encoded phrase
  - require phrase_token_length >= profile.min_phrase_token_length
  - scan the full phrase at every candidate-token start offset
  - do not truncate to 8 runes
  - do not generate internal phrase windows
```

The P2/P3 `min_phrase_token_length >= 8` rule is a minimum length gate, not a
fixed-length comparison. Therefore an 8-rune phrase and a 20-rune phrase can
both score, but they are not equivalent evidence:

```text
8-rune phrase with HD <= 2  -> up to 25% mismatch
20-rune phrase with HD <= 2 -> up to 10% mismatch
```

This means the current whole-phrase method has phrase-length bias: longer
phrases are stricter in relative mismatch terms, while shorter eligible phrases
are more tolerant. This is a deliberate data-taking choice for this tranche, not
a settled production scoring policy.

Future agents and reviewers must not treat P2/P3 as fixed-length 8-rune
evidence. They are currently whole-phrase evidence with a minimum length gate.

Alternative method explicitly excluded from this run:

```text
fixed_window_internal_phrase_scan

For a phrase longer than the threshold:
  - generate all fixed-length internal windows, e.g. all 8-rune windows
  - scan each window separately
```

This may make comparisons more length-uniform, but introduces a different bias
because longer phrases produce more windows and therefore more chances to hit.
Do not implement or silently mix internal phrase windows in the upcoming
full-raw tranche.

Required per-hit or streamed-hit-summary fields for the full-raw run:

```text
ngram_order
profile_id
cut
direction
phrase_token_length
word_lengths
word_hds
total_phrase_hd
max_word_hd
short_word_mismatch_count
phrase_count
phrase_log_count
hit_start
hit_end
candidate_id
chunk_id
```

Required aggregate diagnostics for the full-raw run/review summary:

```text
hit count by phrase-token-length bin:
  8-10
  11-15
  16-20
  21+

weighted hit sum by phrase-token-length bin

known_better / known_worse / bad_control split by phrase-token-length bin

P2 hits by phrase-token-length bin

P3 retained hits by phrase-token-length bin

P2-only hits rejected by P3, by phrase-token-length bin

word-length pattern distribution, e.g.:
  [1, 10]
  [2, 8]
  [4, 5]
  [3, 3, 4]

frequency/log-count bins:
  low
  medium
  high
  very_high
```

The next full-raw asset/build/run review summary must repeat this warning and
must report enough length, word-shape, and frequency detail to decide later
whether to keep whole-phrase scoring, normalise by phrase length, or define a
separate fixed-window scorer.

Focused tests added:

- `tests/scoring/ngram_hamming/test_reference_ngram_hamming.py`
- `tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py`

Test coverage now verifies:

- P2/P3 scan the full phrase, not only the first 8 runes.
- candidate chunks are scanned at every token offset.
- P3 rejects mismatches in words of length `1` or `2`.
- Python/C++ parity for P3.

Verification:

```text
python -m pytest tests/scoring/ngram_hamming/test_reference_ngram_hamming.py tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py
32 passed in 0.15s

python -m pytest tests/scoring/ngram_hamming tests/tools/test_phaseB_ngram_hamming_asset_provenance_inventory_v1.py tests/tools/test_phaseB_ngram_hamming_fast_real_index_smoke_v1.py tests/tools/test_phaseB_ngram_hamming_exact_no_cap_pilot_v1.py tests/tools/test_phaseB_ngram_hamming_exact_no_cap_full_pilot_v1.py tests/tools/test_phaseB_ngram_hamming_bounded_expansion_v1.py tests/tools/test_phaseB_ngram_hamming_balanced_readout_v1.py tests/tools/test_phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1.py
70 passed in 25.48s
```

Current review stop:

- P3 parity tests pass.
- full raw assets have not yet been built in this tranche.
- no full raw scan or canary has been launched yet.
- no production scorer behavior has changed.

## Full-Raw Asset Canary Rescope - 2026-05-29

Broad build attempt:

- launched `build_phaseB_ngram_hamming_full_raw_assets_v1.py` for `fwd`, cuts
  `normal`/`strict`, orders `2`/`3`.
- stopped after about `39` minutes because it had not reached a completed
  independently reviewable asset cell.
- progress reached `n=2`, `26,000,000` raw lines, still inside the 2-gram raw
  source set.
- generated only initial config/manifest files; no completed full raw asset file
  should be treated as available from this stopped attempt.

Reason for rescope:

- the first canary unit was too broad.
- it was teaching raw build throughput, not the intended canary question:
  whether a completed full-data asset cell can be scanned, diagnosed, and used
  to size the next cell.
- do not present this stopped build as a full raw asset/provenance pass.

Rescoped next unit:

```text
asset_scope = first_cell_normal_fwd_order2
asset_mode = full
full_raw_cell_available = true required
full_required_matrix_available = false
sample_line_limit_per_order = none / absent
direction = fwd
cut = normal
order = 2
profiles for scan = P2, P3
scan_mode = whole_phrase_only
internal_phrase_windows = false
```

New first-cell builder:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_first_cell_assets_v1.py`
- hardcoded first independently complete cell only: `normal / fwd / order-2`.
- logs completed files, raw lines, kept rows, elapsed time, and rough ETA.
- writes a manifest that explicitly says the full required matrix is not yet
  available.

This is a proper rescope, not a shortcut:

- sample-index evidence still cannot be presented as full raw.
- the first-cell asset can only support first-cell canary conclusions.
- full `normal`/`strict`, order `2`/`3` assets still require later build steps
  after the first completed cell gives a timing and scan anchor.

Verification after rescope:

```text
python -m py_compile tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_first_cell_assets_v1.py
pass

python -m pytest tests/tools/test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py
7 passed in 0.19s
```

Correction after user review:

- the `first_cell_normal_fwd_order2` build was still too broad for the intended
  canary meaning.
- it was stopped before completion.
- do not treat that run as a completed asset, canary, or reviewable full-raw
  data point.

Revised canary definition:

```text
canary purpose:
  prove workflow, provenance labels, data integrity checks, output schemas,
  P2/P3 scan plumbing, pack hygiene, and full/sample gate behaviour

canary must not:
  claim full raw asset availability
  scan a complete raw order/cut cell
  size the full matrix from incomplete evidence
  hide sample caps or backfill missing data
```

The next canary should be explicitly labelled as a probe, for example:

```text
asset_mode = canary_probe
full_asset_available = false
full_raw_ngram_rebuild_confirmed = false
sample_line_limit_per_order = explicit non-null probe cap
required_asset_mode_for_long_run = full
long_run_full_gate_result = blocked_as_expected_for_probe
scan_mode = whole_phrase_only
internal_phrase_windows = false
```

After the probe passes, the full raw build remains a separate asset-building
stage. A full raw asset/provenance pass requires completed full asset files, not
canary probe outputs.

## Canary Probe Completion - 2026-05-29

Corrected canary-probe scripts:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_canary_probe_assets_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/summarise_phaseB_ngram_hamming_canary_probe_assets_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_canary_probe_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_canary_probe_review_pack_v1.py`

Canary-probe asset contract:

```text
asset_mode = canary_probe
builder_run_mode = sample
full_asset_available = false
full_raw_ngram_rebuild_confirmed = false
sample_line_limit_per_order = 25000
direction = fwd
cuts = normal, strict
orders = 2, 3
scan_mode = whole_phrase_only
internal_phrase_windows = false
```

Probe asset summary:

```text
status = pass
phrase_entries = 28487
```

Canary-probe scan:

```text
status = pass
backend_impl = cpp_fast
python_fallback_allowed = false
completed_scan_cells = 24 / 24
cuts = normal, strict
orders = 2, 3
profiles = P2, P3
candidates = one known_better, one known_worse, one bad_control
full_run_gate_on_probe_assets = blocked_as_expected_for_probe
```

Important interpretation:

- this canary proves workflow, provenance labels, data integrity checks, output
  schemas, P2/P3 scan plumbing, and full/sample gate behaviour.
- this canary does not prove full raw asset availability.
- this canary must not be used as long-run runtime sizing evidence.
- long-run setup still requires a separate full raw asset build with no
  `sample_line_limit_per_order` and no hidden candidate cap.

## Pre-Long-Run External Review Pack - 2026-05-30

Created review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_pre_long_run_external_review_pack_2026-05-30.zip
```

Pack purpose:

- external review before launching the real full raw long run.
- asks whether the canary probe correctly proves workflow/data contract and
  whether the next long-run preparation step is safe.
- explicitly states that the canary probe is not full raw evidence and is not
  valid long-run runtime sizing.

Pack contents include:

- active plan and `AGENTS.md`.
- reviewer summary and review questions.
- canary probe asset summary outputs.
- canary probe scan outputs and hit diagnostics.
- P2/P3 Python and C++ contract files.
- focused tests for P3/canary/full-run gate behaviour.
- full raw asset/canary scripts for reviewer context.

Pack hygiene:

```text
entry_count = 32
backslash_entries = 0
```

Still blocked until review approval:

- launching the full long matrix.
- presenting probe data as full raw.
- using capped probe timing as long-run sizing.
- production scorer changes.

## Pre-Long-Run Review Amendments - 2026-05-30

External review verdict:

```text
pre-long-run review pack = good
long run launch = not yet approved
next step = full raw asset build/provenance after small amendments
```

Required amendments applied:

1. strengthened the full-run gate so `phrase_index_path` must:
   - exist;
   - end with `.jsonl.gz`;
   - be gzip-readable;
   - contain a JSON first row;
   - include required phrase fields;
   - have `phrase_entry_count > 0`.
2. full raw builder provenance now records both:
   - `builder_requested_run_mode`;
   - `builder_requested_sample_line_limit_per_order`;
   - `normalised_asset_mode`;
   - `normalised_sample_line_limit_per_order`.
3. emitted repo-relative path strings are normalised to POSIX-style `/` where
   the canary/full-raw scripts control the manifest content.
4. review/readout docs now state:

```text
P3 eligible phrase count may equal P2 eligible phrase count.
The P3 effect is measured by P3-retained hits and P2-only hits rejected by P3.
```

The canary hits remain an important warning example:

```text
P2 hits = 2
P3 retained hits = 0
P2-only rejected by P3 = 2
short_word_mismatch_count = 1
```

Still not approved:

- full long matrix launch.
- production scorer changes.
- treating canary/probe assets as full raw evidence.

## Strict Contract-And-Diagnostics Amendment Pass - 2026-05-30

Purpose:

- tighten long-run data contract before any full raw build/long run.
- preserve enough diagnostics to inspect phrase-length and word-length bias.
- keep full long matrix blocked.

Implemented amendments:

1. Full asset build provenance now records:

```text
builder_requested_run_mode
builder_requested_sample_line_limit_per_order
effective_builder_run_mode
effective_sample_line_limit_per_order
checked_builder_full_mode_uses_no_sample_cap
normalised_asset_mode
normalised_sample_line_limit_per_order
```

The helper rule is explicit:

```text
effective_sample_line_limit_for_builder("full", 0) == None
effective_sample_line_limit_for_builder("sample", 25000) == 25000
```

2. Phrase-index summariser now validates full phrase-index rows while
summarising:

```text
required fields present
valid token lists
phrase_token_length == len(rune_token_ids)
word_lengths == lengths of word_token_ids
sum(word_lengths) == phrase_token_length
flatten(word_token_ids) == rune_token_ids
ngram_order == len(word_token_ids)
count/log_count fields numeric
direction/cut/order inside required sets
```

The summary manifest records:

```text
phrase_index_rows_checked
phrase_index_invalid_row_count
phrase_index_invalid_examples
```

3. Duplicate phrase identities are no longer overwritten silently in the full
asset summariser. Duplicate collapse preserves:

```text
sum_count
max_count
max_log_count
phrase_count
top_latin_ngram_for_max_count
duplicate_row_count
```

4. Hit rows now record short-word/non-short-word diagnostics:

```text
short_word_count
short_word_token_count
short_word_hd
short_word_mismatch_count
non_short_word_count
non_short_word_token_count
non_short_word_hd
short_word_fraction_of_phrase
normalised_total_hd
normalised_non_short_hd
```

5. Aggregate diagnostic tables now include non-mixing keys:

```text
profile_id
cut
direction
ngram_order
candidate_role
```

This applies to phrase-length, word-pattern, frequency/log-count,
P2/P3-retention, total-HD, normalised-HD, short-word-fraction,
non-short-token-count, and normalised-non-short-HD summaries.

6. Per candidate/chunk/cut/order/profile aggregate rows are emitted for later
rescoring without rerunning the scan:

```text
candidate_chunk_profile_aggregate_rows.csv
```

7. Regenerated canary probe confirms the new diagnostics:

```text
status = pass
completed_scan_cells = 24 / 24
backend_impl = cpp_fast
full_run_gate_on_probe_assets = blocked_as_expected_for_probe
total_hit_count = 2
```

The two P2-only canary hits still show the short-word issue clearly:

```text
word_lengths = [1, 10]
word_hds = [1, 0]
short_word_mismatch_count = 1
non_short_word_token_count = 10
normalised_non_short_hd = 0
P3 retained = 0
```

Verification:

```text
python -m pytest tests/tools/test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py
13 passed in 0.12s
```

Updated pre-long-run review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_pre_long_run_external_review_pack_2026-05-30.zip
entry_count = 38
backslash_entries = 0
```

Current stop point:

- strict diagnostics/gates are implemented and tested.
- canary probe outputs were regenerated with the stricter schema.
- no full raw asset build launched.
- no full long matrix launched.

## Final Pre-Full-Build Contract Amendments - 2026-05-30

External review requested one more amendment pass before full raw asset build.

Implemented:

1. Removed full-builder sample-cap ambiguity.

```text
builder_requested_sample_line_limit_per_order = 0
effective_sample_line_limit_per_order = None
actual_build_config_sample_line_limit_per_order = None
```

The full builder now passes the effective value directly into `BuildConfig`.
For full mode that value is `None`, not `0`.

2. Zero-hit candidate/chunk/profile aggregate rows are explicit.

`candidate_chunk_profile_aggregate_rows.csv` now emits one row for every scanned
candidate/chunk/cut/direction/order/profile cell, including cells with no hits:

```text
raw_hit_count = 0
unique_phrase_hit_count = 0
weighted_hit_sum = 0
max_phrase_log_count = 0
mean_phrase_log_count = 0
```

3. Per-hit rows now preserve collapsed frequency metadata:

```text
sum_count
max_count
max_log_count
duplicate_row_count
top_latin_ngram_for_max_count
```

4. Phrase-index validation rejects bad token/count shapes rather than relying on
permissive casts:

```text
bool tokens
float tokens where ints are required
string tokens
tokens outside 0..28
empty word_token_ids
empty words
empty rune_token_ids
non-positive word lengths
bool word lengths
non-finite count/log values
negative counts
non-positive phrase_count
```

5. Active plan header updated:

```text
Work status = pre_long_run_external_review_ready
Last updated = 2026-05-30
Current gate = full raw asset build/provenance not yet launched
```

Verification:

```text
python -m pytest tests/tools/test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py
17 passed in 0.18s
```

Regenerated canary probe still passes:

```text
completed_scan_cells = 24 / 24
backend_impl = cpp_fast
full_run_gate_on_probe_assets = blocked_as_expected_for_probe
total_hit_count = 2
```

Updated review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_pre_long_run_external_review_pack_2026-05-30.zip
entry_count = 38
backslash_entries = 0
```

Current stop point:

- final pre-full-build contract amendments are implemented and tested.
- probe outputs and review pack are rebuilt.
- no full raw asset build launched.
- no full long matrix launched.

## Full Raw Asset Build/Provenance Launch Prep - 2026-05-30

External review approved the next step:

```text
approved = full raw asset build/provenance only
not approved = full long matrix
```

Small schema clarity amendment applied before launch:

```text
candidate_chunk_profile_aggregate_rows.csv
  cell_p2_hit_count
  cell_p3_retained_hit_count
  cell_p2_only_rejected_by_p3_count
```

The `cell_` prefix clarifies that P2/P3 retention fields are cell-level
comparison fields, not profile-specific hit fields.

Full asset build progress logging amendment:

- checked n-gram builder now emits:
  - files completed versus total;
  - completed bytes versus total source bytes;
  - elapsed time;
  - ETA by completed source bytes where available;
  - line throughput.
- final checked-builder output path is printed repo-relative when under the
  repo root.

Verification before launch:

```text
python -m pytest tests/tools/test_phaseB_ngram_hamming_full_raw_asset_canary_v1.py
17 passed in 0.18s
```

Planned launch scope:

```text
direction = fwd
cuts = normal, strict
orders = 2, 3
asset_mode = full
sample_line_limit_per_order = None / absent
full long matrix = not launched
```

Stop after:

- full raw assets are built and summarised into a provenance pack; or
- the asset build blocks/fails with a clear reason.

Full raw asset build launch:

```text
first launch:
  status = failed immediately
  reason = checked builder config writer cast None sample_line_limit_per_order to int
  fix = checked builder jsonable_config now preserves None

current launch:
  status = running
  pid = 4684
  intended_wallclock_budget = 36h
  stop_condition = full_raw_asset_build_completes_or_fails_clear_reason
  log = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_assets_v1/full_raw_asset_build_20260530_013137.log
  launcher = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_assets_v1/run_full_raw_asset_build_20260530_013137.ps1
  visible_tracker = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_assets_v1/watch_full_raw_asset_build_20260530_013137.ps1
  visible_tracker_pid = 1120
  full_long_matrix_launch = false
```

Early progress:

```text
n=2 source_files = 200
files_completed = 15 / 200
completed_bytes = 55,581,169 / 3,146,485,317
elapsed ~= 1m06s at last check
eta_by_completed_bytes ~= 1h01m for n=2 at last check
```

Next action after build completes:

1. run `summarise_phaseB_ngram_hamming_full_raw_assets_v1.py`;
2. build a full raw asset/provenance review pack;
3. stop for review before any full canary or long matrix launch.

Restart after interrupted hidden run:

```text
previous_pid = 4684
previous_status = stopped/interrupted before completion
previous_log = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_assets_v1/full_raw_asset_build_20260530_013137.log
completion_manifest_found = false

visible_restart_pid = 18112
visible_restart_status = stopped before completion
visible_restart_log = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_assets_v1/full_raw_asset_build_20260530_021540.log
visible_restart_launcher = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_assets_v1/run_full_raw_asset_build_VISIBLE_20260530_021540.ps1
```

The restart uses a visible PowerShell window and streams stdout/stderr through
`Tee-Object` into the repo-relative log.

Second build status check:

```text
checked_at = 2026-05-30
build_running = false
python_build_process_found = false
full_raw_build_manifest_found = false
completed_asset_files_found = false
latest_log_last_write = 2026-05-30 09:16:02
latest_progress_line =
  n=2 files_completed=107/200
  completed_bytes=1,162,148,622/3,146,485,317
  lines=60,000,000
  current_file=5 6.txt
  elapsed=7h00m19s
  eta_by_completed_bytes=11h57m42s
  lines_per_sec=2,379.1
```

No Python traceback, exception, or completed manifest was present in the log.
The output directory for this attempt contains only the initial `config.json`
and `dictionary_manifest.json`; no partial full raw asset file was emitted.

Interpretation:

- the monolithic checked builder holds aggregate dictionaries for a whole
  order/cut/direction output before writing any completed asset files;
- throughput degraded from tens of thousands of rows per second early in
  `n=2` to roughly `2,379` rows per second by the final progress line;
- repeated interruption around the same large `n=2` aggregation stage points
  to memory pressure / large-dictionary aggregation overhead rather than a
  data contract failure;
- do not restart the same monolithic full build again.

Required next implementation direction:

- replace or wrap the full raw asset build with a memory-bounded, resumable
  build strategy;
- emit independently complete shard or cell outputs before the whole order is
  finished;
- preserve duplicate phrase identity collapse metadata during merge:
  `sum_count`, `max_count`, `max_log_count`, `phrase_count`,
  `top_latin_ngram_for_max_count`, and `duplicate_row_count`;
- keep repo-relative logs, visible PowerShell launch, completed/total progress,
  elapsed time, ETA, and partial-output extractability;
- produce a full raw asset/provenance review pack only after the redesigned
  build completes or fails with a clear blocker.

General long-run lesson:

- reusable shard builds are probably the right default pattern for long
  data-taking runs in this project, especially when source data is large,
  duplicate collapse is required, or a process may run overnight;
- prefer independently complete shards with manifests, progress logs, and
  merge/audit stages over monolithic jobs that hold all aggregate state in
  memory until the end;
- shard outputs should be reviewable on their own, resumable after interruption,
  and mergeable without losing provenance or duplicate/frequency metadata.
- before building additional full raw asset families, run a small representative
  profiling slice and remove obvious repeated work from the builder; do not
  assume a recoverable shard design is automatically speed-efficient.
- current likely builder hot spots to audit before more asset builds:
  repeated dictionary-cut membership checks, repeated rune encoding for rows
  kept by both strict and normal, large Python aggregate dictionaries, sorting
  aggregate rows before gzip output, and gzip/CSV write overhead.

Quick profile check while shard build was running:

```text
profile_script = inline read-only cProfile probe
profile_source = order 2, source file 1 6.txt
profile_max_lines = 200,000
lines_seen = 179,169
normal_kept_rows = 9,756
strict_kept_rows = 2,303
encode_phrase_calls = 12,059
```

Top cumulative costs in the scan-only profile:

```text
scan_sources_for_order = 2.999s cumulative
parse_ngram_line_with_reason = 1.251s cumulative
encode_phrase = 0.857s cumulative
Runeglish.encode_english_to_runes = 0.573s cumulative
plain-word checks / normalisation / dictionary loops = material secondary cost
```

Interpretation:

- current shard build is recoverable but not speed-optimal;
- strict rows are encoded separately from normal rows, so rows accepted by both
  cuts pay duplicate encoding cost;
- this profile did not include gzip/sort write cost, which remains a separate
  likely cost for large shards;
- before building additional asset families, implement or review a builder path
  that parses once, computes cut eligibility once, encodes once per kept
  phrase/direction, and then writes that encoded phrase into all applicable cut
  buckets.

Optimized shard-builder restart decision:

```text
decision = stop current shard process and resume with optimized scan path
reason = future asset families will reuse this builder pattern, so remove the
  obvious repeated encoding now instead of accepting a known naive hot path
stopped_python_pid = 7616
completed_shards_preserved_before_stop = 211 / 1118
completed_bytes_preserved_before_stop = 3,161,284,955 / 21,114,123,555
```

Implemented in:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_asset_shards_v1.py
```

New shard scan contract:

```text
USE_OPTIMIZED_SCAN = true
RESUME_LATEST_INCOMPLETE_RUN = true
parse each raw row once
compute normal/strict eligibility once
encode once per kept phrase/direction
add same encoded phrase to all kept cut buckets
skip shards with existing pass shard_manifest.json
ETA after resume uses resume-adjusted completed bytes, not stale completed bytes
with a fresh timer
```

Equivalence check before restart:

```text
profile_source = order 2, source file 1 6.txt
sample_line_limit_per_order = 200,000
original scanner vs optimized scanner = pass
normal/fwd aggregate keys = 9722
strict/fwd aggregate keys = 2301
output stats matched = true
aggregate key sets matched = true
```

Optimized visible resume:

```text
pid = 9064
python_pid = 7348
log = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/full_raw_asset_shards_optimized_resume_20260530_164433.log
run_root = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/20260530T120414Z__phaseB_ngram_hamming_full_raw_asset_shards_v1
resume_completed_shards = 214 / 1118
resume_completed_bytes = 3,171,619,883 / 21,114,123,555
first_new_completed_shard_after_resume = 215 / 1118
eta_method = resume_adjusted_completed_bytes
```

Current full raw shard-build scope and deferred options:

```text
current_build_scope:
  asset_mode = full
  sample_line_limit_per_order = None
  direction = fwd only
  cuts = normal, strict
  orders = 2, 3
  shard_mode = one_source_file_per_shard
  scan_mode_for_later_candidate_run = whole_phrase_only
  internal_phrase_windows = false

not_processed_in_current_build:
  reverse direction / rev encoding
  order 4
  order 5
  phrase-internal fixed windows
  any production scorer output
  any candidate scan / P2-P3 long matrix
```

Deferred asset options to revisit after this full `fwd` order-2/order-3
provenance gate:

```text
option A: rev / normal+strict / orders 2,3
  purpose = direction parity / reverse-evidence expansion
  prerequisite = fwd full asset build + merge/provenance pass

option B: fwd / normal+strict / order 4
  purpose = longer phrase evidence
  risk = larger phrase-token lengths and stronger length-bias effects
  prerequisite = interpretation of fwd orders 2,3 and explicit runtime sizing

option C: fwd / normal+strict / order 5
  purpose = even longer phrase evidence
  risk = sparse hits, stronger length bias, larger build/scan cost
  prerequisite = order-4 value shown or a focused reason to test order 5

option D: rev / orders 4,5
  purpose = full directional/long-order expansion
  prerequisite = separate review; not bundled with first full raw run

option E: fixed-window internal phrase scan
  purpose = length-normalised evidence experiment
  status = explicitly out of scope for this tranche
  prerequisite = separate scorer/index mode and bias review
```

Planning rule for these deferred options:

- do not start another full raw asset family by copying the current pattern
  blindly;
- use the optimized/resumable shard builder as the baseline;
- run a small representative profiling slice first;
- declare wallclock budget, stop condition, output root, log path, and merge
  strategy before launch;
- keep each option independently reviewable so partial data-taking does not
  masquerade as the full matrix.

Shard build restart:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_asset_shards_v1.py
launch_mode = visible PowerShell window with Tee-Object log
pid = 7824
asset_mode = full
sample_line_limit_per_order = None
shard_mode = one_source_file_per_shard
direction = fwd
cuts = normal, strict
orders = 2, 3
total_shards = 1118
total_source_bytes = 21,114,123,555
intended_wallclock_budget = 36h
stop_condition = all_shards_complete_or_first_clear_blocker
log = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/full_raw_asset_shards_20260530_130413.log
run_root = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/20260530T120414Z__phaseB_ngram_hamming_full_raw_asset_shards_v1
full_long_matrix_launch = false
```

Initial verification:

```text
python process found = true
log receiving progress = true
early progress = shard 12 / 1118 started
completed shard outputs are written per source file
```

Existing processed-asset clarification:

```text
checked_at = 2026-05-30
older_complete_processed_asset_set =
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1/20260514T044954Z__phaseB_filtered_ngram_index_v1
older_complete_asset_status = sample, not full
older_complete_asset_sample_line_limit_per_order = 25000
older_complete_asset_summary_input_rows_seen = 25000 per order

older_full_attempt =
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_index_v1/20260514T045150Z__phaseB_filtered_ngram_index_v1
older_full_attempt_status = incomplete
older_full_attempt_outputs = config.json and dictionary_manifest.json only

first_cell_full_asset =
  output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_first_cell_assets_v1/20260529T151604Z__phaseB_ngram_hamming_full_raw_first_cell_assets_v1
first_cell_full_asset_scope = normal/fwd/order-2 only
first_cell_full_required_matrix_available = false

canary_probe_assets =
  asset_mode = canary_probe
  builder_run_mode = sample
  sample_line_limit_per_order = 25000
  full_asset_available = false
```

Conclusion: normal/strict assets do already exist for sample/probe work, but
no existing completed asset set proves the required full no-cap matrix
(`fwd`, `normal`/`strict`, orders `2`/`3`). The shard build is therefore not a
duplicate of an already reviewed full data plane.
