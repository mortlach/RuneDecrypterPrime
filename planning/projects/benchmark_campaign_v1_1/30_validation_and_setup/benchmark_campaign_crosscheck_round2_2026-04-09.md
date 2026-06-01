# Benchmark campaign crosscheck round 2 — 2026-04-09

Status: active
Work status: done
Project: benchmark_campaign_v1_1

This note records a second code-facing crosscheck pass for the active benchmark
campaign home.

## What looks strongly grounded in the reviewed repo bundle

### A. Community benchmark machinery
Confirmed path:
- `tools/benchmarks/community/`

Interpretation:
- campaign implementation remains clearly real

### B. Community workflow and validation tests
Confirmed path:
- `tests/community/`

Examples confirmed in the reviewed bundle:
- campaign schema tests
- combine/aggregate tests
- manifest generation and sharding tests
- run-shard tests
- run-single-job-config tests
- setup-and-preflight tests
- validate-run-bundle tests

Interpretation:
- the campaign is backed by a serious test surface

### C. Scoring/backend tests
Confirmed files:
- `tests/scoring/test_avg_ecdf_runtime_separation.py`
- `tests/scoring/test_backend_selection_and_parity.py`

Interpretation:
- the scoring/backend story is backed by real tests
- preserving scoring/Torch notes under the benchmark home remains justified

## What still needs caution

### D. Support-note freshness
Result:
- the support notes now living under:
  - `33_scoring_and_torch_support/`
  - `35_reference_packs/...`
  are justified as support/reference
- but they have not all been re-validated line-by-line against current code/tests

Interpretation:
- they should remain secondary layers
- some may later move to archive

### E. Draft-origin drift
Result:
- the live docs now need old-draft retirement more than more intake

Interpretation:
- the new project home is justified
- but final cut-over still needs an explicit rule

## What this means for the live project home

The benchmark campaign home is justified as:
- a real active campaign project
- backed by code/tests
- with support/reference layers that still need later freshness triage
