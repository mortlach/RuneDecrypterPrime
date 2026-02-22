# Repo Tidy Sweep

This folder contains repository hygiene checks used by maintainers.

- `sweep.py`: validates:
  - repository tree policy (`src`, `docs`, `tools/benchmarks`, `tools/repo_tidy`, `tests`, `tutorials`, `assets_packed`, `solve/5455`)
  - no machine-specific absolute paths in text files under policy-managed roots

The sweep intentionally does not call git. It scans the filesystem directly and
ignores runtime/cache folders such as `output/`, `.venv/`, `.pytest_cache/`, and `.git/`.

Run:

```powershell
python tools/repo_tidy/sweep.py
```

Optional strict top-level check:

```powershell
python tools/repo_tidy/sweep.py --strict-top-level
```

This check is also enforced by pytest guardrail tests.
