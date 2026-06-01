# PhaseB N-Gram Hamming Exact No-Cap Microbatch Sizing Review Summary - 2026-05-29

Status: review-required
Pack subject: completed 6-cell microbatch sizing slice for `phaseB_ngram_hamming_exact_no_cap_microbatch_sizing_v1`

## Decision Needed

The approved microbatch sizing slice passed. It exercised:

```text
candidate_count = 1
chunks_per_candidate = 1
cut = normal
orders = 2, 3
profiles = P0, P1, P2
planned scan cells = 6
```

This run gives better sizing evidence than the previous first-scan block because it includes order-3 cells and all three approved profiles.

## Run Result

```text
status = pass
backend_impl = cpp_fast
python_fallback_allowed = false
claim_mode = hard_pair_candidate_comparability
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
completed_scans = 6 / 6
elapsed_seconds = 8.172
parity_row_count = 3
all_required_parity_passed = true
```

## Provenance Result

```text
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
controlled_damage_stream_required = false
candidate_full_texts_used_as_primary_scan_source = false
```

The run still does not claim controlled `20-50%` damage-ladder evidence.

## Per-Cell Timing Summary

```text
P0 order 2:  1,709,610 attempts, 0.099s, 0 hits
P0 order 3:  7,415,062 attempts, 0.432s, 0 hits
P1 order 2:  1,709,610 attempts, 0.110s, 2 hits
P1 order 3:  7,415,062 attempts, 0.495s, 0 hits
P2 order 2:  1,709,610 attempts, 0.110s, 2 hits
P2 order 3:  7,415,062 attempts, 0.489s, 0 hits
```

Attempt-weighted projection for the original 120-cell target:

```text
measured_attempts = 27,374,016
measured_scan_seconds = 1.735
measured_attempts_per_second = 15,774,970
full_pilot_target_attempts = 547,480,320
attempt_weighted_full_pilot_projected_seconds = 34.706
```

Important caveat: the projection is scan-time-only. The full runner also pays setup, provenance, output writing, and bounded parity costs. The microbatch total elapsed time was `8.172s`, while measured C++ scan time was `1.735s`.

## Parity Result

Bounded C++/Python parity ran before the microbatch scan and again for the natural zero-hit row found during scanning:

```text
positive_control_phrase_index_row: pass
selected_real_candidate_chunk: pass
natural_zero_hit_or_low_hit_row: pass
```

## Review Questions

1. Is the microbatch enough to approve the original 120-cell pilot as a declared logged run?
2. If approved, what wallclock budget should be declared for the 120-cell pilot? A conservative budget should include scan projection plus setup/parity/output margin.
3. Should the 120-cell pilot remain interactive, or should it be launched in a separate PowerShell window with tee logging under the long-run rules?
4. Is backend acceleration still necessary before the 120-cell pilot, or can it wait until after the first full bounded pilot?

## Recommended Next Step

Approve one logged 120-cell pilot only if the reviewer accepts the scan-time projection and a conservative declared budget.

Suggested budget:

```text
intended wallclock budget = 10 minutes
stop condition = stop if completed cell timings project > 15 minutes after the first 12 cells
```

If reviewer prefers another microbatch first, run a 2-candidate x 1-chunk slice before the 120-cell pilot.
