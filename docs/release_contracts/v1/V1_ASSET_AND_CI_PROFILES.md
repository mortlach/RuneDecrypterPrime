# V1 asset and CI profiles

This is the A1 contract for V1 language-model assets and validation tiers.

## Canonical asset profiles

The repository has exactly two named profiles, defined in the root
`asset_profiles_v1.json` file.

### `ci_light`

`ci_light` is the normal push and pull-request profile. It uses only the
source-bundled LM1/LM2 `nose` assets, does not download GitHub Release bundles,
runs pytest with `not full_assets`, and runs `TutorialRunSet.RELEASE`.

This profile controls CI cost. It is not the complete product capability claim.

### `full_v1`

`full_v1` is the normal user install and release-proof profile. It verifies or
downloads the complete supported LM1-LM4 runtime asset set, runs the complete
pytest suite, and runs the bounded `FULL_ASSET_EXAMPLES` selection.

The default public install remains:

```text
python install.py
```

It must fail clearly when required full assets cannot be obtained or verified.
It must not silently downgrade the accepted LM1-LM4 scorer design to LM1/LM2.

## Test marker contract

Tests that require the installed full LM1-LM4 profile use:

```text
@pytest.mark.full_assets
```

The push gate excludes that marker. The manual full-proof gate does not. Tests
that only inspect the full-profile contract or exercise fake asset bundles may
run under `ci_light`.

## Tutorial profile contract

Full-asset exceptions are explicit filename sets in
`tutorials/v1/run_tutorials.py`. The human catalogue in
`tutorials/v1/README.md` records the corresponding requirement and truth use.

The two-period crib tutorials require `full_v1` because their accepted F1 judge
uses character and WLI orders 1-4. Labels must describe the assets actually
required; a successful cached run does not justify a narrower label.

## Workflow contract

There are two authoritative validation workflows:

1. `.github/workflows/rdp_v1_full_ci.yml` is the only automatic push and
   pull-request gate. It installs `ci_light`, excludes `full_assets` tests and
   runs the `RELEASE` tutorial set on Python 3.11 for Windows and Ubuntu.
2. `.github/workflows/rdp_v1_full_proof.yml` is a manual `workflow_dispatch`
   release gate. It installs `full_v1`, runs complete pytest and runs
   `FULL_ASSET_EXAMPLES` on Python 3.11 for Windows and Ubuntu.

The `QUALIFICATION` group is separate from both workflows. Its long-running
P7/C7 programs require an explicit scientific plan and are not routine release
checks.

Packaging workflows may remain manual and explicitly non-authoritative. They do
not replace either validation gate.

## Release asset contract

`assets_manifest_v1.json` remains the file-and-hash authority. The
`v1_lm_ci_light` set identifies the exact source-bundled files. The
`v1_lm_runtime_full` set identifies the complete supported installation and the
pinned GitHub Release bundles used to obtain missing large files.

The release bundle builder must regenerate both set labels consistently.
