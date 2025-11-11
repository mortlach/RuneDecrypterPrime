# `core/types.py`

> Purpose: canonical enum/validation layer for every high-level option (Direction, Device, SolverName, ObjectiveSpec, etc.). RunAPI, pipeline, and scoring configs all call these helpers to prevent magic strings.

## Key Validators
- `ensure_direction(value)` - Accepts `Direction` or strings (`"ltr"`, `"rtl"`) and returns `Direction`.
- `ensure_device(value)` / `parse_device(val)` - Converts strings (`"cpu"`, `"cuda"`, `"gpu"`) to `Device`.
- `ensure_solver_name(value)` - Maps strings/enums to `SolverName` (beam/ga/sa/hybrid).
- `ensure_scorer_impl`, `ensure_scorer_name` - Similar validation for scorer enums.
- `ensure_keyops_family`, `ensure_cipher_kind`, `ensure_key_kind` - Keep core registries type-safe.
- `parse_optimizer_kind(val)` - Legacy parser used by guardrails.
- `ensure_se_mode`, `ensure_objective_family`, `ensure_stat` - Support scoring configs and telemetry.

## Usage
```python
from rune_decrypter_prime.core.types import ensure_device, ensure_solver_name

device = ensure_device("gpu")        # -> Device.CUDA
solver = ensure_solver_name("ga")    # -> SolverName.GA
```

## Tests
- `tests/api/test_normalize_direction.py`, `tests/guardrails/test_core_no_direction_magic_tokens.py` - depend on `ensure_direction`.
- `tests/guardrails/test_normalize_scorer_and_optimizer_enums.py` - covers the scorer/solver validators.
- `tests/telemetry/test_schema_contract.py` - relies on `ensure_device`/`to_canonical_device_str` to keep telemetry consistent.

## Related Docs
- `docs/reference/api/normalize.md` - most user inputs pass through these helpers.
- `docs/reference/core/config/scoring.md` - uses the objective/stat validators when instantiating `ScoringConfig`.

