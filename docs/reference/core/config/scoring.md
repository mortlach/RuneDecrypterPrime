# `core/config/scoring.py`

> Purpose: defines `ScoringConfig`, the canonical dataclass RunAPI hands to the LMPrime scorer. It normalises objective strings/dicts, encoding directions, seeding modes, and channel weights so every run produces consistent telemetry.

## Components
| Symbol | Description |
| --- | --- |
| `_objective_from_string(spec)` | Parses legacy strings (`"pct.logp.win10"`, `"energy"`, etc.) into `ObjectiveSpec`. |
| `ScoringConfig` | Dataclass with all scorer knobs (`model_root`, `impl`, `dtype`, `objective`, `encoding_dir`, WLI/text channel weights). `__post_init__` normalises enums and channel weights. |

## Usage
```python
from rune_decrypter_prime.core.config.scoring import ScoringConfig

cfg = ScoringConfig(
    objective="pct.logp.win10",
    encoding_dir="ltr",
    n_char=2,
    n_wli=2,
    impl="numpy",
    dtype="float32",
    char_weights={2: 0.6},
    wli_weights=[(2, 0.4)],
)

# RunAPI converts user params into this dataclass before invoking LMPrime.
```

## Validation & Tests
- `tests/api/test_normalize_impl_and_optimizer.py` / `tests/api/test_normalize_direction.py` - ensure user-facing enums land in `ScoringConfig`.
- `tests/scoring/test_backend_selection_and_parity.py` - depends on `ScoringConfig` to switch between NumPy/Torch implementations and verify parity.
- `tests/scoring/test_pct_win10_stats_and_telemetry.py` - confirms `objective` parsing and WLI/channel weights flow into telemetry.

## Related Docs
- `docs/guides/scoring_deep.md` - explains how Hands-on users should tune these knobs.
- `docs/reference/api/normalize.md` - describes how RunAPI builds the kwargs that eventually instantiate `ScoringConfig`.

