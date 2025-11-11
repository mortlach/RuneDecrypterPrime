rune_decrypter_prime/scoring
============================

All scorers (NumPy, Torch, unified) plus the language-model runtime they share.

Main modules
------------
- `rune_scorer.py`: CPU NumPy implementation. Handles windowing, percentile
  objectives, telemetry, and WLI caching.
- `torch_rune_scorer.py`: parity scorer built on PyTorch tensors (CPU/GPU).
- `unified_rune_scorer.py`: small wrapper that dispatches to NumPy or Torch
  depending on config.
- `language_model/`: runtime loader + optional `_fastlm` extension used to
  stream 29-symbol n‑gram tables and ECDF data.

Design notes
------------
- Scorers are deterministic and stateless aside from short-lived caches (WLI
  windows, language-model objects). The engine calls `clear_wli_cache()` after
  every run.
- Inputs are rune-index arrays (`uint8`) plus optional WLI break matrices.
  Scorers use a fixed sliding window (`win=10`, stride=1) to produce percentile
  scores in `[0, 1]` that optimisers maximise.
- Language-model tables live under `data/language_model/…` and are loaded via
  `LmPrimeRuntime`. Building `_fastlm` is optional on Windows (prebuilt `.pyd`
  is included) but required on Linux/macOS for high-throughput loading.
