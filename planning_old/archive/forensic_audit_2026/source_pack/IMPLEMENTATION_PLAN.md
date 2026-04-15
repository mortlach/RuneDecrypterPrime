# RDP Audit Implementation Plan (no code changes yet)

This plan is derived from planning/audit1 sources and the current repository state. It does NOT implement fixes yet.
All items below must be verified in code before any change, unless explicitly marked Verified in ACTIVE_STAGE_TODO.md.

## Inputs
- planning/audit1/ACTIVE_STAGE_TODO.md
- planning/audit1/AUDIT_INDEX.md
- planning/audit1/RDP_Audit_Source_Reference_Map_v2.md
- planning/audit1/bug_hunt_linenum.txt
- planning/audit1/bug_hunt.txt
- planning/audit1/RDP_Audit_pdf_linenum.txt
- planning/audit1/BUG_HUNT_FULL_SUMMARY.md

## Goals
- Resolve contract drift across modules (API, config, scoring, solver, telemetry).
- Verify each audit item (PDF-* and BH-*) against current code.
- Add a complete contract-focused test suite tied to audit IDs.
- Implement fixes in controlled, reversible chunks with clear exit criteria.
- Update docs to reflect final contracts and behavior.

## Non-goals (for this phase)
- No refactors unrelated to an audit ID.
- No performance tuning unless required to fix a verified contract bug.
- No feature additions beyond audit fixes and test coverage.

## bug_hunt.txt full-read additions
- The preamble enforces strict evidence-bound rules; every chunk must include explicit code evidence and avoid inference.
- bug_hunt.txt includes extra test suggestions outside the BH ledger ranges; these are now part of the test backlog:
  - test_beam_knobs_effect (file referenced: tests/solvers/test_beam_knobs_effect.py - not present)
  - test_determinism_canary (exists: tests/smoke/test_determinism_canary.py)
  - test_runapi_determinism (exists: tests/smoke/test_runapi_determinism.py)
  - test_scorer_pct_edges_and_clamps (exists: tests/scoring/test_scorer_pct_edges_and_clamps.py)
  - test_windowing_spans (exists: tests/scoring/test_windowing_spans.py)
  - test_lm_cache_isolation (file referenced: tests/scoring/test_lm_cache_isolation.py - not present)
  - test_objective_direction_guard (file referenced: tests/contracts/test_objective_direction_guard.py - not present)
  - test_permutation_space_interruptors (file referenced: tests/contracts/test_permutation_space_interruptors.py - not present)
  - test_seed_validation_strict (file referenced: tests/solvers/test_seed_validation_strict.py - not present)
  - test_wli_invariants_string_path (file referenced: tests/contracts/test_wli_invariants_string_path.py - not present)
  - test_wli_parity_runeglish (file referenced: tests/contracts/test_wli_parity_runeglish.py - not present)
  - test_score_ranking_parity_scalar_vs_batch (mentioned without file)
  - test_score_ranking_parity_numpy_vs_torch (mentioned without file)
  - test_keyops_mutation_preserves_invariants (mentioned without file)
  - test_keyops_mutation_locality_distribution (mentioned without file)
  - test_ecdf_* (generic mention; locate exact target test file)
- bug_hunt.txt references legacy paths like Copy/ and audit_pack_extract/; treat them as historical and map to current repo paths or mark missing during verification.

## Decision Gate (must happen before fixes)
These are PDF-Q items. We will not implement fixes until decisions are recorded.
- PDF-Q01 Canonical WLI Format
- PDF-Q02 Span vs Pos Usage
- PDF-Q03 Permutation semantics with interruptors
- PDF-Q04 Objective direction handling
- PDF-Q05 Score dtype policy
- PDF-Q06 Language model cache isolation
- PDF-Q07 user_map3 key representation
- PDF-Q08 Beam parameters source of truth

Deliverable: a decision log (location to be confirmed by you).

## Work Chunks (implementation order)
Each chunk includes: scope, audit IDs, required verification, tests, and exit criteria.

### Chunk 0 - Decision log + verification scaffolding (no code changes)
Scope:
- Create decision log location and template.
- Add a status tracker per audit ID in this file or in ACTIVE_STAGE_TODO.md.

Audit IDs: PDF-Q01..PDF-Q08
Verification:
- None (decision capture only).
Exit criteria:
- All decisions recorded with rationale and scope impact.

### Chunk 1 - WLI contract alignment (highest leverage contract drift)
Scope:
- Establish a single WLI contract across API, config, scoring, and telemetry.
- Remove or update conversion paths that contradict the contract.

Audit IDs:
- PDF-03, PDF-09, PDF-10, PDF-12
- BH-B01, BH-S01..BH-S04, BH-F2.1..BH-F2.5

Required verification:
- Validate current WLI production in `src/rune_decrypter_prime/api/normalize.py`.
- Validate `CipherConfig` WLI validation in `src/rune_decrypter_prime/core/config/cipher.py`.
- Validate scorer WLI handling in `src/rune_decrypter_prime/scoring/*`.
- Validate LMPrime WLI validation in `src/rune_decrypter_prime/scoring/language_model/language_model_prime.py`.

Tests to add (from audit):
- PDF-T01, PDF-T02, PDF-T03, PDF-T06, PDF-T12
- BH-B01 tests (test_wli_string_path_contract_poslen, test_wli_config_contract_is_consistent_with_hamming, test_wli_uint8_overflow_guard)
- BH-B02 test_wli_alignment_under_text_permutation

Exit criteria:
- All WLI tests pass, WLI contract documented, and WLI validation enforces the chosen format.

### Chunk 2 - Objective direction + dtype correctness
Scope:
- Confirm how objective direction and dtype are used by solvers and scorers.
- Align code with decision on minimize vs maximize and dtype guarantees.

Audit IDs:
- PDF-01, PDF-02, PDF-05
- BH-B04, BH-S07, BH-S08

Required verification:
- Confirm solver comparison logic and any usage of maximize/minimize in core/solvers.
- Confirm dtype propagation in scoring and telemetry.

Tests to add:
- PDF-T04, PDF-T05
- BH-B04 tests (batch vs scalar ordering, dtype knob, numpy vs torch parity)

Exit criteria:
- Objective direction is explicit and consistent across scoring/solver/telemetry.
- dtype behavior is enforced and covered by tests.

### Chunk 3 - LM cache isolation + ECDF correctness
Scope:
- Fix cache contamination and keying errors.
- Ensure cache data is immutable or safely copied.

Audit IDs:
- PDF-04
- BH-F3.1..BH-F3.5

Required verification:
- Inspect LMPrime cache keys and cache mutation paths.
- Verify window size impacts cache selection for ECDF.

Tests to add:
- PDF-T13 (LM cache isolation)
- New ECDF cache key tests based on BH-F3.*

Exit criteria:
- Cache isolation tests pass; cache keying includes all relevant factors.

### Chunk 4 - Interruptors + permutation alignment
Scope:
- Clarify interruptor semantics and interaction with permutations.
- Enforce consistent behavior across pool/exact modes and metadata.

Audit IDs:
- PDF-08, PDF-11
- BH-B02, BH-S01..BH-S04, BH-S23..BH-S27

Required verification:
- Confirm interruptor symbol selection, mutation, and metadata propagation.
- Confirm text permutation and WLI permutation alignment.

Tests to add:
- PDF-T09, PDF-T10, PDF-T11
- BH-B02 tests (roundtrip / alignment)

Exit criteria:
- Interruptor pipeline roundtrips validated with explicit tests.

### Chunk 5 - Solver acceptance + determinism
Scope:
- Align early-stop semantics, tie-handling, determinism, RNG use.

Audit IDs:
- PDF-05, PDF-06
- BH-S10..BH-S14
- BH-10A..BH-10E

Required verification:
- Confirm early-stop and improvement threshold behavior in solvers.
- Confirm seed normalization behavior (no entropy fallback unless documented).

Tests to add:
- PDF-T07, PDF-T08
- Determinism/seed validation tests scoped to minimal solver loops.

Exit criteria:
- Determinism tests pass and solver telemetry reflects actual behavior.

### Chunk 6 - KeyOps + cipher correctness (roundtrip invariants)
Scope:
- Validate key mutation geometry and cipher round-trip behaviors.

Audit IDs:
- PDF-13
- BH-S15..BH-S22
- BH-S23..BH-S27

Required verification:
- Confirm key ops are valid and do not silently normalize invalid keys.
- Confirm periodic substitution + columnar + interruptor invariants.

Tests to add:
- PDF-T14
- BH-B03 tests

Exit criteria:
- Cipher and KeyOps roundtrip tests pass and key validity is enforced.

### Chunk 7 - Config normalization and telemetry contracts
Scope:
- Eliminate silent defaults and setdefault-based stale telemetry.

Audit IDs:
- BH-8A..BH-8G
- BH-S29..BH-S33

Required verification:
- Confirm configuration normalization and validation paths.
- Confirm telemetry fields are updated and not stale.

Tests to add:
- Telemetry schema and contract tests; update or add as needed.

Exit criteria:
- Telemetry contract tests pass and config normalization is consistent.

## Cross-reference matrix (audit ID -> chunk)
- PDF-Q01..Q08 -> Chunk 0 (decision gate)
- PDF-01..PDF-05 -> Chunk 2
- PDF-06 -> Chunk 5
- PDF-07 -> Chunk 4 (beam parameters overlap with solver; may split)
- PDF-08..PDF-12 -> Chunk 1 or 4 (WLI/permutation/interruptor)
- PDF-13 -> Chunk 6
- PDF-T01..T14 -> Chunks 1..6 as listed above
- BH-B01 -> Chunk 1
- BH-B02 -> Chunk 4
- BH-B03 -> Chunk 6
- BH-B04 -> Chunk 2
- BH-F2.* -> Chunk 1
- BH-F3.* -> Chunk 3
- BH-S05..S09 -> Chunk 2
- BH-S10..S14 -> Chunk 5
- BH-S15..S22 -> Chunk 6
- BH-S23..S27 -> Chunk 4 and 6
- BH-8* -> Chunk 7
- BH-10* -> Chunk 5

## Verification workflow (per item)
For each audit ID:
1) Locate the referenced lines in RDP_Audit_pdf_linenum.txt or bug_hunt_linenum.txt.
2) Find the current file/function in the repo and confirm behavior.
3) Record evidence (file:line) and status in ACTIVE_STAGE_TODO.md.
4) If missing context, note it and request clarification before code changes.

## Testing strategy
- All new tests should be small, deterministic, and markable as `tier_a` unless expensive.
- Keep solver tests minimal; avoid long-running solve benchmarks.
- Only add CUDA tests if CUDA is present and required for parity assertions.

## Workflow checklist (run at start of every chunk)
- Restate audit rules: evidence-bound, no guessing, small adversarial tests, caller/callee evidence.
- Confirm the decision log covers any relevant PDF-Q items for this chunk.
- Verify the audit ID(s) against current code and record evidence (file:line) before any changes.
- Implement only changes tied to a specific audit ID; keep diffs minimal and reversible.
- Run targeted tests for the chunk and record results.
- Update docs only after behavior is stable and tests pass.

## Documentation updates
Update docs only after decisions and implementation per chunk:
- WLI contract: docs/guides/scoring.md, docs/reference/api/normalize.md, docs/reference/api/pipeline_helpers.md, docs/architecture/data.md
- Objective/dtype: docs/reference/core/config/scoring.md, docs/guides/scoring.md
- Interruptors/permutation: docs/guides/architecture.md, docs/reference/api/pipeline.md
- user_map3: docs/README.md or dedicated cipher guide

## Questions (blocking)
- Confirm decision log location.
- Confirm whether to create new test files for missing tests or consolidate into existing modules.
- Confirm pytest marker for contract tests (default `tier_a`).
- Confirm whether implementation starts after decisions, or can start after verification of each item.
