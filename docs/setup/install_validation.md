# Install Validation Playbook

This page separates product install validation from normal CI cost control.

## Product install

The public V1 developer-checkout install is:

```text
python install.py
```

It installs the package, checks native imports, installs or verifies the required
LM3/LM4 release assets, and runs compact smoke tests. It must not silently fall
back to LM2 when large assets are missing.

## CI-light install

Normal push and pull-request workflows use:

```text
python tools/ci/install_light.py
```

This is internal CI tooling only. It skips the real large LM download while still
checking package install, native imports, small assets, smoke tests, and the
tiny fake-asset tests for the large-asset machinery.

## Manual large-asset validation

Run workflow:

```text
.github/workflows/v1-large-asset-validation.yml
```

Current profile:

1. Manual trigger only (`workflow_dispatch`).
2. Fresh runner.
3. Confirms no preloaded `downloads/` asset zips are present.
4. Runs `python install.py`.
5. Downloads the real GitHub release bundles.
6. Verifies bundle SHA256 and byte size.
7. Extracts safely.
8. Verifies the final 129 runtime files.
9. Runs focused asset/install tests and the V1 tutorial gate.

Enable the workflow input to run full pytest when a complete release validation
signal is needed.

## Failure triage artifacts

Collect:

```text
output/install_logs/*.log
output/tutorial_logs/*.txt
```
