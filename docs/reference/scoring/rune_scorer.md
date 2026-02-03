# `scoring/rune_scorer.py`

> Purpose: NumPy implementation of the LMPrime scorer (used on CPU). Converts plaintext indices plus optional WLI `(pos_in_word, word_len)` pairs into windows, computes percentile statistics, and produces the `pct.logp.win10` objective enforced by RunAPI.

## Key Helpers
| Function | Description |
| --- | --- |
| `_to_u8_1d(a)` | Normalises plaintext arrays to contiguous `np.uint8` vectors. |
| `_to_u8_L2(wli_like)` | Validates WLI pairs (pos/len `<= 63`) and coerces them to an `(N, 2)` `uint8` array. |
| `_precompute_windows(...)` (see source) | Builds cached n-gram windows for scoring efficiency. |

## `RuneScorer` Highlights
- Inherits from `BaseScorer`.
- Accepts `ScoringConfig` (objective, weights, encoding direction, etc.) and loads language models from disk when needed.
- `score` / `batch_score` return mono scores that must meet the tutorial thresholds (≥0.55) and populate telemetry via `_stash_stats`.
- When WLI is present, word boundaries are fixed by the WLI list; when WLI is absent, no word-boundary semantics are assumed.
- Assumes plaintext indices are already validated to `0..28` and WLI entries to `<= 63` by the API/normalisation layer.
- Supports deterministic RNG via the provided `xp` backend (NumPy for this file).

## Tests
- `tests/scoring/test_pct_win10_stats_and_telemetry.py` - ensures stats/telemetry are populated.
- `tests/scoring/test_backend_selection_and_parity.py` - compares NumPy vs Torch implementations.
- Tutorial regressions (`tests/tutorials/test_mono_substitution.py`, etc.) indirectly validate this scorer by asserting mono score thresholds.

## Related Docs
- `docs/reference/scoring/torch_rune_scorer.md` - CUDA/Torch counterpart.
- `docs/reference/scoring/base_scorer.md` - abstract contract documented earlier.

