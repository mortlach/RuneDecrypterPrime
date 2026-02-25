# Span-Hamming Scorer (No-WLI)

Audience: Hands-on / Expert  
Outcome: Understand how `span_hamming` computes deterministic, length-aware word-likeness from a flat rune stream.

## What it is
- `span_hamming` scores plaintext without WLI by matching spans against dictionary words with bounded Hamming distance.
- It is separate from the existing WLI Hamming scorer (`scoring/hamming/*`).
- It uses weighted non-overlapping interval selection to avoid double-counting overlapping hits.

## Lexical source
- Reuses `load_raw1grams_wordlists(...)` from:
  - `src/rune_decrypter_prime/scoring/hamming/loader.py`
- Dictionary entries are deduplicated and sorted deterministically per length.

## Core scoring model
For each start `i` and length `L`:
1. Find best dictionary match distance `d(i,L)` (capped at `max_hd + 1`).
2. Convert to quality:
   - `q(i,L) = 1 - min(d(i,L), max_hd+1) / (max_hd+1)` in `[0,1]`
3. Compute interval weight:
   - `wgt(i,L) = q(i,L) * L`

Only intervals with `q >= min_quality_threshold` are kept.

## Overlap resolution
- Candidate intervals overlap heavily.
- `span_hamming` selects a non-overlapping set maximizing total `sum(wgt)` using weighted interval scheduling.
- Deterministic tie-break:
1. higher total weight
2. higher covered chars
3. earlier finishing canonical schedule key `(end, start, -length)` lexicographically

## Reported metrics
Given selected intervals:
- `coverage = covered_chars / N`
- `quality = sum_w / covered_chars` (safe-divide)
- `span_raw = sum_w / N`

Identity:
- `span_raw = coverage * quality`

Per-length arrays (fixed shape):
- `length_bins = [len_min..len_max]`
- `span_raw_by_len`
- `coverage_by_len`
- `quality_by_len`
- `selected_intervals_by_len`
- `chars_covered_by_len`

## Runtime guards
- Split-index prefilter reduces exact Hamming checks.
- Caps:
  - `max_candidates_per_window`
  - `max_intervals_considered_per_start`
- All truncation paths are deterministic.

## Notes
- No scorer/pipeline integration is included in this phase.
- This module is intended for controlled evaluation and later normalization/calibration work.

