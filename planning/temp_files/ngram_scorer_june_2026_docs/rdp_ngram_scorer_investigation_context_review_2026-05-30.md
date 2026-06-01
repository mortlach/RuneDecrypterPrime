# RDP N-Gram Scorer Investigation Context Review - 2026-05-30

Status: discussion prep

Scope: synthesis of the June research reports, the implementation brief, the
no-WLI planning surfaces, and the currently observed n-gram Hamming scorer
progress.

This note is intentionally not a production-change proposal. It is a context
and review document to support a detailed discussion about the proposed concrete
direction for the no-WLI n-gram scoring layer.

## Source Documents Read

Research and implementation-plan documents:

- `planning/temp_files/ngram_scorer_june_2026_docs/deep-research-report(2).md`
- `planning/temp_files/ngram_scorer_june_2026_docs/deep-research-report(3).md`
- `planning/temp_files/ngram_scorer_june_2026_docs/deep-research-report(4).md`
- `planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_implementation_brief_v0_1.md`

No-WLI planning/status documents:

- `planning/projects/no_wli/00_CURRENT_STATE.md`
- `planning/projects/no_wli/04_ACTIVE_RUNBOOK.md`
- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_plan_2026-05-14.md`
- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_coherence_scorer_v1_implementation_start_plan_2026-05-14.md`
- `planning/projects/no_wli/20_active_plans/phaseB_ngram_hamming_exact_no_cap_pilot_design_plan_2026-05-29.md`
- `planning/working/no_wli_current_status_handoff_data_pause_20260514.md`
- `planning/temp_files/ngram_scorer_branch_status.txt`
- `planning/temp_files/phaseB_ngram_hamming_coherence_scorer_v1_approved_spec.md`
- `planning/temp_files/temp_new_ngram_scorer.txt`

Key output readouts checked:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_exact_no_cap_full_pilot_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_exact_no_cap_full_pilot_interpretation_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bounded_expansion_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_balanced_readout_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_balanced_readout_interpretation_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_sample_index_all_candidate_matrix_interpretation_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_nonproduction_scorer_design_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_nonproduction_scorer_combination_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_canary_probe_v1/readout.md`

Live/progress surfaces checked:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/full_raw_asset_shards_20260530_130413.log`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/full_raw_asset_shards_optimized_resume_20260530_164433.log`

## Research Consensus

The three research reports and the implementation brief agree on the core
model:

- Use exact word-structured phrase Hamming as the v1 semantic scorer.
- Keep phrase identity tied to structured `word_token_ids`, not to flattened
  joined token sequences.
- Use `rune_token_ids` for scanning/compatibility, not as the canonical phrase
  identity.
- Treat the scorer as second-stage positive support after word/span-Hamming.
- Do not penalize absence of phrase hits in v1.
- Keep normal and strict assets separate.
- Do not use count/log-count weighting as score-bearing evidence in v1.
- Do not use edit distance, skip/gapped phrase evidence, noisy-channel scoring,
  n-gram LM likelihoods, or WFST machinery as score-bearing v1 paths.
- Do not use raw hit volume as the central score.
- Use exact all-hit accounting: no caps, no top-k, no silent fallback, no silent
  narrowing.

The refined June plan specifically recommends a small support-tuple scorer:

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

with lexicographic comparison, cluster counts as score-bearing units, and raw
hit counts kept diagnostic.

The key modeling warning from the reports is that high hit volume can recreate
the earlier repeated-structure failure mode. The reports repeatedly point to the
old `repeated_3gram_rate` lesson: apparent rescues are not enough if the feature
also produces breaks or inflates on periodic/local repeated structure.

## Proposed First-Run Profile Ladder

The implementation brief's frozen ladder is:

Score-bearing:

| Profile | Orders | Cut | Min phrase token length | Max total HD | Max word HD | Role |
|---|---:|---|---:|---:|---:|---|
| `N3C` | 3 | normal | 8 | 2 | 1 | main normal coverage |
| `S3W` | 3 | strict | 7 | 2 | 2 | strict trigram confirmer |
| `N4L` | 4 | normal | 10 | 3 | 2 | longer normal confirmation |
| `S34C` | 3,4 | strict | 8 | 2 | 1 | highest precision confirmation |

Diagnostic:

| Profile | Orders | Cut | Min phrase token length | Max total HD | Max word HD | Role |
|---|---:|---|---:|---:|---:|---|
| `B2R` | 2 | normal, strict | 7 | 2 | 2 | weak 2-gram telemetry |
| `N3S_diag` | 3 | normal | 7 | 2 | 2 | softer normal trigram diagnostic |
| `F5D` | 5 | normal, strict | 12 | 3 | 2 | sparse 5-gram diagnostic |

This is important because the research plan's ideal center of gravity is
3-grams and 4-grams, while the empirical pilot work so far has found the first
clear signal in normal/order-2/P1-or-P2 style evidence.

## Actual Implementation Progress

The repo is substantially beyond planning.

Completed or implemented:

- Slice 0 damage-source audit passed.
- Slice 1 asset validation passed.
- Slice 2 phrase-index builder passed with `196680` phrase entries.
- Python reference matcher exists in `src/rune_decrypter_prime/scoring/ngram_hamming/`.
- C++ fast backend exists and builds locally.
- C++ extension import passed for `_ngram_hamming_fast`.
- Synthetic reference/tool/fast backend tests passed:
  - `41 passed in 54.58s`
- C++ Slice 2 tiny real-index smoke passed:
  - `backend_impl = cpp_fast`
  - `python_fallback_allowed = false`
  - `parity_match = true`
  - `elapsed_seconds = 0.957`
  - positive-control fast hits = `2`
  - real-candidate fast hits = `0`
- Full bounded n-gram Hamming verification passed:
  - `44 passed in 56.71s`

Current implemented scripts include:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/validate_phaseB_ngram_hamming_assets_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_phrase_index_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_reference_smoke_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_fast_real_index_smoke_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_exact_no_cap_pilot_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_exact_no_cap_full_pilot_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bounded_expansion_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_balanced_readout_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/design_phaseB_ngram_hamming_nonproduction_scorer_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/simulate_phaseB_ngram_hamming_nonproduction_scorer_combination_v1.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_asset_shards_v1.py`

## Empirical Evidence So Far

### Exact Joined N-Gram Scanner

The exact filtered n-gram hard-pair report is already closed as a valid
negative for exact joined phrase scanning on damaged no-WLI streams.

Observed in current-state note:

```text
N4_normal_2_4_combined_core:
  truth preference = 2 / 2594
  rescues = 0
  breaks = 0
  net = 0

N6_normal_plus_strict_support:
  truth preference = 2 / 2594
  rescues = 0
  breaks = 0
  net = 0
```

Interpretation: exact joined phrase scanning is too brittle for this damaged
no-WLI setting. This supports the move to word-structured phrase Hamming.

### Exact No-Cap Full Pilot

Full pilot result:

```text
status = pass
claim_mode = hard_pair_candidate_comparability
backend = cpp_fast
python_fallback_allowed = false
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
selected_candidates = 10
completed_scans = 120
elapsed_seconds = 43.963
```

Interpretation result:

```text
total_hits = 14
candidates_with_hits = 3 / 10
candidates_with_zero_hits = 7 / 10
productive_profile_orders = P1 normal order 2, P2 normal order 2
```

Observation: in this small sample, only normal/order-2/P1-P2 produced hits.
P0 and order-3 were zero-hit controls.

### Bounded Expansion v1

Bounded expansion result:

```text
status = pass
claim_mode = hard_pair_candidate_comparability
backend = cpp_fast
python_fallback_allowed = false
selected_candidates = 100
completed_scans = 600
elapsed_seconds = 75.368
total_hits = 188
candidates_with_hits = 39 / 100
candidates_with_zero_hits = 61 / 100
P0 hits = 0
P1 hits = 95
P2 hits = 93
```

Observation: the productive shape remained normal/order-2/P1-P2.

### Balanced Readout v1

Balanced readout result:

```text
status = pass
claim_mode = hard_pair_candidate_comparability
backend = cpp_fast
python_fallback_allowed = false
selected_candidates = 118
completed_scans = 708
elapsed_seconds = 90.447
total_hits = 328
candidates_with_hits = 44 / 118
candidates_with_zero_hits = 74 / 118
```

Balanced interpretation:

```text
known_better mean hits per candidate = 4.000
known_worse mean hits per candidate = 0.211
high_truth_stable_fill mean hits per candidate = 7.750
bad_control mean hits per candidate = 0.250
panel_rescue_known_better hits = 0
P1/P2 same-hit-count candidates = 117 / 118
P0 positive chunk rows = 1
```

Interpretation:

- There is clear separation between known-better and known-worse strata in this
  bounded comparability readout.
- The signal is not rescue-proven, because panel-rescue known-better candidates
  had zero hits.
- P1 and P2 are almost redundant in this slice.
- P0 should stay an audit/control field.
- This evidence is not a controlled 20-50% damage-ladder result.

### Sample-Index All-Candidate Matrix

Sample-index all-candidate matrix:

```text
status = pass
dataset_status = sample_index_confirmed
selected_candidates = 604
completed_scans = 3624
total_hits = 1051
candidates_with_hits = 243
candidates_with_zero_hits = 361
elapsed_seconds = 386.052
```

Interpretation:

```text
candidates = 604
hard-pair rows evaluated = 2594
source total hits = 1051
source candidates with hits = 243
current known-better rate = 0.767926
P2 raw known-better rate = 0.220509
current+log1p(P2) known-better rate = 0.695451
gated current+log1p(P2) known-better rate = 0.238242
panel-rescue P2-hit candidates = 0 / 20
```

Interpretation:

- Sample-index P2 evidence by itself is not a full hard-pair scorer.
- Adding it naively to the current score made the known-better rate worse than
  current alone in this sample-index interpretation.
- This reinforces the research warning against direct additive fusion.
- It also reinforces the need for support-tuple or tightly gated use rather than
  raw weighted score blending.

### Non-Production Scorer Design/Combination

Non-production scorer design says:

```text
primary signal = normal_order2_P2_raw_weighted_hits
P1/P2 same-hit-count candidates = 117 / 118
P0 audit flags = 1
paired comparisons available = 2
paired comparisons preferring known-better = 1
panel-rescue candidates with primary hits = 0 / 20
```

Combination readout:

```text
current known-better minus known-worse = 0.157779
P2 known-better minus known-worse = 19.907640
current+log1p(P2) known-better minus known-worse = 1.879158
current high-truth minus bad-control = 0.241644
P2 high-truth minus bad-control = 39.070103
current+log1p(P2) high-truth minus bad-control = 3.800268
panel-rescue candidates with P2 hits = 0 / 20
```

Interpretation:

- P2 is a strong separability feature on selected candidate strata.
- It is not yet a pairwise rescue scorer.
- It should remain non-production/report-only.
- Any combination with current score should be designed as bounded support or
  tie-break logic, not as an unbounded additive score.

## Current Full Raw Asset Build Status

The current full raw asset data plane is not complete yet.

Planned current full raw shard-build scope:

```text
asset_mode = full
sample_line_limit_per_order = None
direction = fwd only
cuts = normal, strict
orders = 2, 3
shard_mode = one_source_file_per_shard
scan_mode_for_later_candidate_run = whole_phrase_only
internal_phrase_windows = false
full_long_matrix_launch = false
```

Important history:

- The earlier monolithic full build failed/interrupted before completion.
- It held aggregate dictionaries until whole-order completion and emitted no
  completed asset files.
- The build strategy was replaced with a resumable shard builder.
- The shard builder emits independently complete shard outputs and
  `shard_manifest.json` files.
- An optimized scan path was added:
  - parse each raw row once;
  - compute normal/strict eligibility once;
  - encode once per kept phrase/direction;
  - write the encoded phrase into all applicable cut buckets;
  - skip already completed pass shards.

Live check on 2026-05-30 around 21:22 local time:

```text
python process = running
python pid = 7348
current log = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/full_raw_asset_shards_optimized_resume_20260530_164433.log
completed shard manifests found = 478
pass shard manifests found = 478
latest observed active order = 3
latest observed shard in log = order 3, shard 279, source "3 3 6.txt"
latest observed total elapsed in log = about 4h35m
latest observed ETA by completed bytes = about 18h14m
```

Interpretation:

- The build is currently in 3-gram parsing/building, consistent with the live
  project note that 3-gram data is being parsed.
- The current data plane is recoverable and partially extractable.
- Full fwd order-2/order-3 normal/strict raw assets are not yet complete.
- No full long matrix should start until the build is complete, summarized, and
  reviewed.

## The Main Tension For Discussion

There is a productive tension between the research ideal and the observed first
signal.

Research plan:

- central score-bearing evidence should be 3-gram and 4-gram clustered phrase
  support;
- 2-grams should be weak/diagnostic because they are more inflation-prone;
- strict 3/4 and normal 4 should carry confirmation;
- final v1 should use cluster tuples, not raw hit counts.

Empirical preparation so far:

- exact joined phrase scanning is a valid negative;
- word-structured Hamming implementation and C++ parity are in good shape;
- bounded no-cap pilots found useful signal first in normal/order-2/P1/P2;
- order-3 was zero-hit in the early small pilot;
- full order-3 raw assets are only now being built and are not yet available for
  full/provenance-grade interpretation;
- sample-index all-candidate interpretation warns that raw P2 support is not a
  standalone pairwise scorer and should not be added directly to current score.

This means the next design discussion should not simply ask "2-grams or
3-grams?". It should ask how to bridge from the observed order-2 signal toward
the research-recommended phrase-coherence scorer without either:

- overpromoting weak/short evidence; or
- ignoring the only positive empirical signal seen so far.

## Current Non-Production Reading

The safest current read is:

1. The scorer infrastructure is substantially prepared.
2. The full raw asset plane is the current bottleneck.
3. The first evidence supports order-2 normal P1/P2 as a candidate-comparability
   signal, not as a production ranking rule.
4. P1/P2 are probably redundant in the current order-2 bounded readout, but that
   may change with full assets or other orders.
5. P0 exact hits should stay audit/control.
6. Order-3 and order-4 should not be dismissed, because current full order-3
   evidence is not complete and order-4 has not been run in this tranche.
7. The June tuple/cluster design remains the right eventual shape, but the
   immediate bridge may need a smaller non-production scorer slice around the
   empirically active order-2 signal.
8. Any production change, direct additive blend, controlled damage-ladder claim,
   strict/order-4 expansion, P3/P4 expansion, or broad full hard-pair report
   remains blocked pending review and provenance.

## Recommended Discussion Frame

Recommended framing for the comprehensive discussion:

1. Separate infrastructure readiness from scientific readiness.
2. Separate sample/probe evidence from full raw/provenance evidence.
3. Treat order-2 evidence as a lead, not as a promotion.
4. Treat 3-gram parsing/full raw asset completion as the next necessary evidence
   gate before judging the research tuple design.
5. Decide whether the next scorer slice should be:
   - an order-2 non-production support feature;
   - a cluster-tuple prototype over order 2 and 3 only;
   - a wait-for-full-assets summary/provenance pack before any scorer-design
     movement;
   - or a focused diagnostic explaining why panel-rescue candidates have zero
     P2 hits.

## Hard Boundaries To Preserve

Do not treat any current result as:

- a production scorer result;
- a controlled 20-50% damage-ladder result;
- evidence for live ranking changes;
- evidence that direct additive fusion is safe;
- evidence that order 3/4 are useless;
- evidence that full raw assets are already complete.

Do preserve:

- no CLI args in helper automation;
- hardcoded config switches;
- repo-relative paths/logs;
- visible/logged long runs;
- completed-versus-total progress;
- resumable shard outputs;
- exact all-hit accounting;
- no silent Python/C++ fallback;
- no hit caps or top-k scoring;
- strict/normal separation;
- FWD/REV non-mixing;
- provenance and manifests before interpretation.

