# `scoring/language_model/language_model_prime.py`

> Purpose: load and query the LMPrime language models used by RuneScorer/TorchRuneScorer. Handles normalisation of direction, SE mode, model names, and reading the compressed `.bin.zst` assets.

## Key Helpers
- `_norm_dir`, `_norm_se`, `_norm_model` - Clamp user input to canonical enums.
- `_load_bin(path)` - Reads LMPrime binary files (`<4sBHIff` header, magic `WLI0`) and returns numpy arrays for character/WLI statistics.
- `_load_model(...)` (see source) - Resolves model paths, caches them, and handles fallback when optional assets are missing.

## `LanguageModelPrime`
- Provides APIs for scoring unigram/bigram windows, computing percentiles, and returning stats used by `RuneScorer`.
- Exposes `score()` that returns dataclasses with `logprob_sum`, `char_stats`, etc.

## Usage
Constructed internally by `RuneScorer`/`TorchRuneScorer`; rarely used directly outside of tooling scripts.

## Tests
- `tests/scoring/test_pct_win10_stats_and_telemetry.py` - ensures LMPrime outputs are stable.
- Tutorial regressions relying on mono scores implicitly test model loading.

