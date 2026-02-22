# Docs Lint Tools

Primary runner:
- `python tools/docs_lint/run_docs_lint.py --label manual -- <docs-lint-command>`

This writes:
- `output/tools/docs_lint/<timestamp>__docs_lint__<label>__<git>/docs_lint_report.json`
- `output/tools/docs_lint/<timestamp>__docs_lint__<label>__<git>/docs_lint_report.md`
- `stdout.txt`, `stderr.txt` in the same run folder

It also fails if your command writes outside `output/` (unless `--allow-outside-output` is set).

Low-level guard (generic command wrapper):
- `python tools/ci/validate_outputs.py -- <command>`
