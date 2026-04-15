# Audit Decisions (Chunk 0)

Location: planning/audit1/DECISIONS.md
Purpose: record the binding decisions for PDF-Q items before any code changes.

## Decision status legend
- Pending: not decided yet
- Decided: decision made, rationale recorded
- Revisit: decision provisional, needs re-check after verification

---

## PDF-Q01 Canonical WLI Format
Status: Decided
Decision: Adopt WLI as (pos_in_word, word_len) everywhere.
Rationale: Aligns with LMPrime validation and torch/fastlm 6-bit encoding; minimizes scoring-side changes.
Impacted areas:
- API normalization (normalize.py)
- CipherConfig WLI validation (core/config/cipher.py)
- Scoring WLI validation (language_model_prime.py, rune_scorer.py, torch_rune_scorer.py)
- Telemetry and pipeline helpers
Notes:
Evidence:
- src/rune_decrypter_prime/api/normalize.py:255-406
- src/rune_decrypter_prime/core/config/cipher.py:85-112
- src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:376-396
- src/rune_decrypter_prime/scoring/torch_rune_scorer.py:1105-1138
- tests/api/test_wli_invariants.py:26-59
- tests/api/test_wli_parity.py:12-18

## PDF-Q02 Span vs Pos Usage
Status: Decided
Decision: WLI stores pos/len only; spans are a separate structure if needed for UI/telemetry.
Rationale: Avoids ambiguous conversion paths and contract drift; keeps scoring inputs strict.
Impacted areas:
- Pipeline helpers (coerce_wli_for_config)
- Any WLI serialization/telemetry
Notes:
Evidence:
- src/rune_decrypter_prime/api/pipeline_helpers.py:234-242
- src/rune_decrypter_prime/api/normalize.py:379-406

## PDF-Q03 Permutation semantics with interruptors
Status: Decided
Decision: Permutation applies to full ciphertext including interruptors; WLI and interruptor metadata permute together.
Rationale: Deterministic and consistent; avoids length-coupled crashes when interruptor counts vary.
Impacted areas:
- Ciphers pipeline / interruptors
- initial_text_permutation_indices handling
- WLI permutation alignment
Notes:
Evidence:
- src/rune_decrypter_prime/ciphers/ciphers_pipeline.py:94-95,178-179,221-225
- tests/core/test_interruptor_permutation.py:22-52

## PDF-Q04 Objective direction handling
Status: Decided
Decision: Higher is always better; minimize objectives are disallowed or inverted to preserve monotonicity.
Rationale: Keeps solver acceptance logic simple and consistent across solvers.
Impacted areas:
- Scorer objective handling
- Solver compare/accept logic
- Telemetry objective fields
Notes:
Evidence:
- src/rune_decrypter_prime/core/config/scoring.py:152
- tests/solvers/test_objective_direction.py:57-68

## PDF-Q05 Score dtype policy
Status: Decided
Decision: Joint tables (logp) remain float32. ECDF grids/quantiles are canonical float64 on disk with `meta_json`.
Runtime policy: core lookup/compute stays float32 by default; when high-precision mode is enabled, accumulation, ECDF interpolation,
and the value used for ordering must be float64. Deterministic tie-breaking is required regardless of dtype.
Rationale: Preserve GPU-friendly throughput while ensuring stable ordering when high-precision is requested.
Impacted areas:
- Scorer dtype selection and telemetry
- Torch/NumPy parity
Notes:
Evidence:
- src/rune_decrypter_prime/scoring/rune_scorer.py:122-149,518-528,608-613
- src/rune_decrypter_prime/scoring/torch_rune_scorer.py:179-183,748-750
- tests/scoring/test_scoring_integrity.py:93-110

## PDF-Q06 Language model cache isolation
Status: Decided
Decision: Caches are per-scorer instance and keyed by full config; no shared global mutation.
Rationale: Eliminates run-order hazards and cache contamination.
Impacted areas:
- LMPrime cache keys and mutation
- ECDF cache keying
Notes:
Evidence:
- src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:61-115,174-175,361-366
- tests/scoring/test_lm_cache_isolation.py:46-71

## PDF-Q07 user_map3 key representation
Status: Decided
Decision: Explicit 2-part key (k1, k2) with full domain constraints; enforce validity.
Rationale: Prevents collapsed keyspace and solver ineffectiveness.
Impacted areas:
- GenericMapCipher / user_map3
- KeyOps definitions and keyspace
Notes:
Evidence:
- src/rune_decrypter_prime/ciphers/generic_map_cipher.py:45,85
- tests/ciphers/test_user_map3_domain.py:20-40

## PDF-Q08 Beam parameters source of truth
Status: Decided
Decision: API parameter names are canonical; solver accepts them and deprecates legacy names if needed.
Rationale: Avoids breaking API users while aligning solver implementation.
Impacted areas:
- Solver config
- Beam solver parameter parsing
Notes:
Evidence:
- src/rune_decrypter_prime/api/_resolve.py:14-16,64-65
- src/rune_decrypter_prime/solvers/beam.py:45-99

## Policy-01 API normalization accepts multiple input forms
Status: Decided
Decision: Allow the API normalization layer to accept multiple device/input forms, then canonicalize to core enums for RDP core.
Rationale: Keep the API forgiving while guaranteeing strict, enum-only inputs inside core and solvers.
Impacted areas:
- api/normalize.py device/channel/scorer normalization
- core/types ensure_device and downstream device branching
- telemetry device labels
Notes:
Evidence:
- src/rune_decrypter_prime/api/normalize.py:129-154
- src/rune_decrypter_prime/core/types.py:137-147

## Policy-02 Hard errors on inconsistent or conflicting config
Status: Decided
Decision: Raise hard errors for inconsistent or conflicting config inputs (no silent precedence or undefined behavior).
Rationale: Transparency; avoid tacit overrides or ambiguous behavior.
Impacted areas:
- Interruptor config precedence (interruptors_cfg vs legacy fields)
- Scorer param strict validation vs normalization
- Any config fields that can collide or conflict
Notes:
Evidence:
- src/rune_decrypter_prime/core/config/interruptor.py:69-124
- src/rune_decrypter_prime/core/config/cipher.py:141-147
- src/rune_decrypter_prime/api/normalize.py:160-163

## Policy-03 WLI word-boundary contract
Status: Decided
Decision: When WLI is provided, word boundaries (spaces) are fixed and never part of rune indices; WLI is the canonical boundary source. When WLI is absent, no space/word-boundary contract exists.
Rationale: Prevents incorrect coupling between interruptor placement and word boundaries; avoids inventing boundaries for no-WLI inputs.
Impacted areas:
- Runtime scoring alignment checks
- Interruptor pool search (WLI invariance)
- Documentation/tests for WLI expectations
Notes:
Evidence:
- src/rune_decrypter_prime/scoring/language_model/language_model_prime.py:376-383
- src/rune_decrypter_prime/core/problem/runtime.py:291
- tests/core/test_interruptor_wli_guard.py:42-52
