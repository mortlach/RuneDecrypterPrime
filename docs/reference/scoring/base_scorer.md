# `scoring/base_scorer.py`

> Purpose: abstract scorer contract shared by the NumPy/Torch implementations. Provides telemetry helpers, objective parsing, and enforcement of the `pct.logp.winK` objective family used across tutorials and tests.

## Helpers
| Function | Description |
| --- | --- |
| `parse_objective(obj)` | Parses legacy strings such as `"pct.logp.win10"` into `(family, stat, win_hint)` tuples. |
| `normalize_objective(obj, default_win)` | Canonicalises string objectives to `"pct.logp.winK"` format. |
| `_require_objective_pct_logp_win()` | Ensures the current scorer objective matches the contract and returns the window length. |

## `BaseScorer`
- Abstract base class defining `score`, `batch_score`, `telemetry`, and telemetry helpers (`_stash_stats`, `TelemetrySpan` integration).
- Concrete scorers (NumPy/Torch) inherit from this class.

## Usage
Used internally by `scoring/rune_scorer.py` and `scoring/torch_rune_scorer.py`; not instantiated directly by tutorials.

## Tests
- `tests/scoring/test_pct_win10_stats_and_telemetry.py` - relies on the telemetry helpers here.
- `tests/scoring/test_backend_selection_and_parity.py` - ensures both backends respect the same objective parsing rules defined in this module.

## Related Docs
- `docs/reference/scoring/rune_scorer.md` and `docs/reference/scoring/torch_rune_scorer.md` - concrete implementations built on `BaseScorer`.

