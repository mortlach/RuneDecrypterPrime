# Scoring — deeper guide

The public scoring owner is `api.ScoringConfig`; scorer implementations and
asset loading remain in their exact engine modules.

Important contract points:

- objectives are typed `api.advanced.ScoringObjective` values;
- backend and dtype selections are typed enums;
- requested scorer lanes run, block explicitly or use an explicitly reported
  authorised fallback;
- diagnostic-only signals do not change production ranking;
- oracle/reference material is absent from production scoring inputs;
- `RunResult.scorer_report` and reproducibility metadata expose effective state.

Ordinary code constructs the config directly. `from_dict` exists for serialized
configuration and must reject unknown or ill-typed fields.

NumPy is the normal CPU route. Optional Torch/native routes must preserve the
same declared objective and reporting contract. Full language-model asset gates
are separate from CI-light tests.
