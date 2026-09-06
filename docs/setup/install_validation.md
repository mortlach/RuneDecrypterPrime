# Install validation

This page is for maintainers and release checks. The ordinary installation
route remains:

```text
python install.py
```

That command installs the `full_v1` asset profile and runs compact smoke tests.
The checks below answer a different question: how much of the supported release
surface has been exercised?

The asset-profile definitions live in `asset_profiles_v1.json`.

## CI-light push gate

The normal push and pull-request workflow is:

```text
.github/workflows/rdp_v1_full_ci.yml
```

On Windows and Ubuntu with Python 3.11 it:

1. runs `python tools/ci/install_light.py`;
2. verifies the source-bundled `ci_light` LM1/LM2 profile;
3. runs pytest with `not full_assets`;
4. runs `TutorialRunSet.RELEASE`;
5. preserves install, CI and tutorial logs.

This keeps routine validation bounded. It is deliberately not proof of the
complete LM1-LM4 asset profile.

## Manual full proof

The complete release workflow is:

```text
.github/workflows/rdp_v1_full_proof.yml
```

It is manual (`workflow_dispatch`) and uses fresh Windows and Ubuntu runners
with Python 3.11. It:

1. runs `python install.py`, selecting `full_v1`;
2. downloads or verifies the pinned release assets;
3. runs the complete pytest suite, including `full_assets` tests;
4. runs `TutorialRunSet.FULL_ASSET_EXAMPLES`;
5. preserves install, test and tutorial logs.

This is the release proof for the complete supported asset profile.

## Qualification is separate

`TutorialRunSet.QUALIFICATION` is not part of the push gate or the full proof.
It contains several-hour scientific programs. Run those only when the scientific
question requires them; a documentation edit is not improved by accidentally
starting an afternoon's worth of cryptanalysis.

## Manual wheel proof

`.github/workflows/rdp_v1_wheel_ci.yml` is a separate manual,
non-authoritative packaging check. It proves that CPython 3.11 wheels can be
built and can import the package plus the required native modules on the
supported CI platforms. It does not replace the full asset proof.

See [build and packaging notes](building.md).

## Failure evidence

With the default source output root, useful evidence is written under:

```text
output/install/<run-id>/
output/ci_logs/
output/test_logs/
output/tutorial_logs/
```

The installer records each command in its own log and writes failure metadata
when installation stops. CI workflows upload the relevant log directories as
workflow artefacts.
