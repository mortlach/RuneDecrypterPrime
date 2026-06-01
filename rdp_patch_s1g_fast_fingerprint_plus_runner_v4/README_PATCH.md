# RDP S1g fast raw span-Hamming fingerprint patch v4

This package is a drop-in source patch, not a generated result bundle.

## What this adds

1. A new C++/pybind analysis-only fast backend method:

```text
FastSpanHamming::fingerprint_raw_hamming_counts(...)
FastSpanHammingBackend.fingerprint_raw_hamming_counts(...)
```

2. Backend tests for the new fingerprint contract.

3. A new S1g runner:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_span_hamming_selected_dictionary_500_unit_fingerprint_v1.py
```

4. S1g runner tests for selected-only policy, HD policy, chunking, aggregation, summary flags, and pair rescue/break separation.

## Important policy choices

- Selected dictionaries only.
- No `_all` dictionary cuts.
- No `require_selected=False`.
- New fingerprint mode is separate from current scorer mode.
- Fingerprint scope is `raw_hamming_counts`.
- HD bins are `0..max(0, span_length - 1)`.
- No `hd == span_length` rows are valid.
- `max_candidates_per_window=0` means uncapped for fingerprint mode only.
- Existing `score(...)` behaviour is left unchanged.
- No runtime solver behaviour is changed.
- No Stage 2 gate is promoted.

## Files included

```text
src/rune_decrypter_prime/scoring/span_hamming/FastSpanHamming.h
src/rune_decrypter_prime/scoring/span_hamming/fast_bindings.cpp
src/rune_decrypter_prime/scoring/span_hamming/fast_backend.py
tests/scoring/span_hamming/test_fast_span_hamming_backend.py
tools/benchmarks/periodic_sub_trans/no_wli/analysis/scan_span_hamming_selected_dictionary_500_unit_fingerprint_v1.py
tests/tools/test_no_wli_span_hamming_selected_dictionary_500_unit_scan_v1.py
```


## Third-pass fixes in v4

- Made the S1g runner avoid importing dictionary/data and fast-backend modules at module import time, so its pure unit tests can run in reduced review bundles.
- Made `fast_backend.py` lazily import the hamming wordlist loader only when `wordlists` is not supplied.
- Fixed config-summary accounting for failed configs with reason suffixes such as `research_selected:missing_dictionary_path:...`.
- Added explicit no-sample handling so missing token rows cannot silently produce an apparently complete empty scoring run.
- Corrected progress denominator for parity/canary modes when the optional diagnostic `research_selected` cut is attempted.

## Suggested run order on the build machine

1. Build the `_span_hamming_fast` extension using the existing repo build path.
2. Run the backend span-Hamming tests.
3. Run the S1g runner tests.
4. Set `RUN_MODE = "inventory_only"` in the S1g runner and run it.
5. If primary selected dictionaries load, set `RUN_MODE = "parity_smoke"` and run it.
6. If parity passes, set `RUN_MODE = "canary"` and run it.
7. Only then set `RUN_MODE = "full"`.

## Things I could verify here

- The modified C++ header compiled in a tiny local C++ fixture after the second-pass changes.
- The new S1g runner passes Python syntax compilation.
- The new S1g runner test file passes Python syntax compilation.
- The S1g runner tests pass locally in the reduced review bundle: `17 passed`.
- Second-pass checks fixed duplicated `prefix_500` chunk emission.
- Second-pass checks added per-length backend counters so cap pressure by length is not derived from repeated whole-sample totals.
- Timing and cap-pressure summaries now de-duplicate HD-bin rows before aggregating sample/length counters.

## Things I could not verify here

- pybind11 extension build.
- full repo pytest execution after building the optional extension.

Reason: this extracted review bundle still does not include the normal build/data setup required to run the full repo suite. The pure S1g runner tests now avoid importing data assets at module import time and do run here.
