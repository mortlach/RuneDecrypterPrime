# Repo Tidy TODO

Status date: 2026-02-22

Scope target:
- Top-level folders intended for repository source: `src`, `docs`, `tools`, `tests`, `tutorials`, `assets_packed`, `solve`
- `tools/` intended subfolders: `tools/benchmarks`, `tools/ci`, `tools/docs_lint`, `tools/git_link_scrape`, `tools/repo_tidy`, `tools/repo_utils`, `tools/scaffold`, `tools/symbols`
- `solve/` intended state: legacy shim (README-only), active puzzle work under ignored `solving/<puzzle>/`

Already completed:
- Moved stray generated artifacts out of `src/output/` and `tools/output/` into `output/src/` and `output/tools/`.
- Added no-git repo hygiene sweep: `tools/repo_tidy/sweep.py`.
- Added guard tests: `tests/meta/test_repo_tidy_sweep.py`.
- Removed machine-specific workflow references from updated files (`PyCharm`, absolute local paths).
- Community setup/preflight now writes to `output/tools/benchmarks/community/setup_preflight/...` (latest snapshot under `.../latest/`), not repo root.

Pending cleanup:
- Benchmark artefact hygiene:
  - Move/replace `tools/benchmarks/solve_proof/proven_solve_pipeline_log.csv` with output-root history under `output/tools/benchmarks/solve_proof/...`.
  - Keep only static templates/spec docs under `tools/benchmarks/solve_proof/`.

Completed in top-level cleanup:
- `bigram_research/` -> `docs/research/bigram_research/`
- `legacy/` -> `docs/legacy_source_snapshot/`
- `planning/` kept as top-level local workspace (gitignored), excluded from strict source-tree checks.
- `solving/` kept as local puzzle workspace (gitignored) with puzzle folders (e.g. `54_55`, `finster`).
- `assets/` treated as generated-local runtime workspace and excluded from strict source-tree checks.
- Finster solve outputs migrated to output root:
  - `solve/5455/workbench/solving/finster/outputs/*`
  - -> `output/solve/5455/workbench/solving/finster/outputs/*`
- Finster solve scripts now default to `output/solve/5455/workbench/solving/finster/...`.

Completed in tool subtree:
- Migrated utility scripts into `tools/...`:
  - `ci/validate_outputs.py`
  - `repo_utils/*`
  - `scaffold/new_cipher_scaffold.py`
  - `symbols/generate_symbol_index.py`
  - `git_link_scrape/scrape_github.py` + `git_link_scrape/prompt.txt`
  - `docs_lint/run_docs_lint.py`
- Removed `tools/docs_lint/` tracked reports (moved under `output/tools/docs_lint/legacy_reports/`).

Execution checklist:
1. For each pending folder, decide one action: move, archive, or delete.
2. Update any imports/docs that point to old locations.
3. Re-run:
   - `python tools/repo_tidy/sweep.py`
   - `python tools/repo_tidy/sweep.py --strict-top-level`
   - `pytest tests/meta/test_repo_tidy_sweep.py -q`
4. Keep all newly generated run artifacts under `output/` only.
