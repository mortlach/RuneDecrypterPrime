# Community Benchmark Guide

Guide for running reproducible benchmark sweeps and sharing comparable outputs.

## Goals

- Keep benchmark config explicit in source files (edit constants in runner files).
- Keep outputs comparable via stable profiles + config fingerprinting.
- Keep solved-instance autoskip enabled by default.

## Setup

```powershell
git clone <repo-url>
cd RuneDecrypterPrime
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[dev]
```

## Primary benchmark entrypoints

- `python tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
- `python tools/benchmarks/periodic_sub_trans/col_then_sub/bench_solve_periodic_columnar_pipeline_col_then_sub.py`
- `python tools/benchmarks/periodic_sub_trans/sub_then_col/runner.py`

## Run controls

Edit runner constants at the top of each script.

Most commonly adjusted:

- `PIPELINE_RUN_MODE`
- `FORCE_RERUN_PROVEN`
- `KEY_SEEDS_OVERRIDE`
- `TIERS_REGEX_OVERRIDE`
- `AVOID_REPEAT_FAIL`
- `FAILED_RETRY_SEED_DELTA`

## Output + share checklist

Share run folders from:

- `output/tools/benchmarks/periodic_sub_trans/<flavor>/<timestamp>__<run_name>__<tag>/`

Minimum files to share:

- `summary.json`
- `instances.csv`
- `stages.csv`

Optional:

- `final_instances/*.json`
- corresponding solve-proof log rows under `tools/benchmarks/solve_proof/`

## Sweep rule

Do not retune solver constants mid-sweep. Start a new run after config changes.
