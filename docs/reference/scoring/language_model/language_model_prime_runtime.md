# `scoring/language_model/language_model_prime_runtime.py`

> Purpose: lightweight runtime wrapper that applies direction/SE-mode normalisation and exposes a simple `score_windows(...)` API for use inside the Torch scorer. Keeps the CUDA runtime decoupled from disk-loading logic in `language_model_prime.py`.

## Key Helpers
- `_norm_dir(d)` - Canonicalises direction strings/enums to `"ltr"`/`"rtl"`.
- `LanguageModelPrimeRuntime` (see source) - Holds preloaded model tensors and provides efficient window scoring routines.

## Usage
Internal to `TorchRuneScorer`; not intended for Hands-on callers.

## Tests
- Covered via the same parity tests as the torch scorer (`tests/scoring/test_backend_selection_and_parity.py`).

