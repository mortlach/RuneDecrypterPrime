# Install validation playbook

This page separates the complete product install from normal CI cost control.
The canonical definitions are in `asset_profiles_v1.json` and
`docs/release_contracts/v1/V1_ASSET_AND_CI_PROFILES.md`.

## Full V1 product install

```text
python install.py
```

This selects `full_v1`. It installs the package, checks native imports, obtains
or verifies the complete supported LM1-LM4 runtime assets, and runs compact
smoke tests. It must not silently fall back to LM1/LM2 when full assets are
missing.

## CI-light install

```text
python tools/ci/install_light.py
```

This selects `ci_light`. It verifies the exact source-bundled LM1/LM2 asset set
and does not download the large GitHub Release bundles. It is internal CI
tooling, not a replacement product install.

## Normal push and pull-request validation

Workflow:

```text
.github/workflows/rdp_v1_full_ci.yml
```

This is the only automatic V1 gate. On Windows and Ubuntu with Python 3.11 it:

1. installs `ci_light`;
2. runs pytest with `not full_assets`;
3. runs `TutorialRunSet.CI_LIGHT`;
4. preserves install, test and tutorial logs.

## Manual full-proof validation

Workflow:

```text
.github/workflows/rdp_v1_full_proof.yml
```

This manual `workflow_dispatch` gate uses a fresh Windows and Ubuntu runner. It:

1. runs `python install.py`;
2. downloads pinned release bundles when they are not already present;
3. verifies bundle SHA-256, byte size, extraction safety and final runtime files;
4. runs complete pytest, including `full_assets` tests;
5. runs `TutorialRunSet.ALL_WORKING`;
6. preserves install, test and tutorial logs.

`ALL_WORKING` includes the three long-running Kaeding qualifications. Each may
take several hours; this manual gate is intentionally not a normal CI or local
smoke command.

The full proof is the real release signal for the complete asset profile.

## Failure triage artefacts

Collect:

```text
output/install_logs/*.log
output/ci_logs/*.log
output/test_logs/*.log
output/tutorial_logs/*.txt
```
