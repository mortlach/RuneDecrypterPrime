# Repo Tidy TODO

Status date: 2026-02-22

Scope target:
- Top-level folders intended for repository source: `src`, `docs`, `tools`, `tests`, `tutorials`, `assets_packed`, `solve`
- `tools/` intended subfolders: `tools/benchmarks`, `tools/repo_tidy`
- `solve/` intended subfolders: `solve/5455`

Already completed:
- Moved stray generated artifacts out of `src/output/` and `tools/output/` into `output/src/` and `output/tools/`.
- Added no-git repo hygiene sweep: `tools/repo_tidy/sweep.py`.
- Added guard tests: `tests/meta/test_repo_tidy_sweep.py`.
- Removed machine-specific workflow references from updated files (`PyCharm`, absolute local paths).
- Community setup/preflight now writes to `output/tools/benchmarks/community/setup_preflight/...` (latest snapshot under `.../latest/`), not repo root.

Pending cleanup (reported by `python tools/repo_tidy/sweep.py --strict-top-level`):
- Top-level folders to archive/migrate/remove:
  - `assets/`
  - `bigram_research/`
  - `legacy/`
  - `planning/`
  - `solving/`
- `tools/` subfolders to migrate into approved structure or retire:
  - `tools/ci/`
  - `tools/docs_lint/`
  - `tools/git_link_scrape/`
  - `tools/out/`
  - `tools/repo_utils/`
  - `tools/scaffold/`
  - `tools/symbols/`
- Benchmark artefact hygiene:
  - Move/replace `tools/benchmarks/solve_proof/proven_solve_pipeline_log.csv` with output-root history under `output/tools/benchmarks/solve_proof/...`.
  - Keep only static templates/spec docs under `tools/benchmarks/solve_proof/`.

Execution checklist:
1. For each pending folder, decide one action: move, archive, or delete.
2. Update any imports/docs that point to old locations.
3. Re-run:
   - `python tools/repo_tidy/sweep.py`
   - `python tools/repo_tidy/sweep.py --strict-top-level`
   - `pytest tests/meta/test_repo_tidy_sweep.py -q`
4. Keep all newly generated run artifacts under `output/` only.
