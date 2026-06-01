# Scoring/Torch freshness crosscheck — 2026-04-09

Status: active
Work status: done
Project: benchmark_campaign_v1_1

This note cross-checks the scoring/Torch support notes against the current test
surface found in the reviewed repo bundle.

## Current scoring/backend test anchors seen in the reviewed bundle

Confirmed files include:
- `tests/scoring/test_backend_selection_and_parity.py`
- `tests/scoring/test_score_parity_numpy.py`
- `tests/scoring/test_score_parity_torch.py`
- `tests/scoring/test_unified_scorer_contract_torch.py`
- `tests/scoring/test_torch_objective_contracts.py`
- `tests/scoring/test_avg_ecdf_runtime_separation.py`
- `tests/scoring/test_scoring_integrity.py`

Interpretation:
- current backend, parity, contract, and integrity concerns are actively tested
- scoring/Torch notes remain justified as support material

## File-by-file freshness judgement

### A. Keep as active support for now

#### `scoring_contract_ecdf_abi.md`
Why:
- closely tied to backend/contract reasoning
- still matches the presence of backend-selection/parity tests
- still useful for explaining why scoring contracts matter

Judgement:
- keep as active support

#### `README_TESTS_SCORING_2.md`
Why:
- directly about the scoring test surface
- still useful as a bridge between support notes and the current tests

Judgement:
- keep as active support

#### `torch_scoring_pipeline_upgrade_plan_v1.md`
Why:
- current repo still has substantial Torch-specific tests
- still useful as support context for Torch rollout/contract reasoning

Judgement:
- keep as active support, but clearly secondary to current tests

#### `scoring_speed_investigation_2026-02-22.md`
Why:
- still relevant as backend/performance support context
- especially while scoring/backend evolution remains active

Judgement:
- keep as active support, but review again later if performance shape settles

### B. Keep as historical-but-useful support for now

#### `score_harden_v2.txt`
Why:
- still plausibly useful as hardening history
- but reads more transitional and less like canonical current truth

Judgement:
- historical but useful support
- candidate archive later if superseded by cleaner current notes

#### `fully_torch_compliant_notes.txt`
Why:
- still relevant to upgrade intent
- but reads more like transitional planning/hardening material than a core live document

Judgement:
- historical but useful support
- candidate archive later once the final Torch/benchmark stance is clearer

## Overall judgement

The scoring/Torch support layer should remain in the benchmark project home, but
with a clearer internal split:

- active support:
  - `scoring_contract_ecdf_abi.md`
  - `README_TESTS_SCORING_2.md`
  - `torch_scoring_pipeline_upgrade_plan_v1.md`
  - `scoring_speed_investigation_2026-02-22.md`

- historical but useful support:
  - `score_harden_v2.txt`
  - `fully_torch_compliant_notes.txt`

## What this does not yet do

This note does **not** move any files to archive yet.
It only makes the freshness judgement explicit.
