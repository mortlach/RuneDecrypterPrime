# Span matching and calibration

Find approximate word spans, choose compatible intervals and turn span evidence into configured scores.

## Where to look

- [backend.py](backend.py) — Reference span-matching backend.
- [fast_backend.py](fast_backend.py) — Native backend adapter.
- [interval_select.py](interval_select.py) — Choose non-overlapping intervals.
- [split_index.py](split_index.py) — Length-based candidate indexing.
- [calibrated_assets.py](calibrated_assets.py) — Load span calibration data.
- [lm_assets_v2.py](lm_assets_v2.py) — Language-model calibration profiles.
- [ecdf_interp.py](ecdf_interp.py) — Calibration interpolation.
- [types.py](types.py) — Span configuration, intervals and statistics.
- [setup_span_hamming_fast.py](setup_span_hamming_fast.py) — Build the native implementation.

## Choices and extension

Span mode, distance limits and calibration profile affect how overlapping matches are assessed. Use the guide to choose a supported combination and check lane availability. The native and reference implementations serve the same declared scoring purpose.

Continue with the [guide](../../../../docs/guides/span_hamming_scorer.md) or the [package map](../../README.md).
