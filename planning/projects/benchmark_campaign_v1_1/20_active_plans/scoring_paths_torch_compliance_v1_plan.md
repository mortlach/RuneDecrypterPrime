# Scoring Paths and Torch Compliance Plan (V1)

Status: Active scoring-path and backend-gate plan.

This plan links scoring correctness work to campaign rollout readiness.

Companion docs:

- execution plan: `20_active_plans/community_benchmark_unified_plan_v1_1.md`
- campaign contract: `10_contracts/campaign_spec_v1_1.md`
- setup contract: `30_validation_and_setup/setup_and_preflight_v1_1_spec.md`
- crash evidence: `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/no_wli_stage3_torch_avg_fulltext_crash_report_2026-02-23.md`
- perf evidence: `40_supporting_reference/scoring_and_torch/33_scoring_and_torch_support/scoring_speed_investigation_2026-02-22.md`

## Progress Update (2026-02-27)

This update wave included scoring-path correctness updates and parity checks.

Scoring-plan impact:

- S0 implemented: AVG path is ECDF-free in runtime path (with separation tests).
- S1 implemented: Torch AVG parity coverage added vs NumPy for representative cases.
- no change to public v1.1 submission rule (`cpu + numpy` submissions).
- S2/S3 promotion gates remain active for no-WLI Torch campaign enablement.

Cross-reference for structural progress:

- `40_supporting_reference/runner_cleanup_and_refactor/34_runner_cleanup_and_refactor_history/BENCH_CAMPAIGN_CLEANUP_PLAN_2026-02-25.md`
- `40_supporting_reference/runner_cleanup_and_refactor/34_runner_cleanup_and_refactor_history/benchmarks_periodic_sub_trans_refactor_plan.md`

## Objective

Fix scoring-path correctness first, then expand Torch support safely:

1. AVG must be truly ECDF-free at runtime (NumPy first).
2. Torch AVG must match NumPy AVG with explicit parity tests.
3. no-WLI Stage-3 Torch full-text crash must be closed or hard-gated before promotion.

## Known Blocking Issues

1. Torch path still has a known native crash risk in no-WLI Stage-3 full-text AVG (repro harness retained as safety check).
2. Public campaign submissions are CPU/NumPy only, but internal profiling and no-WLI tuning still depend on stable scoring contracts.
3. Runtime provenance fields (requested vs effective objective/window) still need broader campaign-row surfacing.

## Required Contract (Locked)

1. AVG scoring path:
   - no ECDF cache dependency in runtime path
   - window-agnostic AVG support (not restricted to win10 ECDF assets)
2. PCT/ENERGY scoring path:
   - ECDF-backed and constrained to calibrated windows per contract
3. Torch compliance:
   - feature parity with NumPy for supported objective families
   - deterministic tests and fallback visibility required

## Delivery Phases

## S0: Correctness Gate (NumPy AVG) [Complete]

Work:

- lazy ECDF initialisation in NumPy scorer
- remove any AVG-path ECDF touches and ECDF-side telemetry coupling
- preserve existing PCT/ENERGY behaviour

Tests:

- AVG with non-win10 window works without ECDF assets
- PCT/ENERGY win10 behaviour unchanged

Exit gate:

- AVG path passes with ECDF assets absent for chosen non-win10 tests

Evidence:
- `tests/scoring/test_avg_ecdf_runtime_separation.py`

## S1: Torch AVG Parity Gate [Complete]

Work:

- implement/verify Torch AVG path semantics to match NumPy AVG
- ensure consistent reduction and window-policy behaviour

Tests:

- NumPy vs Torch AVG parity (CPU torch run acceptable)
- parity across representative text lengths and objective params

Exit gate:

- parity tolerances pass on test matrix

Evidence:
- `tests/scoring/test_avg_ecdf_runtime_separation.py`
- `tests/scoring/test_torch_avg_fulltext_stability.py`

## S2: no-WLI Stage-3 Crash Gate [Open]

Work:

- reproduce and isolate full-text Torch AVG crash path
- close root cause or keep enforced fallback to NumPy for that stage

Tests:

- repro harness no longer returns access-violation code
- long-run stability checks complete for configured no-WLI profile set

Exit gate:

- crash path closed, or fallback policy documented and enforced

## S3: Runtime Policy and Telemetry Gate [In Progress]

Work:

- make backend selection behaviour explicit per profile
- preserve deterministic behaviour and add fallback counter assertions for perf profiles

Tests:

- profile policy tests for `impl=numpy`, `impl=torch`, and `impl=auto`
- fallback counters validated where no-fallback is required

Exit gate:

- backend policy is explicit and test-enforced

## Campaign Integration Rules

1. Public v1.1 campaign remains CPU/NumPy even while Torch work continues.
2. no-WLI mixed-flavour campaign promotion is blocked until S0-S2 pass.
3. Any stage-specific backend deviation must be explicit in profile/config and reflected in result metadata.

## Data Integrity and Reporting Requirements

1. Every benchmark run should record backend/objective provenance per stage.
2. Results integration must reject ambiguous provenance rows for campaign-grade datasets.
3. Scoring changes must include before/after metric comparisons on fixed seed sets.

## Open Decisions

1. Whether `impl=auto` should remain device-based only or become capability-aware.
2. Whether solver loop tensorisation is needed for V1 goals, or if decrypt+score acceleration is sufficient.
