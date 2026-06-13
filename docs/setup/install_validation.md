# Install Validation Playbook

This is the lightweight process for confirming install/deploy readiness without a release tag.

## Scope

Pass criteria for a candidate commit:

1. Full test suite is green on your dev machine.
2. Fresh-environment install smoke passes.
3. Setup/preflight emits ready markers in the expected output location.

## Local Clean VM Validation

From repo root in a fresh VM:

```bash
python tools/ci/install_smoke.py
```

Expected outcome:

1. Exit code `0`.
2. `output/tools/benchmarks/community/setup_preflight/latest/benchmark_ready.json` exists and contains `"ready": true`.
3. `output/tools/benchmarks/community/setup_preflight/latest/preflight_report.json` exists and contains `"success": true`.

## GitHub Validation

Run workflow:

- `.github/workflows/install-smoke.yml`

Current profile:

1. Manual trigger (`workflow_dispatch`).
2. Fresh runner matrix: Windows and Ubuntu.
3. Executes `python tools/ci/install_smoke.py`.

## Failure Triage Artifacts

Collect these files from the failing machine/run:

1. `output/tools/benchmarks/community/setup_preflight/latest/setup.log`
2. `output/tools/benchmarks/community/setup_preflight/latest/setup_report.json`
3. `output/tools/benchmarks/community/setup_preflight/latest/preflight.log`
4. `output/tools/benchmarks/community/setup_preflight/latest/preflight_report.json`
