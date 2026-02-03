# `api/normalize.py`

> Purpose: provide a single entry point for converting user-facing inputs (strings, enums, NumPy arrays, legacy aliases) into the typed objects consumed by `RunAPI`. Everything that touches ciphertext, WLI, scorer configuration, or permutation specs flows through this module so that determinism and guardrails live in one place.

## Key Responsibilities

### Scoring / Objective Helpers
| Function | Accepts | Returns |
| --- | --- | --- |
| `normalize_objective_family(value)` | strings such as `"pct"`, `"avg"`, `"energy"` or `ObjectiveFamily` enums | `ObjectiveFamily` |
| `normalize_stat(value)` | `"logp"`, `"zsum"`, `"madsum"` strings or `Stat` enums | `Stat` |
| `normalize_objective_spec(value)` | dotted strings like `pct.logp.win10`, dictionaries, or `ObjectiveSpec` instances | `ObjectiveSpec` |
| `normalize_scorer_params(params)` | dict of scorer kwargs | dict with `encoding_dir`, `objective`, etc. coerced to enums; rejects `channel`/`device` keys |

### Direction / Device / Channels
| Function | Notes |
| --- | --- |
| `normalize_encoding_dir(direction)` | Accepts `Direction` or strings (`"ltr"`, `"rtl"`, legacy `"fwd"`, `"rev"`). |
| `normalize_device(value)` | Accepts `Device` or `"cpu"`, `"cuda"`, `"gpu"`. |
| `normalize_channel(value)` / `normalize_se_mode(value)` | Parse `Channel` or `SeMode` enums from strings. |

### Ciphertext & WLI Utilities
| Function | Description |
| --- | --- |
| `to_indices(text)` | Convert rune strings, English strings, numpy arrays, or `(indices, wli)` tuples to a contiguous `np.uint8` array. Validates integer inputs are in `[0..28]` before casting. |
| `make_single_word_wli(L)` | Build `[[0, L], [1, L], ..., [L-1, L]]` using `(pos_in_word, word_len)`. |
| `wli_from_text(text)` | Infer WLI pairs `(pos_in_word, word_len)` from spaces after transliteration. |

Notes:
- WLI is a pure word-boundary signal; spaces are not part of rune indices. When WLI is present, word boundaries are fixed by the list.
- WLI entries must be `<= 63` (LMPrime uses 6-bit pos/len encoding). For long inputs without spaces, prefer `wli_data=[]` with `scorer_params.use_word_breaks=False`.

### Permutation / Optimiser Helpers
| Function | Description |
| --- | --- |
| `_perm_to_int_list(obj)` / `_perm_as_sequence(obj)` | Strict conversions that reject ragged/permutations with duplicates. |
| `invert_permutation(perm)` | Return `perm⁻¹` so downstream code can reinject plaintext indices. |
| `normalize_optimizer_name(x)` / `normalize_optimizer_spec(spec)` | Map user aliases (`"ga"`, `"beam"`, `"hybrid"`) to the canonical solver names/param dicts. |
| `normalize_scorer_impl(x)` | Accept enum-like or string values (`"numpy"`, `"torch"`, `"auto"`). |

## Usage Example
```python
from rune_decrypter_prime.api import normalize
from rune_decrypter_prime.core.types import Direction

# Convert a human-friendly scorer config into strict enums.
scorer_params = normalize.normalize_scorer_params({
    "encoding_dir": "rtl",
    "objective": "pct.logp.win10",
})

# Prepare ciphertext indices + permutation helpers.
ct_indices = normalize.to_indices("ᚦᛖᚱᛖ ᛋᛖᚳᚱᛖᛏ")
direction = normalize.normalize_encoding_dir(Direction.LTR)
orig_perm = [2, 0, 1]
inverse_perm = normalize.invert_permutation(orig_perm)
```

## Related Tests
- `tests/api/test_normalize_direction.py`, `tests/guardrails/test_core_normalize_direction_accepts_enum_and_string.py` - ensure direction parsing accepts enums/strings only.
- `tests/api/test_normalize_text_permutation.py`, `tests/guardrails/test_core_no_direction_magic_tokens.py` - permutation coercion and legacy token denial.
- `tests/guardrails/test_normalize_scorer_and_optimizer_enums.py` - string/enum equivalence for solver + scorer implementations.

## See Also
- `docs/guides/architecture.md` (Hands-on section uses `to_indices` fast paths).
- `docs/howto/read_telemetry.md` (ties the normalised direction + permutation back to telemetry fields).
- `docs/reference/api/maps_api.md` for the UX helpers that call into these normalisers.

