# Benchmark campaign current-code crosscheck note

Status: active
Work status: needs_review
Project: benchmark_campaign_v1_1

This note records what was actually confirmed in the reviewed bundle.

## A. Confirmed in code/tests

### A1. Community benchmark machinery exists
Confirmed path:
- `tools/benchmarks/community/`

Interpretation:
- campaign implementation is real, not merely planned

### A2. Campaign schema/workflow tests exist
Confirmed path:
- `tests/community/`

Examples confirmed:
- `test_campaign_schemas_v1_1.py`
- `test_combine_and_aggregate_v1_1.py`
- `test_manifest_generation_v1_1.py`
- `test_manifest_sharding_v1_1.py`
- `test_profile_config_layer_v1_1.py`
- `test_run_shard_v1_1.py`
- `test_run_single_job_config_v1_1.py`
- `test_setup_and_preflight.py`
- `test_validate_run_bundle_v1_1.py`

### A3. Scoring-path gate evidence exists
Confirmed files:
- `tests/scoring/test_avg_ecdf_runtime_separation.py`
- `tests/scoring/test_backend_selection_and_parity.py`

Interpretation:
- the campaign scoring-gate story is attached to real tests

### A4. Periodic benchmark support machinery exists
Confirmed paths:
- `tools/benchmarks/periodic_sub_trans/`
- `tools/benchmarks/periodic_sub_trans/common/`
- `tools/benchmarks/periodic_sub_trans/sub_then_col/`
- `tools/benchmarks/periodic_sub_trans/col_then_sub/`

Interpretation:
- the campaign is tied to a real benchmark runner surface, not just schemas

## B. Confirmed planning/code mismatch or incompleteness

### B1. The live planning no longer needs to be read from `planning/drafts/`
The promoted campaign docs are clearly active, but their old home is misleading.

Interpretation:
- migration into this project home is justified

### B2. Support streams are real, but still need stable ordering here
The planning docs treat these as major substreams:
- setup/preflight
- scoring path / Torch compliance
- runner cleanup / harmonisation

Interpretation:
- they belong here, but still need cleaner internal ordering

### B3. Public CPU/NumPy submission discipline remains a planning and policy truth
The campaign docs lock:
- `device="cpu"`
- `scoring_backend="numpy"`

The reviewed tests support the broader scoring/backend story, but the main point
here is still contractual discipline rather than a special new code surface.

## C. Working rule for this project home

State the campaign plainly as:
- real and code-backed
- structurally mis-homed before migration
- still needing one stable live planning home
