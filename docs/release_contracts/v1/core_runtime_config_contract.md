# V1 core runtime config contract

Core runtime and scorer construction receive canonical typed config objects.

Required typed objects:

- `CipherConfig`
- `ScoringConfig`
- `SolverConfig`
- `ProblemSpec`
- `DecryptionProblem`

Public API helpers may accept user shorthand, aliases, or dictionaries. Those inputs must be normalised before they cross into core runtime, scorer construction, or solver execution.

Forbidden in core runtime/scorer paths:

- `src/rune_decrypter_prime/core/config.py` compatibility shim
- hidden `_cfg_get` style helpers
- dict/config-bag support in `ProblemSpec`, `DecryptionProblem`, `RuneScorer`, or `build_scorer`
- raw string enum values where typed enum contracts are required

Requested optional production scorer lanes must be active or blocked. Report-only lanes may be visible and unavailable without changing score or rank.
