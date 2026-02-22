# Tooling Recipes

This page captures repeatable commands for documentation QA and symbol maintenance. Each tool writes into the canonical `output/` tree so artefacts are easy to inspect and share.

---

## Docs Lint Runner

- **Command:** `python tools/benchmarks/repo_tools/ci/validate_outputs.py -- <docs-lint-command>`
- **What it does:** runs your docs lint command and asserts every write stays under `output/`.
- **Outputs:** `output/tools/docs_lint/<timestamp>__docs_lint__<label>__<git>/docs_lint_report.json` and `.md`.
- **When to run:** before publishing docs or when updating references/links. Include the run folder in review attachments if lint fails in CI.

Notes:
- Use a descriptive label in your lint command to keep multiple runs organised.
- Keep docs lint artifacts under `output/tools/docs_lint/...` so they remain shareable and non-personal.

---

## Output Guard (CI-friendly)

- **Command:** `python tools/benchmarks/repo_tools/ci/validate_outputs.py -- <your-command>`
- **What it does:** runs a command and asserts that any created/modified files live under `output/`. Fails with a non-zero exit if writes occur elsewhere.
- **Examples:**
  - `python tools/benchmarks/repo_tools/ci/validate_outputs.py -- <docs-lint-command>`
  - `python tools/benchmarks/repo_tools/ci/validate_outputs.py -- python tools/benchmarks/repo_tools/repo_utils/make_release_src.py`
- **Outputs:** unchanged; this script only reports offenders. Use it to harden public tools before release.

Notes:
- Excludes typical VCS/venv/caches. It checks regular files by mtime/size delta.
- Prefer adding this step to CI around tooling invocations to prevent path leaks and keep artefacts under `output/`.

---

## Symbol Index (optional manual refresh)

- **Command:** `python tools/benchmarks/repo_tools/symbols/generate_symbol_index.py --root src/rune_decrypter_prime > output/tools/benchmarks/repo_tools/symbols/project_symbol_index.txt`
- **Purpose:** generates a lightweight class/function inventory consumed by the docs lint coverage step. Feed the resulting file into version control if the public API changes.
- **Output hygiene:** redirect stdout into `output/tools/benchmarks/repo_tools/symbols/project_symbol_index.txt` (or `output/share/...`) so it stays outside source trees.
- **Customisation:** pass `--root` to scan a different package path.

The docs lint runner already refreshes the index for you; run this command manually only when you need a snapshot outside the lint workflow (e.g., pre-commit hooks or editor extensions).
