# PhaseB N-Gram Hamming Balanced Readout v1 Review Summary - 2026-05-29

Status: review-ready
Pack subject: balanced bounded readout after bounded expansion v1

## Scope

This run keeps the productive scan shape from bounded expansion v1, but replaces mostly deterministic stable-fill selection with an explicit balanced candidate set.

```text
claim_mode = hard_pair_candidate_comparability
cut = normal
order = 2
profiles = P0, P1, P2
target strata = 6
target candidates per stratum = 20
selected candidates = 118
chunks_per_candidate = 2
scan_cells = 708
backend_impl = cpp_fast
python_fallback_allowed = false
controlled_damage_ladder_claim = false
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
```

One stratum had an explicit shortfall:

```text
panel_break_known_worse selected = 18 / 20
```

No silent backfill was used.

## Run Result

```text
status = pass
completed_scans = 708 / 708
elapsed_seconds = 90.447
measured_attempts = 1,210,403,880
measured_scan_seconds = 79.948
measured_attempts_per_second = 15,139,965
```

The run was launched in a separate PowerShell process with unbuffered stdout and tee logging:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_balanced_readout_v1/run_log.txt
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

## Hit Readout

```text
total_hits = 328
candidates_with_hits = 44 / 118
candidates_with_zero_hits = 74 / 118
```

By profile:

```text
P0_exact_short = 1 hit
P1_word_analogue_len7_hd2 = 164 hits
P2_conservative_len8_hd2 = 163 hits
```

By stratum:

```text
known_better_pair_candidate = 160 hits
high_truth_stable_fill = 155 hits
bad_control_candidate = 5 hits
known_worse_pair_candidate = 4 hits
panel_break_known_worse = 4 hits
panel_rescue_known_better = 0 hits
```

By role:

```text
known_better = 160 hits
known_worse = 8 hits
no recorded pair role = 160 hits
```

## Guarded Interpretation

Allowed interpretation:

```text
normal/order-2/P1/P2 strongly separates known-better/high-truth rows from known-worse/bad-control rows in this bounded readout
P1 and P2 remain nearly identical in aggregate hit count
P0 remains mostly a zero-hit control, with one exact hit in the balanced readout
panel_rescue_known_better produced zero hits in this selected slice, which needs follow-up before making rescue claims
```

Forbidden interpretation:

```text
do not claim production ranking improvement
do not claim rescue performance
do not claim controlled 20-50% damage-ladder evidence
do not call this a full hard-pair report
```

## Recommended Next Step

Create a focused comparison/decision pack from this output before scanning wider:

```text
compare hit-rate and weighted-hit separation:
  known_better vs known_worse
  high_truth_stable_fill vs bad_control
  panel_rescue_known_better vs panel_break_known_worse

check whether P1 and P2 are redundant enough to keep one primary profile
inspect the single P0 exact hit
inspect why panel_rescue_known_better is zero despite being known-better
```

Still defer:

```text
strict
order 4
P3/P4
broad pilot
full hard-pair report
production scorer changes
controlled damage-ladder language
```
