# `tutorials/v1/run_all_V1tutorials.py`

> Purpose: reference summary for the batch runner that executes every v1 tutorial.

> Automation helper that discovers every tutorial under `tutorials/v1/` (excluding `dev/`), runs them, and aggregates timings/telemetry into a single report. Useful when validating changes locally before running the full pytest suite.

## Key Helpers
| Function | Description |
| --- | --- |
| `_find_repo_root(start)` | Walks up the filesystem to locate the repo root based on project sentinels. |
| `_ensure_out_dir(repo_root)` | Creates `output/tutorials/all/` (or user-specified folder) to store aggregated reports. |
| `_list_tutorials(tutorials_dir)` | Enumerates tutorial scripts, filtering out `__pycache__` and `dev/`. |
| `_seed_everything(seed)` | Applies deterministic seeds for Python/NumPy/random so batch runs stay reproducible. |
| `_now_tag()` | Timestamp helper used in report filenames. |
| `run_all()` | Orchestrates the entire flow: discover -> seed -> run each tutorial -> collect telemetry/profiling stats. |

## Usage
```bash
python tutorials/v1/run_all_V1tutorials.py --out output/tutorials/batch_runs
```

Outputs a summary JSON/Markdown in the specified folder so you can review scores, runtimes, and failed tutorials quickly.

## Related Docs
- `docs/tests_docs/overview.md` - describes when to run this script vs pytest tiers.
- `docs/guides/outputs.md` - explains the folder structure that this script populates.

