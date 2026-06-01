# PhaseB N-Gram Hamming Bounded Expansion v1 Review Summary - 2026-05-29

Status: review-ready
Pack subject: bounded 100-candidate expansion after exact no-cap pilot gate closure

## Scope

This run intentionally speeds up after the exact no-cap pilot gate closed, while keeping claim boundaries disciplined.

```text
claim_mode = hard_pair_candidate_comparability
cut = normal
order = 2
profiles = P0, P1, P2
candidates = 100
chunks_per_candidate = 2
scan_cells = 600
backend_impl = cpp_fast
python_fallback_allowed = false
controlled_damage_ladder_claim = false
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
```

## Run Result

```text
status = pass
completed_scans = 600 / 600
elapsed_seconds = 75.368
measured_attempts = 1,025,766,000
measured_scan_seconds = 65.044
measured_attempts_per_second = 15,770,456
```

The run was launched in a separate PowerShell process with unbuffered stdout and tee logging:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bounded_expansion_v1/run_log.txt
```

## Provenance / Backend

```text
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
controlled_damage_stream_required = false
candidate_full_texts_used_as_primary_scan_source = false
```

## Parity

Bounded parity passed with four rows:

```text
positive_control_phrase_index_row: pass
selected_real_candidate_chunk P1 normal order 2: pass
p2_order2_real_nonzero_hit_chunk: pass
natural_zero_hit_or_low_hit_row: pass
```

The new P2 non-zero-hit parity case covers the productive shape that mattered in the previous full pilot.

## Hit Readout

```text
total_hits = 188
candidates_with_hits = 39 / 100
candidates_with_zero_hits = 61 / 100
```

By profile:

```text
P0_exact_short = 0 hits
P1_word_analogue_len7_hd2 = 95 hits
P2_conservative_len8_hd2 = 93 hits
```

By stratum:

```text
current_scorer_correct_good_candidate = 6 hits
stable_fill = 182 hits
all other selected strata = 0 hits
```

By role:

```text
known_better = 6 hits
known_worse = 0 hits
no recorded pair role = 182 hits
```

## Interpretation Guardrails

Allowed interpretation:

```text
normal/order-2/P1/P2 continues to be the productive shape
P0 exact remains a useful zero-hit control in this sample
hit signal is no longer vanishingly sparse at 100 candidates
hits concentrate in high-truth stable-fill candidates and one known-better row
```

Forbidden interpretation:

```text
do not claim ranking improvement
do not claim rescue performance
do not claim controlled 20-50% damage-ladder evidence
do not call this representative of the full hard-pair set
```

## Important Caveat

The 100-candidate selection is still not a balanced stratified evaluation. After the first fixed strata are selected, most rows come from deterministic `stable_fill`. That means the high hit count in `stable_fill` is useful signal, but it is not yet a fair hard-pair effectiveness estimate.

## Recommended Next Step

Move to a balanced bounded readout, not acceleration yet:

```text
normal/order-2/P1/P2 primary
P0 retained as control
select a balanced candidate set across:
  known_better
  known_worse
  current-scorer misrank/rescue rows
  panel rescue rows
  panel break rows
  bad controls
  high-truth stable-fill rows
```

The next output should explicitly compare hit rates and weighted hit sums between useful and bad/control strata. Keep claim mode as `hard_pair_candidate_comparability`.
