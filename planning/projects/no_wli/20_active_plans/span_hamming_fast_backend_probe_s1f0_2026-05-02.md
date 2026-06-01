# S1f0 Span-Hamming Fast Backend Probe

Date: 2026-05-02
Status: implementation probe
Runtime status: no solver runtime change

## Purpose

Before the full S1f span-Hamming calibration, build a fast optional backend that
matches the current Python span-Hamming backend.

The goal is not to design a new scorer. The goal is to make the full
calibration practical and to avoid spending hours measuring Python loop
overhead.

## Current Method Being Replaced For Calibration

The active span-Hamming path is:

```text
raw1grams CSV dictionary
-> load_raw1grams_wordlists
-> Python LengthSplitIndex by span length
-> slice-bucket candidate lookup
-> capped candidate IDs
-> Python limited Hamming distance
-> best interval per start/length
-> per-start interval cap
-> non-overlapping interval selection
-> span_raw / coverage / quality stats
```

This is not the older C++ WLI Hamming backend.

## Fast Backend Contract

The fast backend must match `SpanHammingBackend` for:

```text
SpanHammingConfig fields
span_raw
coverage
quality
n_chars
chars_covered
n_intervals_selected
length_bins
span_raw_by_len
coverage_by_len
quality_by_len
selected_intervals_by_len
chars_covered_by_len
n_windows_total
n_windows_scored
n_candidates_considered
n_candidates_pruned_cap
selected_intervals when debug_return_intervals=True
```

It may expose raw pre-selection intervals for calibration, but those must be
labelled separately from selected intervals.

## Implementation Files

```text
src/rune_decrypter_prime/scoring/span_hamming/FastSpanHamming.h
src/rune_decrypter_prime/scoring/span_hamming/fast_bindings.cpp
src/rune_decrypter_prime/scoring/span_hamming/setup_span_hamming_fast.py
src/rune_decrypter_prime/scoring/span_hamming/fast_backend.py
tests/scoring/span_hamming/test_fast_span_hamming_backend.py
```

## Build Rule

The extension is optional and explicitly built with:

```text
python src/rune_decrypter_prime/scoring/span_hamming/setup_span_hamming_fast.py
```

No CLI arguments are added to repo automation. The build script uses hardcoded
defaults, matching the local agent rule.

## Decision Rule

Advance to S1f full calibration if:

```text
the extension builds
focused parity tests pass
small benchmark shows the fast backend is not slower than Python
raw/selected interval meanings are kept separate
```

Hold if:

```text
parity fails
cap-pressure counts differ
selected interval tie-breaking differs
the extension cannot be built cleanly
```

## Stage 2 Status

Stage 2 remains on hold. This probe only supports the S1f calibration run.

## Completed Probe Result

Build:

```text
py -3.11 src/rune_decrypter_prime/scoring/span_hamming/setup_span_hamming_fast.py
```

Focused tests:

```text
py -3.11 -m pytest tests/scoring/span_hamming/test_span_hamming_backend.py tests/scoring/span_hamming/test_fast_span_hamming_backend.py
```

Result:

```text
20 passed
```

S1 token-sample probe:

```text
py -3.11 tools/benchmarks/periodic_sub_trans/no_wli/analysis/benchmark_fast_span_hamming_probe_v1.py
```

Output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_fast_backend_probe_v1/
```

Result:

```text
token hashes tested: 20
config count: 2
result rows: 40
parity failed rows: 0
mean speedup: 3.714x
median speedup: 3.687x
```

Conclusion:

```text
The optional fast backend is acceptable for S1f calibration support, provided
the calibration script continues to keep Python parity checks available.
```

## Speed-Tuned Backend Result

After the first probe, the fast backend was speed-tuned:

```text
packed integer split-bucket keys where possible
stamp-array candidate union instead of unordered_set
direct continuous length-bin indexing
stronger C++ optimization and link-time optimization flags
```

Small probe after tuning:

```text
result rows: 40
parity failed rows: 0
mean speedup: 8.833x
```

Full S1 token/config parity sweep:

```text
token hashes: 604
configs: 9
result rows: 5436
parity failed rows: 0
elapsed seconds: 3065.98
mean speedup: 12.300x
median speedup: 11.848x
min speedup: 4.806x
max speedup: 17.267x
```

Sweep output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fast_span_hamming_parity_sweep_v1/
```

Config-level result:

```text
raw_selected_len3_14_hd2_cap256__s1b_default:
  mean speedup 11.724x

raw_selected_len3_14_hd0_exact:
  mean speedup 6.210x

raw_selected_len3_14_hd1:
  mean speedup 11.147x

raw_selected_len4_14_hd1:
  mean speedup 11.383x

raw_selected_len5_8_hd2_fixture_like:
  mean speedup 14.917x

raw_selected_len6_14_hd2_longer:
  mean speedup 14.754x

raw_selected_len3_14_hd2_cap512:
  mean speedup 14.159x

raw_selected_len3_14_hd2_cap1024:
  mean speedup 15.810x

raw_all_len3_14_hd2_cap256:
  mean speedup 10.594x
```

Review status:

```text
Ready for review as an S1f support backend. Still report-only; no solver
runtime scorer path changed.
```
