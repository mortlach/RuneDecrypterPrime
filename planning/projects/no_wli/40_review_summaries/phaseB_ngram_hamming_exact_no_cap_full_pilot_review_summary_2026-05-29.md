# PhaseB N-Gram Hamming Exact No-Cap Full Pilot Review Summary - 2026-05-29

Status: review-required
Pack subject: completed 120-cell full pilot for `phaseB_ngram_hamming_exact_no_cap_full_pilot_v1`

## Decision Needed

The approved full 120-cell pilot completed within the declared 10-minute guard.

This remains a bounded hard-pair candidate comparability pilot. It is not a broad pilot, not a full hard-pair report, and not a controlled `20-50%` damage ladder claim.

## Run Result

```text
status = pass
backend_impl = cpp_fast
python_fallback_allowed = false
claim_mode = hard_pair_candidate_comparability
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
selected_candidates = 10
completed_scans = 120 / 120
elapsed_seconds = 43.963
max_wallclock_seconds = 600.0
```

Early runtime guard:

```text
early_projection_check_cells = 12
early_projection_after_12_cells = 38.1 seconds
early_projection_stop_seconds = 600.0
```

## Provenance Result

```text
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
controlled_damage_stream_required = false
candidate_full_texts_used_as_primary_scan_source = false
```

The scan source is still the hard-pair manifest token path plus chunk manifest. `candidate_full_texts.jsonl.gz` is only a check source and matched selected token streams.

## Output Row Counts

```text
cell_timing_rows = 120
chunk_feature_rows = 120
candidate_feature_rows = 60
debug_examples_rows = bounded output only
parity_rows = 3
```

## Timing Summary

```text
measured_attempts = 547,480,320
measured_scan_seconds = 36.956
measured_attempts_per_second = 14,814,535
elapsed_seconds = 43.963
```

The total elapsed time includes setup, provenance, bounded parity, scan, and output writing. The measured scan time is lower than total elapsed because `cell_timing_rows.csv` records C++ scan-cell wallclock only.

## Hit Summary

```text
total hit_count across timing rows = 14
```

This is enough to prove exact no-cap scan outputs are populated, but it is not a scorer-effectiveness report.

## Parity Result

Bounded C++/Python parity passed:

```text
positive_control_phrase_index_row: pass
selected_real_candidate_chunk: pass
natural_zero_hit_or_low_hit_row: pass
```

## Review Questions

1. Is this sufficient to close the exact no-cap pilot gate?
2. Should the next step be a narrow feature/readout interpretation pack, or should acceleration/indexing happen first?
3. Are the current feature rows enough to compare candidate strata qualitatively without producing a full hard-pair report?
4. Should strict/order-4/P3/P4 remain deferred until after this output is interpreted?
5. Should any additional parity cases be added before expanding beyond this 10-candidate bounded pilot?

## Recommended Next Step

Create a narrow interpretation/review pack over the existing bounded pilot outputs only:

```text
allowed:
- summarize feature-row and candidate-row distributions
- preserve claim_mode = hard_pair_candidate_comparability
- compare selected strata qualitatively
- identify whether the no-cap scorer has enough signal to justify a next bounded expansion

still forbidden:
- broad pilot
- full hard-pair report
- production scorer changes
- controlled 20-50% damage ladder language
```
