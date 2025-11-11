# `scoring/policy.py`

> Purpose: shared policy objects for scorer windowing and WLI validation. Keeps the `ScoringConfig` window semantics small and central.

## Components
| Symbol | Description |
| --- | --- |
| `Windowing` dataclass | Represents window size/stride hints passed to scorers. Defaults are lightweight (mostly unused in v1). |
| `validate_wli_pairs(wli)` | Returns `True` if WLI spans are well-formed (each pair convertible to ints). Used before scoring to avoid runtime errors. |

## Usage
Imported by scoring configs and tutorials when validating manual WLI overrides.

## Tests
- Indirectly exercised via `tests/telemetry/test_schema_contract.py` and `tests/api/test_normalize_text_permutation.py`, which feed WLI spans through the scoring pipeline.

