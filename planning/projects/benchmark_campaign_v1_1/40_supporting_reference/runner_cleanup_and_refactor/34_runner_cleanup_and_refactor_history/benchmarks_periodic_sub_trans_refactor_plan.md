# Benchmarks Refactor Plan: `periodic_sub_trans`

Status: Supporting implementation plan (structure/harness refactor).

Campaign and scoring gates are governed by:

- `20_active_plans/community_benchmark_unified_plan_v1_1.md`
- `20_active_plans/scoring_paths_torch_compliance_v1_plan.md`

## Goal

Refactor periodic substitution + transposition benchmark runners into a tidy, harmonized structure without changing solver logic.

This refactor is structural (move/copy/extract shared helpers), not an algorithm rewrite.

## Progress Snapshot (2026-02-27)

Completed:
- Shared runner `Tier` type extracted to `tools/benchmarks/periodic_sub_trans/common/runner_types.py` and adopted by:
  - `no_wli/runner.py`
  - `col_then_sub/runner.py`
  - `sub_then_col/runner.py`
- Shared IO helpers expanded in `common/io_reports.py`:
  - `append_csv_row(...)`
  - `write_pipeline_snapshot_files(...)`
- All three flavors now use shared snapshot writing for `instances/stages/summary` JSON+CSV.
- Campaign single-job integration now discovers output directories by flavor path rather than global top-level directory scans.
- Campaign single-job integration now pins campaign scorer backend to NumPy across runner globals and scorer profile dictionaries.
- Campaign single-job integration now uses per-runner `configure_campaign_run(...)` entrypoints (legacy mutation fallback removed).
- `no_wli`, `sub_then_col`, and `col_then_sub` runners now write history rows directly through shared `common/io_reports.append_csv_row(...)` (no local wrapper shims).
- Legacy top-level compatibility wrappers added:
  - `tools/benchmarks/bench_solve_periodic_columnar_pipeline_no_wli.py`
  - `tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
  - `tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py`

Remaining:
- Optional extraction of proven-log specific helpers into dedicated common module.

## Scope

In scope:
- three benchmark flavors currently used:
  - no WLI
  - sub then col
  - col then sub
- shared benchmark utilities:
  - run/output path handling
  - logging/report writing
  - final artifact save/restore
  - proven-solved log helpers
- backwards-compatible wrappers at current top-level script names.

Out of scope:
- changing core solver algorithms
- changing benchmark objective logic beyond path/helper extraction
- including the generic `bench_solve_periodic_columnar_pipeline.py` in this migration wave.

## Target Structure

```
tools/benchmarks/periodic_sub_trans/
  README.md
  common/
    __init__.py
    paths.py
    io_reports.py
    artifacts.py
    proven_logs.py
    telemetry.py
  config/
    __init__.py
    no_wli_pipeline_profiles.py
    ...
  no_wli/
    README.md
    runner.py
    verify_artifacts.py
  col_then_sub/
    README.md
    runner.py
  sub_then_col/
    README.md
    runner.py
```

Legacy entrypoints remain:
- `tools/benchmarks/bench_solve_periodic_columnar_pipeline_no_wli.py`
- `tools/benchmarks/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
- `tools/benchmarks/bench_solve_periodic_columnar_pipeline_sub_then_col.py`

They become thin wrappers importing the new runners.

## Output Path Standard (Required)

All benchmark tool outputs remain under:
- `output/tools/benchmarks/...`

For this refactor, output path mirrors repo structure:
- runner path `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- output root `output/tools/benchmarks/periodic_sub_trans/no_wli/...`

## Migration Phases

1. Scaffold directories + base docs [Done]
2. Extract shared path/report/artifact helpers [In Progress]
3. Migrate no-WLI runner first [Done, with wrapper compatibility kept]
4. Migrate col-then-sub runner [Done, with wrapper compatibility kept]
5. Migrate sub-then-col runner [Done, with wrapper compatibility kept]
6. Convert old scripts to wrappers [Done]
7. Validate compatibility and outputs [In Progress]

## Compatibility Rules

- Existing command lines must continue to work during transition.
- Existing `solve_proof` CSV/JSONL files stay in place and continue to be used.
- Report file names and schema keys should remain stable unless explicitly documented.
- Deterministic behavior (same seed + same config) must not regress.

## Validation Checklist

- `py_compile` passes for all migrated modules and wrappers.
- Smoke run per flavor completes and writes expected report set.
- Output directory goes to `output/tools/benchmarks/periodic_sub_trans/<flavor>/...`.
- `final_instances/` artifacts load with integer arrays and verifier passes (no-WLI path).
- Proven-solved skip/write behavior remains intact.

Latest validation evidence:
- `tests/tools/test_periodic_sub_trans_runner_scorer_impl.py` passed.
- `tests/tools/test_periodic_sub_trans_legacy_entry_wrappers.py` passed.
- `tests/community/test_run_single_job_config_v1_1.py` passed.
- `tests/community/test_run_shard_v1_1.py` passed.
- `tests/community/test_validate_run_bundle_v1_1.py` passed.
- `tests/community/test_combine_and_aggregate_v1_1.py` passed.
- `py_compile` passed for updated runner/common/community/wrapper files.

## Risk Notes

- Path regressions in output roots
- accidental behavior changes while extracting shared code
- import path breakage in wrappers
- subtle differences in telemetry field names/order

Mitigation:
- migrate one flavor at a time
- compare run config/report keys before and after migration
- keep wrappers until stable.
