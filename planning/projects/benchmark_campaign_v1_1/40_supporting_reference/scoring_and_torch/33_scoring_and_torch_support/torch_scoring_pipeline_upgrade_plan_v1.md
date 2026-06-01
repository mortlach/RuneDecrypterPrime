# Torch Scoring Pipeline Upgrade Plan (V1, Scoring-Only Scope)

Status: Draft execution plan, implementation not started.

Progress (2026-02-25):

- S0 completed (baseline scorer suite run and captured).
- S1 completed (torch hash/probe safety hardening + tests).
- S2 partially completed (full-text AVG stability/parity tests added and passing).
- S3 partially completed (unified scorer exception contract tightened + tests).

## 1) Scope Lock

This plan is intentionally limited to Torch scoring paths so we can stabilise and harden them without solver/cipher/runners refactors.

In scope:

- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py`
- `src/rune_decrypter_prime/scoring/unified_rune_scorer.py`
- `src/rune_decrypter_prime/scoring/rune_scorer.py` (only where needed for parity/contract alignment)
- scoring-focused tests under `tests/scoring/`
- Torch crash repro tests under `tests/tools/` that directly target scorer crash paths

Out of scope for this pass:

- periodic cipher kernels
- solver/runtime tensor-native refactor
- benchmark runner behaviour changes
- campaign schema/pipeline tooling changes

## 2) Inputs Used

Primary planning inputs:

- `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`
- `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/fully_torch_compliant_notes.txt`
- `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/no_wli_stage3_torch_avg_fulltext_crash_report_2026-02-23.md`
- `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/scoring_speed_investigation_2026-02-22.md`
- `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/v1_outward_bugs_bloat_docs_log_2026-02-23.md`

Current code/test anchors:

- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py`
- `src/rune_decrypter_prime/scoring/rune_scorer.py`
- `src/rune_decrypter_prime/scoring/unified_rune_scorer.py`
- `tests/scoring/test_avg_ecdf_runtime_separation.py`
- `tests/scoring/test_torch_input_validation.py`
- `tests/scoring/test_torch_batch_score_numpy_input.py`
- `tests/scoring/test_backend_selection_and_parity.py`
- `tests/tools/test_no_wli_stage3_torch_avg_fulltext_crash_repro.py`

## 3) Current State (Scoring Layer)

1. AVG ECDF separation is partially implemented and already guarded by tests.
2. Torch scorer supports PCT/ENERGY logp and AVG logp paths, including full-text AVG.
3. Full-text AVG Torch path still has known native-crash risk in long runs.
4. Low-level hashing helpers still rely on `assert` (unsafe in optimized runtime).
5. Unified scorer has broad silent fallback handling that can hide scoring-path defects.

## 4) Delivery Plan

## Phase S0: Baseline and Guardrails

Goal:

Freeze current scorer behaviour before edits.

Work:

1. Run existing scorer contract/parity suite and capture pass/fail baseline.
2. Keep crash repro test as manual gate (`RUN_CRASH_REPRO = False`) and preserve script compile check.
3. Record exact target objectives for this pass:
   - `pct.logp.win10`
   - `energy.logp.win10`
   - `avg.logp.winK` (fixed window and full_text)

Tests (existing):

- `tests/scoring/test_avg_ecdf_runtime_separation.py`
- `tests/scoring/test_torch_input_validation.py`
- `tests/scoring/test_torch_batch_score_numpy_input.py`
- `tests/scoring/test_backend_selection_and_parity.py`

Exit gate:

Baseline test run complete and failures triaged before any scorer edits.

## Phase S1: Torch Scorer Safety Hardening

Goal:

Remove crash-prone and optimization-sensitive constructs in Torch scorer internals.

Work:

1. Replace `assert`-based runtime checks in hashing helpers with explicit validation errors.
2. Harden hash/probe loops:
   - explicit probe-exhausted handling and deterministic fallback semantics
   - clear diagnostics counters in `last_stats` for probe stress/fallback events
3. Add shape/dtype sanity checks near model token packing and lookup entry points.

Files:

- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py`

New tests:

- `tests/scoring/test_torch_hash_helpers_validation.py`
  - invalid dtype/rank paths raise deterministic `ValueError`
- `tests/scoring/test_torch_probe_loop_safety.py`
  - forced collision/probe-limit conditions do not crash and report diagnostics

Exit gate:

No `assert`-only runtime invariants remain in Torch scorer hot path; safety tests pass.

## Phase S2: AVG Full-Text Stability and Correctness

Goal:

Stabilise full-text AVG path and guarantee NumPy/Torch agreement.

Work:

1. Audit `_score_raw_logp_full_text` for unsafe device/cpu transitions and bounds assumptions.
2. Ensure consistent handling for:
   - short text vs n-gram order
   - mixed n-gram weights (`char_n3` + `char_n4`)
   - `avg_window_policy=full_text` telemetry fields
3. Ensure AVG path never touches ECDF codepaths.
4. Preserve Stage-3 mitigation fallback capability until crash gate is closed.

Files:

- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py`

Tests (extend existing + new):

- extend `tests/scoring/test_avg_ecdf_runtime_separation.py`
  - add larger batch/length matrix for AVG full-text parity
  - add repeated-call stability check (same input, identical output)
- add `tests/scoring/test_torch_avg_fulltext_stability.py`
  - deterministic repeated scoring loop across fixed seeds
  - explicit check for no ECDF initialisation/calls

Manual gate:

- `tools/benchmarks/periodic_sub_trans/no_wli/repro_stage3_torch_avg_fulltext_access_violation.py`

Exit gate:

Full-text AVG parity passes and manual repro completes repeatedly without native crash.

## Phase S3: Scoring API/Facade Contract Tightening

Goal:

Make scorer interface behaviour explicit and non-silent for Torch paths.

Work:

1. Remove broad silent fallbacks in `unified_rune_scorer` where they hide backend failures.
2. Keep backward compatibility of public methods:
   - `score`
   - `batch_score`
   - `score_with_raw`
   - `batch_score_with_raw`
3. Normalise telemetry keys between NumPy and Torch for objective metadata.
4. Update stale Torch scorer module header comments to reflect actual objective support.

Files:

- `src/rune_decrypter_prime/scoring/unified_rune_scorer.py`
- `src/rune_decrypter_prime/scoring/torch_rune_scorer.py`

New tests:

- `tests/scoring/test_unified_scorer_contract_torch.py`
  - backend exceptions are surfaced deterministically (not silently swallowed)
  - raw-score API consistency checks
- `tests/scoring/test_torch_objective_contracts.py`
  - accepted families/stat combos are explicit
  - unsupported combos fail with precise errors

Exit gate:

Torch scoring contract is explicit, documented, and test-enforced.

## Phase S4: Regression and Performance-Sanity Gates

Goal:

Ship with robust regression protection for scorer-only upgrade.

Work:

1. Add focused regression matrix for representative lengths/objectives.
2. Add lightweight scoring performance sanity checks (not benchmark claims), mainly:
   - no pathological slowdown from safety fixes
   - batch path still used
3. Keep crash repro test as manual/opt-in gate in normal CI.

Tests:

- extend `tests/scoring/test_backend_selection_and_parity.py`
- add `tests/scoring/test_torch_batch_path_regression.py`
- keep `tests/tools/test_no_wli_stage3_torch_avg_fulltext_crash_repro.py` manual gate

Exit gate:

All scoring-tier tests green; no regressions in core parity/safety contracts.

## 5) Test Matrix (What "Robust" Means Here)

Fast deterministic unit tests:

- helper validation
- objective contract failures
- telemetry field presence
- no-ECDF AVG guarantees

Medium integration tests:

- NumPy vs Torch parity for:
  - `pct.logp.win10`
  - `energy.logp.win10`
  - `avg.logp.winK` fixed window
  - `avg.logp.winK` full_text

Heavy/manual gates:

- native crash repro loop
- optional CUDA parity path when CUDA is available

## 6) Definition of Done (Scoring-Only Upgrade)

1. Torch scorer no longer contains assert-only invariants in hot path.
2. AVG full-text path is stable and parity-tested against NumPy.
3. Unified scorer no longer silently masks Torch path errors.
4. Existing scoring behaviour for PCT/ENERGY remains intact.
5. Regression suite for scoring paths passes consistently.
6. Any remaining known risk is explicitly documented with enforced fallback policy.

## 7) Immediate Next Step

Start Phase S0 by running the baseline scorer suite and recording the first failure list (if any), then implement S1 first.
