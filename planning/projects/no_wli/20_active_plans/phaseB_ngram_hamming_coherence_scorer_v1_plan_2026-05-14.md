# PhaseB N-Gram Hamming Coherence Scorer v1 Plan - 2026-05-14

Status: active
Work status: fast_real_index_smoke_review_ready
Project: no_wli
Owner: agent
Last updated: 2026-05-29
Short name: ngram_hamming_coherence_v1
Supersedes:
- planning/projects/no_wli/20_active_plans/phaseB_filtered_ngram_hard_pair_report_v1_plan_2026-05-14.md
- planning/temp_files/phaseB_ngram_hamming_coherence_scorer_v1_approved_spec.md
Source-of-truth parents:
- planning/temp_files/phaseB_ngram_hamming_coherence_scorer_v1_approved_spec.md
- output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_filtered_ngram_hard_pair_report_v1/readout.md
- output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1/readout.md
- output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1/readout.md

## Purpose

Build the approved robust no-WLI phrase/order evidence layer for damaged
candidate text.

The scorer asks:

```text
After word-Hamming has found local damaged-word evidence, do those damaged
word-like regions line up into plausible ordered filtered n-gram phrases?
```

This is a second-stage coherence scorer. It does not replace word-Hamming and it
does not change production ranking defaults in v1.

The intended stack is:

1. word-Hamming scorer
2. n-gram Hamming coherence scorer
3. later joint scorer with word-Hamming, n-gram coherence, and current
   character/language score

## Why This Supersedes Exact Filtered N-Gram v1

The exact filtered n-gram report completed on 2026-05-14 using sample-mode
assets and showed that exact joined phrase scanning is too brittle for the
damaged no-WLI hard-pair set:

- hard pairs: `2594`
- FWD sample filtered n-gram assets
- `N4_normal_2_4_combined_core`: truth preference `2 / 2594`, rescues `0`,
  breaks `0`, net `0`
- `N6_normal_plus_strict_support`: truth preference `2 / 2594`, rescues `0`,
  breaks `0`, net `0`
- `N10_span_len7_support_plus_ngram_core` matched the span-Hamming carry-forward
  result rather than adding useful exact n-gram support:
  truth preference `2016 / 2594`, rescues `286`, breaks `240`, net `+46`

The exact scanner answered its narrow question. The next live question is not
more exact joined phrase scanning; it is word-structured phrase Hamming.

## Scope

In scope:

- FWD no-WLI candidates only
- filtered strict and normal n-gram assets
- core orders `2`, `3`, and `4`
- diagnostic/stress order `5`
- word-structured Hamming phrase scoring
- damage levels `20%`, `30%`, `40%`, and `50%`
- two `500`-token chunks per candidate where available
- hard-pair rescue/break reporting
- comparison against current scorer, span/word-Hamming rows, proxy coherence,
  and exact filtered n-gram v1
- independent C++ backend
- Python reference implementation for tiny tests
- deterministic manifests, failure manifests, and tests before full reporting

Out of scope:

- changing production default ranking weights
- mixing FWD and REV in one calibration
- WLI scoring
- edit-distance matching with insertions/deletions
- fitted weights on the hard-pair set
- top-k scoring or hit caps
- silent fallback, silent narrowing, or silent asset/profile switching

## Non-Negotiable Contract

- Use `rune_token_ids` for scanning.
- Do not use `rune_key_hex`; it contains separator material that no-WLI
  candidates do not contain.
- FWD and REV must never be combined silently. v1 is FWD only.
- The scorer must count all eligible phrase hits exactly for a requested fixed
  profile or fail loudly with a failure manifest.
- Debug examples may be bounded, but examples must never feed score values.
- No hit caps are allowed: no top-k phrase scoring, max hits per offset, max
  hits per chunk, capped per-order score values, or silent match dropping.
- The C++ backend is independent. Existing span/word-Hamming backend code may be
  used as a guide for style and build pattern, not as a behavior constraint.
- All generated paths, manifests, logs, and readouts must use repo-relative
  paths where controllable.
- Repo helper/automation scripts must use hardcoded configuration constants, not
  CLI arguments.

## Approved Initial Profiles

| Profile | Role | Orders | Cuts | Min phrase token length | Max total HD | Max word HD | Damage levels |
|---|---|---|---|---:|---:|---:|---|
| `P0_exact_short` | baseline | `2,3,4` | normal, strict | `5` | `0` | `0` | `20,30,40,50` |
| `P1_word_analogue_len7_hd2` | core | `2,3,4` | normal, strict | `7` | `2` | `2` | `20,30,40,50` |
| `P2_conservative_len8_hd2` | core | `2,3,4` | normal, strict | `8` | `2` | `1` | `20,30,40,50` |
| `P3_longer_phrase_len10_hd3` | core diagnostic | `3,4` | normal, strict | `10` | `3` | `2` | `20,30,40,50` |
| `P4_strict_long_len10_hd2` | diagnostic/support | `3,4` | strict | `10` | `2` | `1` | `20,30,40,50` |
| `P5_order5_diagnostic_len12_hd3` | diagnostic only | `5` | normal, strict | `12` | `3` | `2` | `20,30,40,50` |

Profiles are fixed comparison profiles. v1 may report profile performance, but
must not tune profile parameters on the hard-pair set and report the tuned result
as independent evidence.

## Phrase-Hit Rule

A valid phrase hit exists only when:

1. adjacent fixed-length candidate spans match the phrase word lengths;
2. the phrase word-token sequence exists in the filtered n-gram phrase index;
3. every word is within the profile per-word HD threshold;
4. total phrase HD is within the profile total threshold;
5. phrase token length satisfies the profile length rule;
6. direction, cut, and order match the active profile.

Each phrase hit must be able to report:

```text
candidate_id
chunk_id
damage_level
profile_id
ngram_order
dictionary_cut
phrase_id
phrase_count
phrase_log_count
phrase_token_length
word_lengths
word_hds
total_phrase_hd
max_word_hd
mean_word_hd
normalised_phrase_hd
hit_start
hit_end
```

## Opportunity Count

Use the approved v1 denominator:

```text
opportunity_count = number of candidate start offsets at which at least one
phrase in the active phrase index could fit within the chunk length and profile
length limits
```

This is a placement opportunity count, not a word-hit count.

Required backend counters:

```text
candidate_tokens_scanned
candidate_start_offsets_considered
phrase_entries_considered
phrase_verification_attempts
phrase_verification_passes
phrase_hits
opportunity_count
```

## Feature Families

Core chunk features:

- `phrase_hit_count`
- `unique_phrase_hit_count`
- `binary_phrase_presence`
- `weighted_hit_sum`
- `max_phrase_weight`
- `mean_phrase_weight`
- `token_coverage`
- `opportunity_count`
- `hit_rate`
- `weighted_hit_rate`
- `unique_phrase_rate`
- `mean_total_phrase_hd`
- `min_total_phrase_hd`
- `mean_normalised_phrase_hd`
- `best_normalised_phrase_hd`

Candidate-level aggregation must report chunk values plus:

- `mean_chunk_value`
- `max_chunk_value`
- `min_chunk_value`
- `positive_chunk_count`
- `positive_chunk_fraction`

Primary v1 aggregation is `mean_chunk_value`; `max_chunk_value` and
`positive_chunk_fraction` are diagnostics.

Core weighting modes:

- `unweighted`
- `binary_presence`
- `log_count_weighted`

Diagnostic weighting modes:

- `max_count_weighted`
- `sum_count_weighted`

If assets are sample-mode, unweighted and binary features remain first-class and
count weighting must be labelled as sample-sensitive.

## Score Families

Report fixed transparent score families:

- `H0`: current scorer baseline
- `H1`: normal P1 order-specific, orders `2`, `3`, `4` separately
- `H2`: strict P1 order-specific, orders `2`, `3`, `4` separately
- `H3`: normal P1 combined, mean of order-normalised scores
- `H4`: normal P2 combined
- `H5`: strict P2 combined
- `H6`: normal P2 support plus separate strict confirmation diagnostic
- `H7`: long phrase support, P3/P4 orders `3` and `4`
- `H8`: word-Hamming analogue, P1 `phrase_total_token_length >= 7` and
  `total_phrase_hd <= 2`
- `H9`: low-damage support using P0 and P2
- `H10`: verified word-Hamming row plus n-gram coherence
- `H11`: verified S5 word-Hamming signal plus n-gram coherence
- `H12`: conservative support rule requiring both word-Hamming and n-gram
  coherence margins above fixed thresholds
- `H13`: 5-gram diagnostic, P5 only

Before coding, verify the exact current row names for the word-Hamming and S5
inputs from local files. The draft row names are not to be hard-coded until
verified.

## Required Implementation Targets

Planning target:

```text
planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md
```

Proposed code targets, pending repo inspection:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_assets_v1.py
tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_phrase_index_v1.py
tools/benchmarks/periodic_sub_trans/no_wli/analysis/reference_phaseB_ngram_hamming_matcher_v1.py
tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_pilot_v1.py
tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_hard_pair_report_v1.py
tests/tools/test_phaseB_ngram_hamming_coherence_v1.py
```

The exact C++ and pybind paths must be chosen only after repo inspection.

## Required Output Root

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_hard_pair_report_v1
```

Required output families:

- config and input manifests
- damage manifest
- n-gram asset manifest
- phrase index manifest
- backend manifest
- score definition manifest
- chunk and candidate feature CSVs
- debug examples JSONL, clearly labelled as examples only
- pairwise summary, margin sweep, score gaps, and correlations
- damage-level, order, cut, profile, phrase-length, and weighting summaries
- proxy, word-Hamming, and exact n-gram comparison files
- top rescues, breaks, false positives, and false negatives
- `readout.md`

## Acceptance Gates

Gate 1 - asset validation:

- `rune_token_ids` present
- FWD assets present
- strict and normal present
- orders `2`, `3`, and `4` present
- asset mode recorded
- duplicate handling recorded
- token values valid
- empty token sequences rejected

Gate 2 - Python reference tests:

- exact phrase hit
- one damaged word
- multiple damaged words
- minimum phrase length rejection
- total HD rejection
- per-word HD rejection
- duplicate phrase collapse
- FWD/REV separation
- `rune_key_hex` rejection
- debug example limits do not affect scores

Gate 3 - backend parity:

- independent C++ backend matches Python reference on small fixed examples.

Gate 4 - exact no-cap pilot:

```text
candidates: 10
chunks: 20
direction: FWD
cuts: normal
orders: 2, 3
profiles: P0, P1, P2
damage_levels: 20, 30, 40, 50
```

Pass conditions:

- non-zero phrase hits for at least one non-exact profile
- all eligible hits counted
- no scoring caps
- runtime recorded
- repeat run deterministic
- debug examples labelled as examples only

Gate 5 - expanded pilot:

- add strict
- add order `4`
- add P3 and P4
- confirm exact counting still completes
- confirm no profile silently changes

Gate 6 - full hard-pair report:

- run the full `604` candidate / `2594` pair report only after earlier gates
  pass.

Gate 7 - review before production weighting:

- no production ranking change before review.

## Runtime Guardrails

Do not start with the full hard-pair report.

If any pilot or report becomes a long-running investigation, follow the local
runtime rules:

- declare intended wallclock budget and stop condition before launch
- use the smallest independently complete canary that answers the next branch
  question
- consult retained runtime history before any multi-hour no-WLI runtime
- launch long runs in a separate PowerShell window
- tee stdout/stderr to a repo-relative log file
- emit completed-versus-total progress, elapsed time, and ETA where estimable
- verify all repo-relative output/log/catalog paths resolve under repo root and
  have valid parents before launch and before closeout

## Immediate Next Sequence

1. Inspect the local repo structure.
2. Identify the existing word/span-Hamming backend build pattern.
3. Identify filtered n-gram asset schema and actual asset file names.
4. Build asset validation.
5. Build phrase index builder.
6. Build tiny Python reference matcher.
7. Add reference tests.
8. Build independent C++ backend.
9. Add backend parity tests.
10. Run exact no-cap pilot.
11. Run expanded pilot.
12. Run full hard-pair report only after gates pass.

## Still Unverified Until Repo Inspection

Do not hard-code these from the approved spec:

- exact C++ backend paths
- pybind module name
- existing word-Hamming row names
- exact S5 row name
- current hard-pair input file names
- current n-gram asset file names
- actual filtered n-gram asset schema
- exact damage model config names
- test helper names
- build helper names

## Implementation Start Plan - 2026-05-14

The repo-intelligence start plan is now review-ready:

```text
planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_implementation_start_plan_2026-05-14.md
```

Review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_start_review_pack_2026-05-14.zip
```

Implementation remains gated on review of file placement, phrase identity,
pilot input source, and first test split. No scorer code has been changed by the
start-plan pass.

Review verdict:

- approved with amendments before coding
- amendments added to the start plan:
  - Slice 0 damage-source audit
  - canonical structured `word_token_ids`
  - explicit flat candidate versus word-structured phrase wording
  - no silent backend fallback
  - clarified opportunity metrics
  - deterministic deliberate pilot candidate selection

Implementation progress:

- Slice 0 damage-source audit completed and passed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_damage_source_audit_v1`
- Slice 1 asset validation completed and passed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_asset_validation_v1`
- Slice 2 phrase index completed and passed:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_phrase_index_v1`
  - phrase entries: `196680`
- Slice 3 Python reference matcher is implemented under:
  - `src/rune_decrypter_prime/scoring/ngram_hamming/`
- Initial Slice 4 tests are implemented under:
  - `tests/scoring/ngram_hamming/`
  - `tests/tools/`

Next implementation slice is independent C++ backend/parity or, if review
prefers more Python-only evidence first, a tiny explicit-Python pilot. Full
hard-pair reporting remains gated.

Pre-C++ amendment status:

- pack-level review passed with amendments
- code-level review was blocked because the first implementation pack omitted
  source/test contents
- amendments are implemented:
  - exact damaged-stream sharing is marked `unverified`
  - stream-fingerprint fields are frozen for later pilot proof
  - parser/token contract is frozen in the asset manifest
  - asset detail CSVs are emitted
  - profile eligibility summary is emitted
  - tiny bounded Python reference smoke passed
- replacement implementation review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_impl_review_pack_2026-05-15.zip`

Source-level review passed with pre-C++ amendments. Those amendments are now
implemented:

- profile direction is part of the reusable reference contract
- wrong-direction phrase entries are rejected by the profile filter
- `rune_lengths` and candidate tokens are strict
- builder invalid rows block core FWD index status
- duplicate count metadata is explicit
- amended tests pass

Updated pre-C++ contract review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_pre_cpp_contract_review_pack_2026-05-15.zip
```

C++ Slice 1 source is now implemented and the local optional extension build
passes after Microsoft C++ Build Tools became available. Import verification for
`_ngram_hamming_fast` passes, and the synthetic parity tests now execute instead
of skipping. No real-data backend loading, pilot, or report runner has started.

Build/parity verification on 2026-05-29:

```text
python src/rune_decrypter_prime/scoring/ngram_hamming/setup_ngram_hamming_fast.py
pass; copied _ngram_hamming_fast.cp311-win_amd64.pyd into src/rune_decrypter_prime/scoring/ngram_hamming/

python -m pytest tests/scoring/ngram_hamming/test_reference_ngram_hamming.py tests/tools/test_phaseB_ngram_hamming_slice0_slice1_v1.py tests/tools/test_phaseB_ngram_hamming_phrase_index_v1.py tests/tools/test_phaseB_ngram_hamming_reference_smoke_v1.py tests/scoring/ngram_hamming/test_fast_ngram_hamming_backend.py -q
41 passed in 54.58s
```

Review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_coherence_scorer_v1_cpp_slice1_source_review_pack_2026-05-15.zip
```

Current next gate:

- external/source review of the built C++ Slice 1 and C++ Slice 2 tiny
  real-index smoke behavior.

Do not start the full hard-pair report before the tiny real-index smoke and the
planned exact no-cap pilot gates.

## Fast Real-Index Smoke Update - 2026-05-29

C++ Slice 2 tiny real-index smoke is implemented:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_fast_real_index_smoke_v1.py`
- `tests/tools/test_phaseB_ngram_hamming_fast_real_index_smoke_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_fast_real_index_smoke_v1`

Result:

```text
backend_impl: cpp_fast
reference_backend_impl: python_reference
python_fallback_allowed: False
broad_pilot: False
loaded entries: 2000
elapsed seconds: 0.957
parity match: True
positive-control fast hits: 2
real-candidate fast hits: 0
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

- review is required before moving to the exact no-cap pilot or any broader
  real-data report.
